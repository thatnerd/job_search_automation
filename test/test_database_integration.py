"""
Integration tests for complete job scraping workflow with database storage.

These tests cover end-to-end scenarios combining LinkedIn scraping,
job description extraction, database storage, and CLI interactions.
Following TDD principles for comprehensive workflow validation.
"""

import tempfile
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock, call
import json

import pytest
import sys
sys.path.insert(0, '.')

from lib.linkedin_session import LinkedInSession
from lib.job_database import JobDatabase, JobRecord, ScrapeSession


class TestCompleteWorkflowIntegration:
    """Test complete workflow from scraping to database storage."""

    @pytest.fixture
    def temp_database(self):
        """Create a temporary database for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "integration_test.db"
            yield JobDatabase(db_path=db_path)

    @pytest.fixture
    def mock_linkedin_session(self, temp_database):
        """Create a LinkedIn session with mocked browser and real database."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                with patch.dict('os.environ', {'COOKIE_ENCRYPTION_KEY': 'rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs='}):
                    session = LinkedInSession(headless=True)
                    session.driver = MagicMock()
                    session.db = temp_database
                    yield session

    @pytest.fixture
    def sample_linkedin_job_data(self):
        """Sample job data as would be scraped from LinkedIn DOM."""
        return [
            {
                'job_id': 'integration_job_1',
                'title': 'Senior Python Developer',
                'company': 'TechCorp',
                'work_type': 'Remote',
                'location': 'San Francisco, CA',
                'salary': '$120K/yr - $150K/yr',
                'benefits': 'Health, Dental, 401k, Stock Options',
                'url': 'https://www.linkedin.com/jobs/view/integration_job_1',
                'description': None
            },
            {
                'job_id': 'integration_job_2',
                'title': 'Data Scientist',
                'company': 'DataCorp',
                'work_type': 'Hybrid',
                'location': 'New York, NY',
                'salary': '$110K/yr - $140K/yr',
                'benefits': 'Competitive benefits package',
                'url': 'https://www.linkedin.com/jobs/view/integration_job_2',
                'description': None
            },
            {
                'job_id': 'integration_job_3',
                'title': 'DevOps Engineer',
                'company': 'CloudCorp',
                'work_type': 'On-site',
                'location': 'Austin, TX',
                'salary': '$130K/yr - $160K/yr',
                'benefits': 'Great work-life balance',
                'url': 'https://www.linkedin.com/jobs/view/integration_job_3',
                'description': None
            }
        ]

    def test_complete_scraping_workflow_without_descriptions(self, mock_linkedin_session, sample_linkedin_job_data):
        """
        Test complete job scraping workflow without description extraction.

        Verifies that jobs are properly scraped, stored in database,
        and linked to scrape sessions for audit trail.
        """
        session = mock_linkedin_session

        # Mock the scraping method
        with patch.object(session, '_scrape_job_listings') as mock_scrape:
            mock_scrape.return_value = sample_linkedin_job_data

            # Perform the scraping workflow
            result = session.scrape_jobs_to_database(
                search_terms="python developer",
                location="remote"
            )

            # Verify workflow completed successfully
            assert result is not None
            assert 'session_id' in result
            assert 'jobs_processed' in result
            assert 'new_jobs' in result
            assert result['jobs_processed'] == 3
            assert result['new_jobs'] == 3

            # Verify jobs were stored in database
            for job_data in sample_linkedin_job_data:
                stored_job = session.db.get_job(job_data['job_id'])
                assert stored_job is not None
                assert stored_job['title'] == job_data['title']
                assert stored_job['company'] == job_data['company']
                assert stored_job['salary'] == job_data['salary']
                assert stored_job['status'] == 'active'
                assert stored_job['source'] == 'linkedin'

            # Verify generated salary columns were computed
            job1 = session.db.get_job('integration_job_1')
            assert job1['salary_min_yearly'] == 120000
            assert job1['salary_max_yearly'] == 150000

            # Verify scrape session was created
            session_id = result['session_id']
            with sqlite3.connect(session.db.db_path) as conn:
                session_data = conn.execute(
                    "SELECT * FROM scrape_sessions WHERE session_id = ?",
                    (session_id,)
                ).fetchone()
                assert session_data is not None
                assert session_data[2] == 3  # total_jobs_found
                assert session_data[3] == 3  # new_jobs_added

            # Verify job-session mappings were created
            with sqlite3.connect(session.db.db_path) as conn:
                mappings = conn.execute(
                    "SELECT * FROM job_session_mapping WHERE session_id = ?",
                    (session_id,)
                ).fetchall()
                assert len(mappings) == 3

    def test_complete_scraping_workflow_with_descriptions(self, mock_linkedin_session, sample_linkedin_job_data):
        """
        Test complete job scraping workflow with description extraction.

        Verifies that job descriptions are extracted and stored along
        with basic job data.
        """
        session = mock_linkedin_session

        # Mock scraping and description extraction
        with patch.object(session, '_scrape_job_listings') as mock_scrape:
            with patch.object(session, '_extract_job_description') as mock_extract:
                mock_scrape.return_value = sample_linkedin_job_data

                # Mock description extraction for each job
                descriptions = [
                    "Build scalable Python applications using Django and Flask. Work with microservices architecture and containerized deployments.",
                    "Analyze complex datasets using Python, SQL, and machine learning frameworks. Create predictive models and data visualizations.",
                    "Manage cloud infrastructure on AWS and Azure. Implement CI/CD pipelines and monitoring solutions."
                ]
                mock_extract.side_effect = descriptions

                # Perform scraping with description extraction
                result = session.scrape_jobs_with_descriptions_to_database(
                    search_terms="senior engineer",
                    max_descriptions=3
                )

                # Verify workflow completed successfully
                assert result is not None
                assert result['jobs_processed'] == 3
                assert result['descriptions_extracted'] == 3

                # Verify description extraction was called for each job
                assert mock_extract.call_count == 3

                # Verify descriptions were stored
                for i, job_data in enumerate(sample_linkedin_job_data):
                    stored_job = session.db.get_job(job_data['job_id'])
                    assert stored_job['description'] == descriptions[i]

                # Verify FTS table was populated with descriptions
                with sqlite3.connect(session.db.db_path) as conn:
                    fts_results = conn.execute(
                        "SELECT job_id FROM jobs_fts WHERE jobs_fts MATCH 'Python'"
                    ).fetchall()
                    assert len(fts_results) == 2  # Two jobs mention Python

    def test_incremental_scraping_with_updates(self, mock_linkedin_session, sample_linkedin_job_data):
        """
        Test incremental scraping where some jobs are new and others are updates.

        Verifies that the workflow properly handles job deduplication
        and updates existing records when data changes.
        """
        session = mock_linkedin_session

        # First scraping run
        with patch.object(session, '_scrape_job_listings') as mock_scrape:
            mock_scrape.return_value = sample_linkedin_job_data

            first_result = session.scrape_jobs_to_database(search_terms="test")

            assert first_result['new_jobs'] == 3
            assert first_result['updated_jobs'] == 0

        # Second scraping run with some updated data
        updated_job_data = sample_linkedin_job_data.copy()
        updated_job_data[0] = {
            'job_id': 'integration_job_1',  # Same job ID
            'title': 'Lead Python Developer',  # Updated title
            'company': 'TechCorp',
            'work_type': 'Remote',
            'location': 'San Francisco, CA',
            'salary': '$140K/yr - $170K/yr',  # Updated salary
            'benefits': 'Health, Dental, 401k, Stock Options, Unlimited PTO',  # Updated benefits
            'url': 'https://www.linkedin.com/jobs/view/integration_job_1',
            'description': None
        }

        # Add a new job
        updated_job_data.append({
            'job_id': 'integration_job_4',
            'title': 'Frontend Developer',
            'company': 'WebCorp',
            'work_type': 'Remote',
            'location': 'Remote',
            'salary': '$100K/yr - $130K/yr',
            'benefits': 'Standard benefits',
            'url': 'https://www.linkedin.com/jobs/view/integration_job_4',
            'description': None
        })

        with patch.object(session, '_scrape_job_listings') as mock_scrape:
            mock_scrape.return_value = updated_job_data

            second_result = session.scrape_jobs_to_database(search_terms="test")

            assert second_result['new_jobs'] == 1  # Only the new job
            assert second_result['updated_jobs'] == 1  # The updated job

            # Verify the update was applied
            updated_job = session.db.get_job('integration_job_1')
            assert updated_job['title'] == 'Lead Python Developer'
            assert updated_job['salary'] == '$140K/yr - $170K/yr'
            assert updated_job['salary_min_yearly'] == 140000
            assert updated_job['salary_max_yearly'] == 170000

            # Verify the new job was added
            new_job = session.db.get_job('integration_job_4')
            assert new_job is not None
            assert new_job['title'] == 'Frontend Developer'

    def test_error_recovery_during_workflow(self, mock_linkedin_session, sample_linkedin_job_data):
        """
        Test workflow error recovery and partial success handling.

        Verifies that failures in individual job processing don't
        prevent successful processing of other jobs.
        """
        session = mock_linkedin_session

        with patch.object(session, '_scrape_job_listings') as mock_scrape:
            with patch.object(session, '_extract_job_description') as mock_extract:
                mock_scrape.return_value = sample_linkedin_job_data

                # Simulate description extraction failure for second job
                def description_side_effect(url):
                    if 'integration_job_2' in url:
                        raise Exception("Failed to extract description")
                    elif 'integration_job_1' in url:
                        return "Successfully extracted description 1"
                    elif 'integration_job_3' in url:
                        return "Successfully extracted description 3"

                mock_extract.side_effect = description_side_effect

                # Should continue processing despite individual failures
                result = session.scrape_jobs_with_descriptions_to_database(
                    search_terms="test",
                    max_descriptions=3
                )

                # All jobs should still be processed
                assert result['jobs_processed'] == 3
                assert result['descriptions_extracted'] == 2  # 2 successful, 1 failed

                # Verify successful descriptions were stored
                job1 = session.db.get_job('integration_job_1')
                job2 = session.db.get_job('integration_job_2')
                job3 = session.db.get_job('integration_job_3')

                assert job1['description'] == "Successfully extracted description 1"
                assert job2['description'] is None  # Failed extraction
                assert job3['description'] == "Successfully extracted description 3"

    def test_workflow_with_job_lifecycle_management(self, mock_linkedin_session, sample_linkedin_job_data):
        """
        Test complete workflow including job lifecycle management.

        Verifies that jobs not found in latest scrape are marked as 'removed'
        to track job posting lifecycle.
        """
        session = mock_linkedin_session

        # Initial scraping with all jobs
        with patch.object(session, '_scrape_job_listings') as mock_scrape:
            mock_scrape.return_value = sample_linkedin_job_data

            first_result = session.scrape_jobs_to_database(search_terms="test")
            assert first_result['new_jobs'] == 3

        # Second scraping with only some jobs still available
        remaining_jobs = sample_linkedin_job_data[:2]  # Only first two jobs
        with patch.object(session, '_scrape_job_listings') as mock_scrape:
            mock_scrape.return_value = remaining_jobs

            second_result = session.scrape_jobs_to_database(search_terms="test")

            # Mark missing jobs as removed
            active_job_ids = [job['job_id'] for job in remaining_jobs]
            removed_count = session.db.mark_jobs_removed(active_job_ids)

            assert removed_count == 1  # integration_job_3 should be marked removed

            # Verify job statuses
            job1 = session.db.get_job('integration_job_1')
            job2 = session.db.get_job('integration_job_2')
            job3 = session.db.get_job('integration_job_3')

            assert job1['status'] == 'active'
            assert job2['status'] == 'active'
            assert job3['status'] == 'removed'

    def test_workflow_performance_with_large_dataset(self, mock_linkedin_session):
        """
        Test workflow performance and database efficiency with larger datasets.

        Verifies that the workflow can handle reasonable numbers of jobs
        without performance issues.
        """
        session = mock_linkedin_session

        # Generate a larger dataset (50 jobs)
        large_job_dataset = []
        for i in range(50):
            large_job_dataset.append({
                'job_id': f'perf_test_job_{i:03d}',
                'title': f'Software Engineer {i}',
                'company': f'Company_{i % 10}',  # 10 different companies
                'work_type': ['Remote', 'Hybrid', 'On-site'][i % 3],
                'location': f'City_{i % 5}, State',  # 5 different locations
                'salary': f'${90 + i}K/yr - ${120 + i}K/yr',
                'benefits': 'Standard benefits package',
                'url': f'https://www.linkedin.com/jobs/view/perf_test_job_{i:03d}',
                'description': None
            })

        with patch.object(session, '_scrape_job_listings') as mock_scrape:
            mock_scrape.return_value = large_job_dataset

            # Test workflow performance
            import time
            start_time = time.time()

            result = session.scrape_jobs_to_database(search_terms="performance test")

            end_time = time.time()
            processing_time = end_time - start_time

            # Verify all jobs were processed
            assert result['jobs_processed'] == 50
            assert result['new_jobs'] == 50

            # Performance should be reasonable (less than 5 seconds for 50 jobs)
            assert processing_time < 5.0

            # Verify database integrity
            stats = session.db.get_stats()
            assert stats['total_jobs'] == 50
            assert stats['active_jobs'] == 50
            assert len(stats['top_companies']) == 10  # 10 different companies


