"""
Tests for LinkedIn job data extraction from actual DOM structure.

These tests expose critical issues with the current job data extraction logic:
1. Company, location, and salary are in SEPARATE DOM elements, not a combined subtitle
2. Current implementation incorrectly tries to split on "·" separators
3. Missing extraction of useful metadata (promoted status, connections, etc.)

Based on real LinkedIn HTML analysis, the actual DOM structure is:
- Company: .artdeco-entity-lockup__subtitle span (separate element)
- Location: .artdeco-entity-lockup__caption .job-card-container__metadata-wrapper span
- Salary: .artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span
- Promoted: .job-card-container__footer-item span
- Connections: .job-card-container__job-insight-text

These tests follow TDD principles - they should FAIL initially and guide us
to the correct implementation that matches LinkedIn's actual DOM structure.
"""

import pytest
import sys
from unittest.mock import MagicMock, patch
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, '.')
from lib.linkedin_session import LinkedInSession


class TestLinkedInDOMExtraction:
    """Test LinkedIn job data extraction from correct DOM structure."""

    @pytest.fixture
    def session(self):
        """Create a LinkedInSession instance for testing."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                return LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=', headless=True)

    def test_company_name_extracted_from_separate_subtitle_element(self, session):
        """
        Test that company name is extracted from the correct separate DOM element.

        EXPECTED TO FAIL: Current implementation tries to parse from combined subtitle.
        Should extract from: .artdeco-entity-lockup__subtitle span (separate element).

        Real LinkedIn DOM structure:
        <div class="artdeco-entity-lockup__subtitle ember-view">
            <span class="XmAWZhYFKVGPMBtyUKWTbDvwSIcVeNHUcxi" dir="ltr">
                <!---->Datadog<!---->
            </span>
        </div>
        """
        # Mock job element with real LinkedIn DOM structure
        mock_job_element = MagicMock()

        # Mock company element (separate from location/salary)
        mock_company_element = MagicMock()
        mock_company_element.text = "Datadog"

        # Mock that company is found in separate subtitle element
        def mock_find_element_side_effect(by, selector):
            if selector == ".artdeco-entity-lockup__subtitle span":
                return mock_company_element
            else:
                # Other selectors should not find company
                raise Exception(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Extract job data
        job_data = session._extract_job_data(mock_job_element, 0)

        # Should extract company name from separate element
        assert job_data is not None, "Job data extraction should succeed"
        assert "company" in job_data, "Should extract company field"
        assert job_data["company"] == "Datadog", f"Expected 'Datadog', got '{job_data.get('company')}'"

    def test_location_extracted_from_separate_caption_element(self, session):
        """
        Test that location is extracted from the correct separate DOM element.

        EXPECTED TO FAIL: Current implementation tries to parse from combined subtitle.
        Should extract from: .artdeco-entity-lockup__caption .job-card-container__metadata-wrapper span

        Real LinkedIn DOM structure:
        <div class="artdeco-entity-lockup__caption ember-view">
            <ul class="job-card-container__metadata-wrapper">
                <li>
                    <span dir="ltr"><!---->New York, NY<!----></span>
                </li>
            </ul>
        </div>
        """
        # Mock job element with real LinkedIn DOM structure
        mock_job_element = MagicMock()

        # Mock location element
        mock_location_element = MagicMock()
        mock_location_element.text = "New York, NY"

        # Mock that location is found in caption element
        def mock_find_element_side_effect(by, selector):
            if selector == ".artdeco-entity-lockup__caption .job-card-container__metadata-wrapper span":
                return mock_location_element
            else:
                raise Exception(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Extract job data
        job_data = session._extract_job_data(mock_job_element, 0)

        # Should extract location from separate element
        assert job_data is not None, "Job data extraction should succeed"
        assert "location" in job_data, "Should extract location field"
        assert job_data["location"] == "New York, NY", f"Expected 'New York, NY', got '{job_data.get('location')}'"

    def test_salary_extracted_from_separate_metadata_element(self, session):
        """
        Test that salary is extracted from the correct separate DOM element.

        EXPECTED TO FAIL: Current implementation tries to parse from combined subtitle.
        Should extract from: .artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span

        Real LinkedIn DOM structure:
        <div class="mt1 t-sans t-12 t-black--light t-normal t-roman artdeco-entity-lockup__metadata ember-view">
            <ul class="job-card-container__metadata-wrapper">
                <li>
                    <span dir="ltr"><!---->$116K/yr - $169K/yr · 401(k) benefit<!----></span>
                </li>
            </ul>
        </div>
        """
        # Mock job element with real LinkedIn DOM structure
        mock_job_element = MagicMock()

        # Mock salary element
        mock_salary_element = MagicMock()
        mock_salary_element.text = "$116K/yr - $169K/yr · 401(k) benefit"

        # Mock that salary is found in metadata element
        def mock_find_element_side_effect(by, selector):
            if selector == ".artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span":
                return mock_salary_element
            else:
                raise Exception(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Extract job data
        job_data = session._extract_job_data(mock_job_element, 0)

        # Should extract salary from separate element
        assert job_data is not None, "Job data extraction should succeed"
        assert "salary" in job_data, "Should extract salary field"
        assert job_data["salary"] == "$116K/yr - $169K/yr · 401(k) benefit", \
            f"Expected '$116K/yr - $169K/yr · 401(k) benefit', got '{job_data.get('salary')}'"

    def test_promoted_status_extracted_from_footer_element(self, session):
        """
        Test that 'Promoted' status is extracted from footer element.

        EXPECTED TO FAIL: Current implementation doesn't extract promoted status.
        Should extract from: .job-card-container__footer-item span

        Real LinkedIn DOM structure:
        <ul class="job-card-list__footer-wrapper job-card-container__footer-wrapper">
            <li class="job-card-container__footer-item">
                <span dir="ltr"><!---->Promoted<!----></span>
            </li>
        </ul>
        """
        # Mock job element with real LinkedIn DOM structure
        mock_job_element = MagicMock()

        # Mock promoted element
        mock_promoted_element = MagicMock()
        mock_promoted_element.text = "Promoted"

        # Mock that promoted status is found in footer
        def mock_find_element_side_effect(by, selector):
            if selector == ".job-card-container__footer-item span":
                return mock_promoted_element
            else:
                raise Exception(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Extract job data
        job_data = session._extract_job_data(mock_job_element, 0)

        # Should extract promoted status
        assert job_data is not None, "Job data extraction should succeed"
        assert "promoted" in job_data, "Should extract promoted field"
        assert job_data["promoted"] is True, f"Expected promoted=True, got '{job_data.get('promoted')}'"

    def test_connections_insight_extracted_from_insight_element(self, session):
        """
        Test that connection insights are extracted from correct element.

        EXPECTED TO FAIL: Current implementation doesn't extract connection insights.
        Should extract from: .job-card-container__job-insight-text

        Real LinkedIn DOM structure:
        <div class="job-card-list__insight">
            <div class="display-flex align-items-center t-black--light t-12">
                <div class="job-card-container__job-insight-text" dir="ltr">
                    <!---->9 connections work here<!---->
                </div>
            </div>
        </div>
        """
        # Mock job element with real LinkedIn DOM structure
        mock_job_element = MagicMock()

        # Mock connections insight element
        mock_insight_element = MagicMock()
        mock_insight_element.text = "9 connections work here"

        # Mock that insight is found
        def mock_find_element_side_effect(by, selector):
            if selector == ".job-card-container__job-insight-text":
                return mock_insight_element
            else:
                raise Exception(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Extract job data
        job_data = session._extract_job_data(mock_job_element, 0)

        # Should extract connection insight
        assert job_data is not None, "Job data extraction should succeed"
        assert "connections_insight" in job_data, "Should extract connections_insight field"
        assert job_data["connections_insight"] == "9 connections work here", \
            f"Expected '9 connections work here', got '{job_data.get('connections_insight')}'"

    def test_current_implementation_fails_with_separate_elements(self, session):
        """
        Test that current implementation fails because it expects combined subtitle.

        EXPECTED TO PASS: This test verifies the current broken behavior.
        Current implementation looks for combined subtitle with "·" separators,
        but real LinkedIn DOM has separate elements.
        """
        # Mock job element with separate elements (real LinkedIn structure)
        mock_job_element = MagicMock()

        # Mock separate elements for company, location, salary
        mock_company_element = MagicMock()
        mock_company_element.text = "Datadog"

        mock_location_element = MagicMock()
        mock_location_element.text = "New York, NY"

        mock_salary_element = MagicMock()
        mock_salary_element.text = "$116K/yr - $169K/yr"

        # Mock that the OLD selector (current implementation) finds no combined text
        def mock_find_element_side_effect(by, selector):
            if selector == ".artdeco-entity-lockup__subtitle span":
                # Current implementation expects combined text like "Company · Location · Salary"
                # But real DOM only has company name
                return mock_company_element
            else:
                raise Exception(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Extract job data with current implementation
        job_data = session._extract_job_data(mock_job_element, 0)

        # Current implementation should fail to extract location and salary
        # because it expects them to be in the same element as company
        if job_data:
            # If current implementation tries to parse "Datadog" as "Company · Location · Salary"
            # it will fail to extract location and salary properly

            # Company might be extracted (if it's the first part)
            company = job_data.get("company", "")

            # But location and salary will be missing or wrong
            location = job_data.get("location", "")
            salary = job_data.get("salary", "")

            # Current implementation should NOT extract location from separate element
            assert location != "New York, NY", \
                "Current implementation incorrectly extracted location from separate element"

            # Current implementation should NOT extract salary from separate element
            assert salary != "$116K/yr - $169K/yr", \
                "Current implementation incorrectly extracted salary from separate element"

    def test_complete_job_extraction_with_correct_selectors(self, session):
        """
        Test complete job extraction using the correct DOM selectors.

        EXPECTED TO FAIL: Current implementation doesn't use correct selectors.
        Should extract all fields from their proper separate DOM elements.
        """
        # Mock job element with full LinkedIn DOM structure
        mock_job_element = MagicMock()

        # Mock title element
        mock_title_element = MagicMock()
        mock_title_element.text = "Senior Software Engineer"
        mock_title_element.get_attribute.return_value = "https://linkedin.com/jobs/view/12345"

        # Mock separate elements for each data field
        mock_company_element = MagicMock()
        mock_company_element.text = "Datadog"

        mock_location_element = MagicMock()
        mock_location_element.text = "New York, NY"

        mock_salary_element = MagicMock()
        mock_salary_element.text = "$116K/yr - $169K/yr · 401(k) benefit"

        mock_promoted_element = MagicMock()
        mock_promoted_element.text = "Promoted"

        mock_insight_element = MagicMock()
        mock_insight_element.text = "9 connections work here"

        # Mock element finding with correct selectors
        def mock_find_element_side_effect(by, selector):
            selector_mapping = {
                "a.job-card-container__link": mock_title_element,
                ".artdeco-entity-lockup__subtitle span": mock_company_element,
                ".artdeco-entity-lockup__caption .job-card-container__metadata-wrapper span": mock_location_element,
                ".artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span": mock_salary_element,
                ".job-card-container__footer-item span": mock_promoted_element,
                ".job-card-container__job-insight-text": mock_insight_element,
            }

            if selector in selector_mapping:
                return selector_mapping[selector]
            else:
                raise Exception(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Extract job data
        job_data = session._extract_job_data(mock_job_element, 0)

        # Should extract all fields from correct elements
        assert job_data is not None, "Job data extraction should succeed"

        expected_fields = {
            "title": "Senior Software Engineer",
            "company": "Datadog",
            "location": "New York, NY",
            "salary": "$116K/yr - $169K/yr · 401(k) benefit",
            "promoted": True,
            "connections_insight": "9 connections work here",
            "url": "https://linkedin.com/jobs/view/12345"
        }

        for field, expected_value in expected_fields.items():
            assert field in job_data, f"Should extract {field} field"
            assert job_data[field] == expected_value, \
                f"Field {field}: expected '{expected_value}', got '{job_data.get(field)}'"

    def test_salary_benefits_parsing_from_metadata_element(self, session):
        """
        Test that salary and benefits are properly parsed from metadata element.

        EXPECTED TO FAIL: Current implementation doesn't handle salary with benefits.
        Should parse salary range and separate benefits information.
        """
        # Mock job element
        mock_job_element = MagicMock()

        # Mock salary element with benefits
        mock_salary_element = MagicMock()
        mock_salary_element.text = "$116K/yr - $169K/yr · 401(k) benefit"

        def mock_find_element_side_effect(by, selector):
            if selector == ".artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span":
                return mock_salary_element
            else:
                raise Exception(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Extract job data
        job_data = session._extract_job_data(mock_job_element, 0)

        # Should parse salary and benefits separately
        assert job_data is not None, "Job data extraction should succeed"
        assert "salary" in job_data, "Should extract salary field"
        assert "benefits" in job_data, "Should extract benefits field"

        # Salary should be the range part
        assert "$116K/yr - $169K/yr" in job_data["salary"], \
            f"Salary should contain range, got: '{job_data.get('salary')}'"

        # Benefits should be extracted separately
        assert "401(k) benefit" in job_data["benefits"], \
            f"Benefits should contain '401(k) benefit', got: '{job_data.get('benefits')}'"

    def test_work_type_extraction_from_location_parentheses(self, session):
        """
        Test that work type (Remote, Hybrid) is extracted from location parentheses.

        EXPECTED TO FAIL: Current implementation might not extract work type.
        Should extract work type from location like "New York, NY (Hybrid)".
        """
        # Mock job element
        mock_job_element = MagicMock()

        # Mock location with work type in parentheses
        mock_location_element = MagicMock()
        mock_location_element.text = "New York, NY (Hybrid)"

        def mock_find_element_side_effect(by, selector):
            if selector == ".artdeco-entity-lockup__caption .job-card-container__metadata-wrapper span":
                return mock_location_element
            else:
                raise Exception(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Extract job data
        job_data = session._extract_job_data(mock_job_element, 0)

        # Should extract location and work type separately
        assert job_data is not None, "Job data extraction should succeed"
        assert "location" in job_data, "Should extract location field"
        assert "work_type" in job_data, "Should extract work_type field"

        # Location should be cleaned (without parentheses)
        assert job_data["location"] == "New York, NY", \
            f"Expected clean location 'New York, NY', got '{job_data.get('location')}'"

        # Work type should be extracted from parentheses
        assert job_data["work_type"] == "Hybrid", \
            f"Expected work_type 'Hybrid', got '{job_data.get('work_type')}'"

    def test_job_state_extraction_from_footer(self, session):
        """
        Test that job state (Viewed, Applied, etc.) is extracted from footer.

        EXPECTED TO FAIL: Current implementation doesn't extract job state.
        Should extract from: .job-card-container__footer-job-state

        Real LinkedIn DOM structure:
        <li class="job-card-container__footer-item job-card-container__footer-job-state t-bold">
            Viewed
        </li>
        """
        # Mock job element
        mock_job_element = MagicMock()

        # Mock job state element
        mock_state_element = MagicMock()
        mock_state_element.text = "Viewed"

        def mock_find_element_side_effect(by, selector):
            if selector == ".job-card-container__footer-job-state":
                return mock_state_element
            else:
                raise Exception(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Extract job data
        job_data = session._extract_job_data(mock_job_element, 0)

        # Should extract job state
        assert job_data is not None, "Job data extraction should succeed"
        assert "job_state" in job_data, "Should extract job_state field"
        assert job_data["job_state"] == "Viewed", \
            f"Expected job_state 'Viewed', got '{job_data.get('job_state')}'"

    def test_multiple_metadata_elements_handling(self, session):
        """
        Test handling of multiple metadata elements (salary, benefits, etc.).

        EXPECTED TO FAIL: Current implementation doesn't handle multiple metadata.
        Should find and process all metadata spans in the metadata wrapper.
        """
        # Mock job element
        mock_job_element = MagicMock()

        # Mock multiple metadata elements
        mock_salary_span = MagicMock()
        mock_salary_span.text = "$116K/yr - $169K/yr"

        mock_benefits_span = MagicMock()
        mock_benefits_span.text = "401(k) benefit"

        # Mock find_elements (plural) to return multiple spans
        def mock_find_elements_side_effect(by, selector):
            if selector == ".artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span":
                return [mock_salary_span, mock_benefits_span]
            else:
                return []

        mock_job_element.find_elements.side_effect = mock_find_elements_side_effect

        # Also need to handle find_element (singular) calls
        def mock_find_element_side_effect(by, selector):
            raise Exception(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Extract job data
        job_data = session._extract_job_data(mock_job_element, 0)

        # Should process multiple metadata elements
        assert job_data is not None, "Job data extraction should succeed"

        # Should extract both salary and benefits from separate spans
        assert "salary" in job_data, "Should extract salary from first metadata span"
        assert "benefits" in job_data, "Should extract benefits from second metadata span"

        assert job_data["salary"] == "$116K/yr - $169K/yr", \
            f"Expected salary '$116K/yr - $169K/yr', got '{job_data.get('salary')}'"

        assert job_data["benefits"] == "401(k) benefit", \
            f"Expected benefits '401(k) benefit', got '{job_data.get('benefits')}'"


class TestCurrentImplementationFailures:
    """Test cases that demonstrate how the current implementation fails."""

    @pytest.fixture
    def session(self):
        """Create a LinkedInSession instance for testing."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                return LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=', headless=True)

    def test_current_combined_subtitle_parsing_fails(self, session):
        """
        Test that current subtitle parsing approach fails with real DOM structure.

        Current implementation expects: "Company · Location · Salary"
        Real LinkedIn DOM has: separate elements for each field.

        EXPECTED TO PASS: This documents the current failing behavior.
        """
        # Mock job element that matches real LinkedIn DOM
        mock_job_element = MagicMock()

        # Real LinkedIn has company in subtitle, but NOT combined with location/salary
        mock_subtitle_element = MagicMock()
        mock_subtitle_element.text = "Datadog"  # Only company name, no "·" separators

        def mock_find_element_side_effect(by, selector):
            if selector == ".artdeco-entity-lockup__subtitle span":
                return mock_subtitle_element
            else:
                # Current implementation doesn't look for separate location/salary elements
                raise Exception(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Extract with current implementation
        job_data = session._extract_job_data(mock_job_element, 0)

        if job_data:
            # Current implementation tries to split on "·" but won't find any
            company = job_data.get("company", "")
            location = job_data.get("location", "")
            salary = job_data.get("salary", "")

            # Should extract company (it's in the subtitle)
            assert company == "Datadog", f"Should extract company, got '{company}'"

            # Should NOT extract location (it's in a separate element)
            assert location == "" or location is None, \
                f"Should NOT extract location from subtitle, but got '{location}'"

            # Should NOT extract salary (it's in a separate element)
            assert salary == "" or salary is None, \
                f"Should NOT extract salary from subtitle, but got '{salary}'"

    def test_missing_selector_fallbacks_cause_data_loss(self, session):
        """
        Test that missing selectors for separate elements cause data loss.

        EXPECTED TO PASS: Documents how current implementation loses data.
        Current implementation doesn't have selectors for separate location/salary elements.
        """
        # Mock job element with real LinkedIn structure
        mock_job_element = MagicMock()

        # Mock that current selectors don't find the separate elements
        def mock_find_element_side_effect(by, selector):
            # Current implementation selectors
            current_selectors = [
                ".artdeco-entity-lockup__subtitle span",
                ".job-card-container__primary-description",
                ".job-card-list__title",
                "h3 a"
            ]

            # Should NOT find the correct separate elements
            correct_selectors = [
                ".artdeco-entity-lockup__caption .job-card-container__metadata-wrapper span",  # location
                ".artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span", # salary
                ".job-card-container__footer-item span", # promoted
                ".job-card-container__job-insight-text"  # connections
            ]

            if selector in current_selectors:
                # Mock basic element for current selectors
                mock_element = MagicMock()
                mock_element.text = "Basic data"
                return mock_element
            elif selector in correct_selectors:
                # Current implementation shouldn't be looking for these
                raise Exception(f"Current implementation doesn't use selector: {selector}")
            else:
                raise Exception(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Extract with current implementation
        job_data = session._extract_job_data(mock_job_element, 0)

        # Current implementation should miss the separate element data
        if job_data:
            # These fields should be missing because current implementation
            # doesn't look in the correct separate elements
            assert "promoted" not in job_data or not job_data.get("promoted"), \
                "Current implementation should not extract promoted status"

            assert "connections_insight" not in job_data or not job_data.get("connections_insight"), \
                "Current implementation should not extract connections insight"

            assert "work_type" not in job_data or not job_data.get("work_type"), \
                "Current implementation should not extract work type"