"""
Tests to ensure all job data fields are present with explicit null values when not found.

This test ensures consistent JSON schema output where all expected fields
are always present, either with actual data or explicit null values.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.linkedin_session import LinkedInSession


class TestJobDataSchema:
    """Test that job data always contains all expected fields with explicit nulls."""

    EXPECTED_FIELDS = {
        'index': int,
        'job_id': (str, type(None)),
        'url': (str, type(None)),
        'title': (str, type(None)),
        'company': (str, type(None)),
        'work_type': (str, type(None)),
        'location': (str, type(None)),
        'salary': (str, type(None)),
        'benefits': (str, type(None))
    }

    def test_job_data_has_all_expected_fields_when_all_present(self):
        """Test that job with all data present has all expected fields."""
        session = LinkedInSession(headless=True)

        # Mock element with all data present
        mock_element = Mock()

        # Mock link element with job ID
        mock_link = Mock()
        mock_link.get_attribute.return_value = "https://www.linkedin.com/jobs/view/12345/?param=value"
        mock_element.find_element.return_value = mock_link

        # Mock title
        mock_title = Mock()
        mock_title.text = "Senior Engineer"

        # Mock company
        mock_company = Mock()
        mock_company.text = "Tech Corp"

        # Mock work type
        mock_work_type = Mock()
        mock_work_type.text = "Remote"

        # Mock location
        mock_location = Mock()
        mock_location.text = "New York, NY"

        # Mock salary
        mock_salary = Mock()
        mock_salary.text = "$100K/yr - $150K/yr"

        # Mock benefits
        mock_benefits = Mock()
        mock_benefits.text = "401(k), Health"

        # Setup find_element to return appropriate mocks
        def mock_find_element(by_type, selector):
            if "jobs" in selector:
                return mock_link
            elif "job-card-container__primary-description" in selector:
                return mock_title
            elif "artdeco-entity-lockup__subtitle" in selector:
                return mock_company
            elif "job-card-container__metadata-item" in selector:
                return mock_work_type
            elif "artdeco-entity-lockup__caption" in selector:
                return mock_location
            elif "job-card-container__salary-info" in selector:
                return mock_salary
            elif "job-card-container__benefits" in selector:
                return mock_benefits
            raise NoSuchElementException()

        mock_element.find_element.side_effect = mock_find_element

        job_data = session._extract_job_data(mock_element, 0)

        # Verify all expected fields are present
        for field_name in self.EXPECTED_FIELDS:
            assert field_name in job_data, f"Field '{field_name}' missing from job_data"

        # Verify data types
        assert isinstance(job_data['index'], int)
        assert isinstance(job_data['job_id'], str)
        assert isinstance(job_data['url'], str)
        assert isinstance(job_data['title'], str)
        assert isinstance(job_data['company'], str)
        assert isinstance(job_data['work_type'], str)
        assert isinstance(job_data['location'], str)
        assert isinstance(job_data['salary'], str)
        assert isinstance(job_data['benefits'], str)

    def test_job_data_has_explicit_nulls_when_fields_missing(self):
        """Test that job with missing data has explicit null values for missing fields."""
        session = LinkedInSession(headless=True)

        # Mock element with minimal data (only title available)
        mock_element = Mock()

        # Mock title (only field present)
        mock_title = Mock()
        mock_title.text = "Engineer Position"

        # Setup find_element to only return title, everything else raises NoSuchElementException
        def mock_find_element(by_type, selector):
            if "job-card-container__primary-description" in selector:
                return mock_title
            raise NoSuchElementException()

        mock_element.find_element.side_effect = mock_find_element

        job_data = session._extract_job_data(mock_element, 0)

        # Verify all expected fields are present
        for field_name in self.EXPECTED_FIELDS:
            assert field_name in job_data, f"Field '{field_name}' missing from job_data"

        # Verify explicit nulls for missing data
        assert job_data['index'] == 1  # Always set
        assert job_data['job_id'] is None  # Missing -> explicit null
        assert job_data['url'] is None  # Missing -> explicit null
        assert job_data['title'] == "Engineer Position"  # Present
        assert job_data['company'] is None  # Missing -> explicit null
        assert job_data['work_type'] is None  # Missing -> explicit null
        assert job_data['location'] is None  # Missing -> explicit null
        assert job_data['salary'] is None  # Missing -> explicit null
        assert job_data['benefits'] is None  # Missing -> explicit null

    def test_job_data_partial_fields_present(self):
        """Test job with some fields present, others missing have explicit nulls."""
        session = LinkedInSession(headless=True)

        # Mock element with partial data
        mock_element = Mock()

        # Mock available elements
        mock_link = Mock()
        mock_link.get_attribute.return_value = "https://www.linkedin.com/jobs/view/67890/"

        mock_title = Mock()
        mock_title.text = "Data Scientist"

        mock_company = Mock()
        mock_company.text = "AI Startup"

        # Setup find_element to return some elements
        def mock_find_element(by_type, selector):
            if "jobs" in selector:
                return mock_link
            elif "job-card-container__primary-description" in selector:
                return mock_title
            elif "artdeco-entity-lockup__subtitle" in selector:
                return mock_company
            # All other selectors raise NoSuchElementException
            raise NoSuchElementException()

        mock_element.find_element.side_effect = mock_find_element

        job_data = session._extract_job_data(mock_element, 1)

        # Verify all expected fields are present
        for field_name in self.EXPECTED_FIELDS:
            assert field_name in job_data, f"Field '{field_name}' missing from job_data"

        # Verify mixed data and nulls
        assert job_data['index'] == 2
        assert job_data['job_id'] == "67890"  # Extracted from URL
        assert job_data['url'] == "https://www.linkedin.com/jobs/view/67890/"  # Present
        assert job_data['title'] == "Data Scientist"  # Present
        assert job_data['company'] == "AI Startup"  # Present
        assert job_data['work_type'] is None  # Missing -> explicit null
        assert job_data['location'] is None  # Missing -> explicit null
        assert job_data['salary'] is None  # Missing -> explicit null
        assert job_data['benefits'] is None  # Missing -> explicit null

    def test_scraped_jobs_json_schema_consistency(self):
        """Test that actual scraped job data follows consistent schema."""
        # This would test against real scraped data
        test_json_path = "/Users/will/repo/thatnerd/job_search_automation/data/test_data/test_job_id_extraction.json"

        try:
            with open(test_json_path, 'r') as f:
                data = json.load(f)

            jobs = data.get('jobs', [])
            assert len(jobs) > 0, "No jobs found in test data"

            for i, job in enumerate(jobs):
                # Verify all expected fields are present
                for field_name in self.EXPECTED_FIELDS:
                    assert field_name in job, f"Job {i}: Field '{field_name}' missing from job data"

                # Verify field types (allowing null)
                for field_name, expected_types in self.EXPECTED_FIELDS.items():
                    if not isinstance(expected_types, tuple):
                        expected_types = (expected_types,)

                    actual_value = job[field_name]
                    assert isinstance(actual_value, expected_types), \
                        f"Job {i}: Field '{field_name}' has type {type(actual_value)}, expected {expected_types}"

        except FileNotFoundError:
            pytest.skip("Test JSON file not found - run scraper first")