class TestCLIWorkflowIntegration:
    """Test CLI integration with complete workflows."""

    def test_cli_search_after_scraping_workflow(self, temp_database):
        """
        Test CLI search functionality after completing a scraping workflow.

        Verifies that jobs scraped via the workflow can be properly
        searched and displayed through the CLI interface.
        """
        # First, populate database with scraped jobs
        job_data = [
            JobRecord(
                job_id='cli_integration_1',
                title='Python Developer',
                company='TechCorp',
                work_type='Remote',
                salary='$100K/yr - $120K/yr',
                location='San Francisco, CA'
            ),
            JobRecord(
                job_id='cli_integration_2',
                title='Data Scientist',
                company='DataCorp',
                work_type='Hybrid',
                salary='$110K/yr - $140K/yr',
                location='New York, NY'
            )
        ]

        for job in job_data:
            temp_database.upsert_job(job)

        # Test CLI search functionality
        from script.linkedin_auth import main
        from io import StringIO

        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.JobDatabase') as mock_db_class:
                mock_docopt.return_value = {
                    'search-jobs': True,
                    '<query>': 'Python',
                    '--company': None,
                    '--location': None,
                    '--work-type': None,
                    '--min-salary': None,
                    '--max-salary': None,
                    '--limit': '100',
                    'login': False,
                    'db-stats': False,
                    'decrypt-cookies': False
                }

                # Mock database to return our test data
                mock_db_class.return_value = temp_database

                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    main()

                output = mock_stdout.getvalue()
                assert "Python Developer" in output
                assert "TechCorp" in output
                assert "$100K/yr - $120K/yr" in output

    def test_cli_stats_after_scraping_workflow(self, temp_database):
        """
        Test CLI statistics display after completing scraping workflows.

        Verifies that database statistics accurately reflect the results
        of scraping workflows.
        """
        # Populate database with diverse job data
        companies = ['TechCorp', 'DataCorp', 'WebCorp', 'TechCorp']
        work_types = ['Remote', 'Hybrid', 'On-site', 'Remote']
        statuses = ['active', 'active', 'removed', 'active']

        for i in range(4):
            job = JobRecord(
                job_id=f'stats_test_{i}',
                title=f'Developer {i}',
                company=companies[i],
                work_type=work_types[i],
                status=statuses[i]
            )
            temp_database.upsert_job(job)

        # Create scrape sessions
        session1 = ScrapeSession(
            timestamp=datetime.now(),
            total_jobs_found=4,
            new_jobs_added=4
        )
        session2 = ScrapeSession(
            timestamp=datetime.now(),
            total_jobs_found=2,
            new_jobs_added=0
        )

        temp_database.create_scrape_session(session1)
        temp_database.create_scrape_session(session2)

        # Test CLI stats functionality
        from script.linkedin_auth import main
        from io import StringIO

        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.JobDatabase') as mock_db_class:
                mock_docopt.return_value = {
                    'search-jobs': False,
                    'db-stats': True,
                    'login': False,
                    'decrypt-cookies': False
                }

                mock_db_class.return_value = temp_database

                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    main()

                output = mock_stdout.getvalue()

                # Verify statistics are displayed correctly
                assert "Total Jobs: 4" in output
                assert "Active Jobs: 3" in output  # 3 active, 1 removed
                assert "Total Scrape Sessions: 2" in output

                # Verify breakdowns
                assert "active: 3" in output
                assert "removed: 1" in output
                assert "TechCorp: 2" in output  # Most common company
                assert "Remote: 2" in output   # Most common work type


