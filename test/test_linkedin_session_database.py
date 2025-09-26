"""
Tests for LinkedIn session database integration functionality.

These tests define the expected behavior for scraping jobs to database,
extracting job descriptions, and integration with the JobDatabase class.
Following TDD principles - these tests should be written BEFORE implementation!
"""

import tempfile
import pytest
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock, call

import sys
sys.path.insert(0, '.')
from lib.linkedin_session import LinkedInSession
from lib.job_database import JobDatabase, JobRecord, ScrapeSession


class TestLinkedInSessionDatabaseIntegration:
    """Test LinkedIn session integration with JobDatabase."""

    @pytest.fixture
    def mock_session(self):
        """Create a mocked LinkedInSession for testing database integration."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                with patch.dict('os.environ', {'COOKIE_ENCRYPTION_KEY': 'rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs='}):
                    session = LinkedInSession(headless=True)

                    # Mock the browser and database dependencies
                    session.driver = MagicMock()
                    session.db = MagicMock()

                    yield session

    @pytest.fixture
    def sample_job_data(self):
        """Sample job data as would be scraped from LinkedIn."""
        return [
            {
                'job_id': 'linkedin_123',
                'title': 'Senior Python Developer',
                'company': 'TechCorp',
                'work_type': 'Remote',
                'location': 'San Francisco, CA',
                'salary': '$120K/yr - $150K/yr',
                'benefits': 'Health, Dental, 401k',
                'url': 'https://www.linkedin.com/jobs/view/123',
                'description': None  # Will be filled by description extraction
            },
            {
                'job_id': 'linkedin_456',
                'title': 'Data Scientist',
                'company': 'DataCorp',
                'work_type': 'Hybrid',
                'location': 'New York, NY',
                'salary': '$110K/yr - $140K/yr',
                'benefits': 'Great benefits package',
                'url': 'https://www.linkedin.com/jobs/view/456',
                'description': None
            }
        ]

    def test_scrape_jobs_to_database_basic(self, mock_session, sample_job_data):
        """
        Test basic job scraping with database storage.

        This method should scrape job listings and store them in the database
        without fetching full job descriptions.
        """
        # Mock the job scraping method to return sample data
        with patch.object(mock_session, '_scrape_job_listings') as mock_scrape:
            mock_scrape.return_value = sample_job_data

            # Mock database operations
            mock_session.db.create_scrape_session.return_value = 1
            mock_session.db.upsert_job.return_value = (True, False)  # inserted, not updated

            # Call the method under test
            result = mock_session.scrape_jobs_to_database(
                search_terms="python developer",
                location="remote"
            )

            # Verify expected behavior
            assert result is not None
            assert 'session_id' in result
            assert 'jobs_processed' in result
            assert 'new_jobs' in result

            # Verify scrape session was created
            mock_session.db.create_scrape_session.assert_called_once()

            # Verify jobs were upserted
            assert mock_session.db.upsert_job.call_count == len(sample_job_data)

            # Verify job data structure
            for call_args in mock_session.db.upsert_job.call_args_list:
                job_record = call_args[0][0]
                assert isinstance(job_record, JobRecord)
                assert job_record.source == 'linkedin'

    def test_scrape_jobs_to_database_with_search_criteria(self, mock_session, sample_job_data):
        """
        Test job scraping with specific search criteria stored in session.

        Verifies that search parameters are properly recorded in the scrape session.
        """
        with patch.object(mock_session, '_scrape_job_listings') as mock_scrape:
            mock_scrape.return_value = sample_job_data

            mock_session.db.create_scrape_session.return_value = 1
            mock_session.db.upsert_job.return_value = (True, False)

            # Call with specific search criteria
            result = mock_session.scrape_jobs_to_database(
                search_terms="senior python developer",
                location="san francisco",
                work_type="remote",
                max_results=50
            )

            # Verify scrape session includes search criteria
            session_call = mock_session.db.create_scrape_session.call_args[0][0]
            assert isinstance(session_call, ScrapeSession)

            # Search criteria should be stored as JSON
            assert session_call.search_criteria is not None
            assert 'senior python developer' in session_call.search_criteria
            assert 'san francisco' in session_call.search_criteria
            assert 'remote' in session_call.search_criteria

    def test_scrape_jobs_to_database_error_handling(self, mock_session):
        """
        Test error handling during job scraping and database operations.

        Ensures that errors during scraping or database operations are handled gracefully.
        """
        # Test scraping failure
        with patch.object(mock_session, '_scrape_job_listings') as mock_scrape:
            mock_scrape.side_effect = Exception("Scraping failed")

            result = mock_session.scrape_jobs_to_database(
                search_terms="python developer"
            )

            assert result is None or result.get('error') is not None

        # Test database failure
        with patch.object(mock_session, '_scrape_job_listings') as mock_scrape:
            mock_scrape.return_value = [{'job_id': 'test', 'title': 'Test'}]

            mock_session.db.create_scrape_session.side_effect = Exception("Database error")

            result = mock_session.scrape_jobs_to_database(
                search_terms="python developer"
            )

            assert result is None or result.get('error') is not None

    def test_scrape_jobs_with_descriptions_to_database(self, mock_session, sample_job_data):
        """
        Test job scraping with full job description extraction.

        This method should scrape jobs and then extract full descriptions
        from individual job pages before storing in database.
        """
        # Mock job scraping and description extraction
        with patch.object(mock_session, '_scrape_job_listings') as mock_scrape:
            with patch.object(mock_session, '_extract_job_description') as mock_extract:
                mock_scrape.return_value = sample_job_data
                mock_extract.side_effect = [
                    "Build amazing Python applications using Django and Flask...",
                    "Analyze complex datasets using Python, SQL, and machine learning..."
                ]

                mock_session.db.create_scrape_session.return_value = 1
                mock_session.db.upsert_job.return_value = (True, False)

                # Call the method under test
                result = mock_session.scrape_jobs_with_descriptions_to_database(
                    search_terms="python developer",
                    max_descriptions=10
                )

                # Verify description extraction was called for each job
                assert mock_extract.call_count == len(sample_job_data)

                # Verify jobs were stored with descriptions
                job_calls = mock_session.db.upsert_job.call_args_list
                for i, call_args in enumerate(job_calls):
                    job_record = call_args[0][0]
                    assert job_record.description is not None
                    assert len(job_record.description) > 0

    def test_scrape_jobs_with_descriptions_limited(self, mock_session, sample_job_data):
        """
        Test job scraping with limited description extraction.

        Verifies that the max_descriptions parameter properly limits how many
        job descriptions are extracted.
        """
        with patch.object(mock_session, '_scrape_job_listings') as mock_scrape:
            with patch.object(mock_session, '_extract_job_description') as mock_extract:
                # Create more jobs than the limit
                extended_job_data = sample_job_data + [
                    {'job_id': 'linkedin_789', 'title': 'DevOps Engineer', 'company': 'CloudCorp'}
                ]
                mock_scrape.return_value = extended_job_data
                mock_extract.return_value = "Sample job description"

                mock_session.db.create_scrape_session.return_value = 1
                mock_session.db.upsert_job.return_value = (True, False)

                # Limit descriptions to 2
                result = mock_session.scrape_jobs_with_descriptions_to_database(
                    search_terms="python developer",
                    max_descriptions=2
                )

                # Should only extract 2 descriptions despite having 3 jobs
                assert mock_extract.call_count == 2

                # Verify first 2 jobs have descriptions, third doesn't
                job_calls = mock_session.db.upsert_job.call_args_list
                assert len(job_calls) == 3

                job1 = job_calls[0][0][0]
                job2 = job_calls[1][0][0]
                job3 = job_calls[2][0][0]

                assert job1.description is not None
                assert job2.description is not None
                assert job3.description is None  # Not extracted due to limit

    def test_scrape_jobs_with_descriptions_error_recovery(self, mock_session, sample_job_data):
        """
        Test description extraction with individual job failures.

        Ensures that failure to extract one job description doesn't prevent
        processing of other jobs.
        """
        with patch.object(mock_session, '_scrape_job_listings') as mock_scrape:
            with patch.object(mock_session, '_extract_job_description') as mock_extract:
                mock_scrape.return_value = sample_job_data

                # First extraction succeeds, second fails
                mock_extract.side_effect = [
                    "Successfully extracted description",
                    Exception("Failed to extract description")
                ]

                mock_session.db.create_scrape_session.return_value = 1
                mock_session.db.upsert_job.return_value = (True, False)

                result = mock_session.scrape_jobs_with_descriptions_to_database(
                    search_terms="python developer"
                )

                # Should still process both jobs
                assert mock_session.db.upsert_job.call_count == len(sample_job_data)

                # First job should have description, second should be None
                job_calls = mock_session.db.upsert_job.call_args_list
                job1 = job_calls[0][0][0]
                job2 = job_calls[1][0][0]

                assert job1.description == "Successfully extracted description"
                assert job2.description is None


class TestJobDescriptionExtraction:
    """Test job description extraction from individual job pages."""

    @pytest.fixture
    def mock_session_with_driver(self):
        """Create a LinkedIn session with mocked WebDriver."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                with patch.dict('os.environ', {'COOKIE_ENCRYPTION_KEY': 'rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs='}):
                    session = LinkedInSession(headless=True)

                    # Mock WebDriver
                    session.driver = MagicMock()

                    yield session

    def test_extract_job_description_success(self, mock_session_with_driver):
        """
        Test successful job description extraction.

        Verifies that job descriptions are properly extracted from LinkedIn job pages
        using appropriate DOM selectors.
        """
        session = mock_session_with_driver
        job_url = "https://www.linkedin.com/jobs/view/123456"

        # Mock the page elements
        mock_description_element = MagicMock()
        mock_description_element.text = """
        We are looking for a Senior Python Developer to join our team.

        Responsibilities:
        - Develop scalable web applications
        - Work with databases and APIs
        - Collaborate with frontend teams

        Requirements:
        - 5+ years Python experience
        - Django/Flask knowledge
        - Strong problem-solving skills
        """

        session.driver.find_element.return_value = mock_description_element

        # Mock successful navigation
        session.driver.get.return_value = None

        result = session._extract_job_description(job_url)

        # Verify navigation and extraction
        session.driver.get.assert_called_once_with(job_url)
        session.driver.find_element.assert_called()

        # Verify extracted content
        assert result is not None
        assert "Senior Python Developer" in result
        assert "Responsibilities" in result
        assert "Requirements" in result
        assert "Django/Flask" in result

    def test_extract_job_description_show_more_button(self, mock_session_with_driver):
        """
        Test job description extraction with "Show more" button click.

        Verifies that truncated descriptions are fully expanded by clicking
        the "Show more" button when present.
        """
        session = mock_session_with_driver
        job_url = "https://www.linkedin.com/jobs/view/123456"

        # Mock show more button and description elements
        mock_show_more_button = MagicMock()
        mock_description_element = MagicMock()
        mock_description_element.text = "Full job description after clicking show more..."

        def mock_find_element(by, value):
            if "show-more" in value or "Show more" in value:
                return mock_show_more_button
            else:
                return mock_description_element

        session.driver.find_element.side_effect = mock_find_element

        result = session._extract_job_description(job_url)

        # Verify show more button was clicked
        mock_show_more_button.click.assert_called_once()

        # Verify description was extracted
        assert result == "Full job description after clicking show more..."

    def test_extract_job_description_multiple_selectors(self, mock_session_with_driver):
        """
        Test job description extraction with fallback selectors.

        Verifies that multiple DOM selectors are tried to handle different
        LinkedIn page layouts and find job descriptions reliably.
        """
        session = mock_session_with_driver
        job_url = "https://www.linkedin.com/jobs/view/123456"

        # Mock the scenario where first selector fails, second succeeds
        mock_description_element = MagicMock()
        mock_description_element.text = "Job description found with fallback selector"

        def mock_find_element_with_fallback(by, value):
            if "primary-selector" in value:
                raise Exception("Element not found")
            else:
                return mock_description_element

        session.driver.find_element.side_effect = mock_find_element_with_fallback

        result = session._extract_job_description(job_url)

        # Should still succeed with fallback selector
        assert result == "Job description found with fallback selector"

    def test_extract_job_description_navigation_failure(self, mock_session_with_driver):
        """
        Test job description extraction when page navigation fails.

        Verifies graceful handling of network errors, timeouts, or blocked requests.
        """
        session = mock_session_with_driver
        job_url = "https://www.linkedin.com/jobs/view/invalid"

        # Mock navigation failure
        session.driver.get.side_effect = Exception("Page not found")

        result = session._extract_job_description(job_url)

        # Should return None on navigation failure
        assert result is None

    def test_extract_job_description_element_not_found(self, mock_session_with_driver):
        """
        Test job description extraction when description element is not found.

        Verifies handling of pages where job description elements are missing
        or have unexpected DOM structure.
        """
        session = mock_session_with_driver
        job_url = "https://www.linkedin.com/jobs/view/123456"

        # Mock successful navigation but no description element
        session.driver.get.return_value = None
        session.driver.find_element.side_effect = Exception("Element not found")

        result = session._extract_job_description(job_url)

        # Should return None when description element not found
        assert result is None

    def test_extract_job_description_empty_content(self, mock_session_with_driver):
        """
        Test job description extraction when element contains no useful content.

        Verifies handling of description elements that exist but are empty
        or contain only whitespace.
        """
        session = mock_session_with_driver
        job_url = "https://www.linkedin.com/jobs/view/123456"

        # Mock element with empty/whitespace content
        mock_description_element = MagicMock()
        mock_description_element.text = "   \n\t   "

        session.driver.find_element.return_value = mock_description_element

        result = session._extract_job_description(job_url)

        # Should return None for empty content
        assert result is None

    def test_extract_job_description_with_wait(self, mock_session_with_driver):
        """
        Test job description extraction with explicit waits for dynamic content.

        Verifies that the extraction waits for dynamic content to load
        before attempting to extract job descriptions.
        """
        session = mock_session_with_driver
        job_url = "https://www.linkedin.com/jobs/view/123456"

        # Mock WebDriverWait functionality
        with patch('lib.linkedin_session.WebDriverWait') as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait.return_value = mock_wait_instance

            mock_description_element = MagicMock()
            mock_description_element.text = "Job description loaded after wait"
            mock_wait_instance.until.return_value = mock_description_element

            result = session._extract_job_description(job_url)

            # Verify wait was used
            mock_wait.assert_called_once()
            mock_wait_instance.until.assert_called_once()

            assert result == "Job description loaded after wait"

    def test_extract_job_description_rate_limiting(self, mock_session_with_driver):
        """
        Test job description extraction with rate limiting between requests.

        Verifies that appropriate delays are implemented to avoid overwhelming
        LinkedIn servers and triggering anti-bot measures.
        """
        session = mock_session_with_driver

        with patch('time.sleep') as mock_sleep:
            mock_description_element = MagicMock()
            mock_description_element.text = "Test description"
            session.driver.find_element.return_value = mock_description_element

            # Extract multiple descriptions
            urls = [
                "https://www.linkedin.com/jobs/view/1",
                "https://www.linkedin.com/jobs/view/2"
            ]

            for url in urls:
                session._extract_job_description(url)

            # Verify sleep was called for rate limiting
            # (Implementation detail - actual sleep duration may vary)
            assert mock_sleep.called


