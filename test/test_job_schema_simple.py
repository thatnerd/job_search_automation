"""
Simple test to verify job data schema with explicit nulls.
"""

import pytest
import json
from unittest.mock import Mock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.linkedin_session import LinkedInSession


def test_scraped_jobs_have_all_required_fields():
    """Test that all scraped jobs have required fields with explicit nulls."""

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

    # Test against the actual scraped data
    test_json_path = "/Users/will/repo/thatnerd/job_search_automation/data/test_data/test_explicit_nulls.json"

    try:
        with open(test_json_path, 'r') as f:
            data = json.load(f)

        jobs = data.get('jobs', [])
        assert len(jobs) > 0, "No jobs found in test data"

        for i, job in enumerate(jobs):
            # Verify all expected fields are present
            for field_name in EXPECTED_FIELDS:
                assert field_name in job, f"Job {i}: Field '{field_name}' missing from job data"

            # Verify field types (allowing null)
            for field_name, expected_types in EXPECTED_FIELDS.items():
                if not isinstance(expected_types, tuple):
                    expected_types = (expected_types,)

                actual_value = job[field_name]
                assert isinstance(actual_value, expected_types), \
                    f"Job {i}: Field '{field_name}' has type {type(actual_value)}, expected {expected_types}. Value: {actual_value}"

        print(f"✓ All {len(jobs)} jobs have consistent schema with explicit nulls")

    except FileNotFoundError:
        pytest.skip("Test JSON file not found - run scraper first")


def test_extraction_method_returns_all_fields():
    """Test that _extract_job_data always returns all expected fields."""
    session = LinkedInSession(headless=True)

    # Create a mock element that will fail most extractions
    mock_element = Mock()
    mock_element.find_element.side_effect = Exception("No element found")
    mock_element.find_elements.return_value = []
    mock_element.get_attribute.return_value = None

    # The method should still return a job_data dict with all fields as nulls
    job_data = session._extract_job_data(mock_element, 0)

    # Verify structure exists
    assert job_data is not None, "Method should return dict, not None"
    assert isinstance(job_data, dict), "Method should return dictionary"

    # Verify all expected fields are present
    expected_fields = ['index', 'job_id', 'url', 'title', 'company', 'work_type', 'location', 'salary', 'benefits']

    for field in expected_fields:
        assert field in job_data, f"Field '{field}' missing from job_data"

    # Verify index is set correctly
    assert job_data['index'] == 1  # 0 + 1

    # Verify all other fields are null when nothing can be extracted
    for field in expected_fields[1:]:  # Skip index
        assert job_data[field] is None, f"Field '{field}' should be None but is {job_data[field]}"

    print("✓ _extract_job_data returns consistent schema even when extraction fails")