class TestWorkflowEdgeCases:
    """Test edge cases and error conditions in workflows."""

    @pytest.fixture
    def temp_database(self):
        """Create a temporary database for edge case testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "edge_test.db"
            yield JobDatabase(db_path=db_path)

    def test_workflow_with_duplicate_job_ids(self, temp_database):
        """
        Test workflow handling when scraping returns duplicate job IDs.

        Verifies that duplicate job IDs within a single scraping session
        are handled appropriately.
        """
        # Create mock session
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                with patch.dict('os.environ', {'COOKIE_ENCRYPTION_KEY': 'rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs='}):
                    session = LinkedInSession(headless=True)
                    session.driver = MagicMock()
                    session.db = temp_database

        duplicate_job_data = [
            {
                'job_id': 'duplicate_test',
                'title': 'First Version',
                'company': 'TechCorp'
            },
            {
                'job_id': 'duplicate_test',  # Same job ID
                'title': 'Second Version',
                'company': 'TechCorp'
            }
        ]

        with patch.object(session, '_scrape_job_listings') as mock_scrape:
            mock_scrape.return_value = duplicate_job_data

            result = session.scrape_jobs_to_database(search_terms="test")

            # Should handle duplicates gracefully (behavior depends on implementation)
            # Typically, the last occurrence would be the one stored
            stored_job = temp_database.get_job('duplicate_test')
            assert stored_job is not None

    def test_workflow_with_empty_scrape_results(self, temp_database):
        """
        Test workflow handling when scraping returns no results.

        Verifies that empty scraping results are handled gracefully
        without errors.
        """
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                with patch.dict('os.environ', {'COOKIE_ENCRYPTION_KEY': 'rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs='}):
                    session = LinkedInSession(headless=True)
                    session.driver = MagicMock()
                    session.db = temp_database

        with patch.object(session, '_scrape_job_listings') as mock_scrape:
            mock_scrape.return_value = []  # Empty results

            result = session.scrape_jobs_to_database(search_terms="nonexistent")

            # Should complete successfully with empty results
            assert result is not None
            assert result['jobs_processed'] == 0
            assert result['new_jobs'] == 0

    def test_workflow_with_malformed_job_data(self, temp_database):
        """
        Test workflow handling of malformed or incomplete job data.

        Verifies that jobs with missing required fields or invalid data
        are handled appropriately without breaking the workflow.
        """
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                with patch.dict('os.environ', {'COOKIE_ENCRYPTION_KEY': 'rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs='}):
                    session = LinkedInSession(headless=True)
                    session.driver = MagicMock()
                    session.db = temp_database

        malformed_job_data = [
            {
                'job_id': 'malformed_1',
                'title': 'Valid Job',
                'company': 'TechCorp'
                # Missing optional fields - should be OK
            },
            {
                # Missing job_id - should be handled gracefully
                'title': 'No Job ID',
                'company': 'DataCorp'
            },
            {
                'job_id': 'malformed_3',
                'title': None,  # None title
                'company': '',  # Empty company
                'salary': 'Invalid salary format'
            }
        ]

        with patch.object(session, '_scrape_job_listings') as mock_scrape:
            mock_scrape.return_value = malformed_job_data

            # Should handle malformed data without crashing
            result = session.scrape_jobs_to_database(search_terms="test")

            # Implementation should skip invalid jobs or handle them gracefully
            assert result is not None
            # Exact behavior depends on implementation error handling