class TestDatabaseIntegrationHelpers:
    """Test helper methods for database integration."""

    @pytest.fixture
    def mock_session(self):
        """Create a mocked LinkedInSession."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                with patch.dict('os.environ', {'COOKIE_ENCRYPTION_KEY': 'rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs='}):
                    yield LinkedInSession(headless=True)

    def test_convert_scraped_data_to_job_record(self, mock_session):
        """
        Test conversion of scraped data dictionary to JobRecord.

        Verifies that scraped job data is properly converted to JobRecord objects
        with appropriate field mapping and data validation.
        """
        scraped_data = {
            'job_id': 'linkedin_12345',
            'title': 'Senior Software Engineer',
            'company': 'TechCorp Inc.',
            'work_type': 'Remote',
            'location': 'San Francisco, CA',
            'salary': '$130K/yr - $160K/yr',
            'benefits': 'Health, Dental, Vision, 401k',
            'url': 'https://www.linkedin.com/jobs/view/12345',
            'description': 'Build amazing software products...'
        }

        # This method would be a helper in the actual implementation
        job_record = mock_session._scraped_data_to_job_record(scraped_data)

        assert isinstance(job_record, JobRecord)
        assert job_record.job_id == 'linkedin_12345'
        assert job_record.title == 'Senior Software Engineer'
        assert job_record.company == 'TechCorp Inc.'
        assert job_record.work_type == 'Remote'
        assert job_record.location == 'San Francisco, CA'
        assert job_record.salary == '$130K/yr - $160K/yr'
        assert job_record.benefits == 'Health, Dental, Vision, 401k'
        assert job_record.url == 'https://www.linkedin.com/jobs/view/12345'
        assert job_record.description == 'Build amazing software products...'
        assert job_record.status == 'active'  # Default
        assert job_record.source == 'linkedin'  # Default

    def test_create_scrape_session_from_parameters(self, mock_session):
        """
        Test creation of ScrapeSession from search parameters.

        Verifies that search parameters are properly serialized and stored
        in scrape session records for audit trail and repeatability.
        """
        search_params = {
            'search_terms': 'python developer',
            'location': 'remote',
            'work_type': 'remote',
            'max_results': 100
        }

        timestamp = datetime.now()
        total_jobs = 25

        # This would be a helper method in the actual implementation
        session_record = mock_session._create_scrape_session_record(
            search_params, total_jobs, timestamp
        )

        assert isinstance(session_record, ScrapeSession)
        assert session_record.timestamp == timestamp
        assert session_record.total_jobs_found == total_jobs
        assert session_record.source == 'linkedin'

        # Search criteria should be JSON-serialized
        import json
        criteria = json.loads(session_record.search_criteria)
        assert criteria['search_terms'] == 'python developer'
        assert criteria['location'] == 'remote'
        assert criteria['work_type'] == 'remote'
        assert criteria['max_results'] == 100