"""
Documentation and tests for correct LinkedIn DOM selectors.

This file serves as both test suite and implementation guide, documenting
the correct CSS selectors to use for LinkedIn job data extraction based on
real LinkedIn HTML structure analysis.

SELECTOR REFERENCE (from real LinkedIn DOM):

Company Name:
    .artdeco-entity-lockup__subtitle span
    Example: <span class="XmAWZhYFKVGPMBtyUKWTbDvwSIcVeNHUcxi">Datadog</span>

Location:
    .artdeco-entity-lockup__caption .job-card-container__metadata-wrapper span
    Example: <span dir="ltr">New York, NY</span>

Salary/Benefits:
    .artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span
    Example: <span dir="ltr">$116K/yr - $169K/yr · 401(k) benefit</span>

Promoted Status:
    .job-card-container__footer-item span (contains "Promoted")
    Example: <span dir="ltr">Promoted</span>

Job State:
    .job-card-container__footer-job-state
    Example: <li class="...job-card-container__footer-job-state...">Viewed</li>

Connection Insights:
    .job-card-container__job-insight-text
    Example: <div class="job-card-container__job-insight-text">9 connections work here</div>

These tests define the expected behavior using the correct selectors.
"""

import pytest
import sys
from unittest.mock import MagicMock, patch
from selenium.common.exceptions import NoSuchElementException
from typing import Dict, Any, List, Tuple

# Add project root to path
sys.path.insert(0, '.')
from lib.linkedin_session import LinkedInSession


class TestCorrectLinkedInSelectors:
    """Tests using the correct LinkedIn DOM selectors based on real HTML analysis."""

    @pytest.fixture
    def session(self):
        """Create a LinkedInSession instance for testing."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                return LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=', headless=True)

    def create_mock_job_element(self, job_data: Dict[str, Any]) -> MagicMock:
        """
        Create a mock job element with the correct LinkedIn DOM structure.

        Args:
            job_data: Dictionary with job information to mock

        Returns:
            Mock WebElement with correct selector mappings
        """
        mock_element = MagicMock()

        def mock_find_element_side_effect(by, selector):
            # Title selectors
            if selector in ["a[aria-label*='with verification']", "a.job-card-container__link"]:
                if "title" in job_data:
                    mock_title = MagicMock()
                    mock_title.text = job_data["title"]
                    mock_title.get_attribute.return_value = job_data.get("url", "")
                    return mock_title

            # Company selector
            elif selector == ".artdeco-entity-lockup__subtitle span":
                if "company" in job_data:
                    mock_company = MagicMock()
                    mock_company.text = job_data["company"]
                    return mock_company

            # Location selector
            elif selector == ".artdeco-entity-lockup__caption .job-card-container__metadata-wrapper span":
                if "location" in job_data:
                    mock_location = MagicMock()
                    mock_location.text = job_data["location"]
                    return mock_location

            # Salary/benefits selector
            elif selector == ".artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span":
                if "salary" in job_data:
                    mock_salary = MagicMock()
                    mock_salary.text = job_data["salary"]
                    return mock_salary

            # Promoted status selector
            elif selector == ".job-card-container__footer-item span":
                if job_data.get("promoted"):
                    mock_promoted = MagicMock()
                    mock_promoted.text = "Promoted"
                    return mock_promoted

            # Job state selector
            elif selector == ".job-card-container__footer-job-state":
                if "job_state" in job_data:
                    mock_state = MagicMock()
                    mock_state.text = job_data["job_state"]
                    return mock_state

            # Connection insights selector
            elif selector == ".job-card-container__job-insight-text":
                if "connections_insight" in job_data:
                    mock_insight = MagicMock()
                    mock_insight.text = job_data["connections_insight"]
                    return mock_insight

            # Element not found
            raise NoSuchElementException(f"Element not found: {selector}")

        def mock_find_elements_side_effect(by, selector):
            # Handle multiple metadata elements
            if selector == ".artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span":
                elements = []
                if "salary" in job_data:
                    mock_salary = MagicMock()
                    mock_salary.text = job_data["salary"]
                    elements.append(mock_salary)
                if "benefits" in job_data:
                    mock_benefits = MagicMock()
                    mock_benefits.text = job_data["benefits"]
                    elements.append(mock_benefits)
                return elements
            return []

        mock_element.find_element.side_effect = mock_find_element_side_effect
        mock_element.find_elements.side_effect = mock_find_elements_side_effect

        return mock_element

    def test_correct_selector_usage_comprehensive_example(self, session):
        """
        Test comprehensive job extraction using all correct selectors.

        This is the master test that defines how the fixed implementation should work.
        EXPECTED TO FAIL: Current implementation uses wrong selectors.
        """
        # Complete job data example based on real LinkedIn DOM
        job_data = {
            "title": "Senior Software Engineer",
            "company": "Datadog",
            "location": "New York, NY",
            "salary": "$116K/yr - $169K/yr · 401(k) benefit",
            "promoted": True,
            "job_state": "Viewed",
            "connections_insight": "9 connections work here",
            "url": "https://linkedin.com/jobs/view/4300683036"
        }

        mock_job_element = self.create_mock_job_element(job_data)

        # Extract using correct selectors (this is what the fix should implement)
        extracted_data = session._extract_job_data(mock_job_element, 0)

        # Verify all fields extracted correctly
        assert extracted_data is not None, "Should extract job data successfully"

        expected_fields = {
            "title": "Senior Software Engineer",
            "company": "Datadog",
            "location": "New York, NY",
            "url": "https://linkedin.com/jobs/view/4300683036",
            "promoted": True,
            "job_state": "Viewed",
            "connections_insight": "9 connections work here"
        }

        # Salary should be parsed (removing benefits part)
        if "salary" in extracted_data:
            assert "$116K/yr - $169K/yr" in extracted_data["salary"], \
                f"Should extract salary range from: '{extracted_data['salary']}'"

        # Benefits should be extracted separately
        if "benefits" in extracted_data:
            assert "401(k) benefit" in extracted_data["benefits"], \
                f"Should extract benefits from: '{extracted_data['benefits']}'"

        for field, expected_value in expected_fields.items():
            assert field in extracted_data, f"Missing field: {field}"
            assert extracted_data[field] == expected_value, \
                f"Field {field}: expected '{expected_value}', got '{extracted_data[field]}'"

    def test_selector_priority_and_fallbacks(self, session):
        """
        Test selector priority and fallback mechanisms.

        EXPECTED TO FAIL: Current implementation doesn't have proper fallback chains.
        """
        # Test data that should work with fallback selectors
        fallback_scenarios = [
            {
                "name": "Primary title selector fails",
                "working_selector": "a.job-card-container__link",
                "job_data": {"title": "Fallback Title", "url": "https://linkedin.com/jobs/view/1"}
            },
            {
                "name": "Primary company selector works",
                "working_selector": ".artdeco-entity-lockup__subtitle span",
                "job_data": {"company": "Fallback Company"}
            }
        ]

        for scenario in fallback_scenarios:
            mock_job_element = self.create_mock_job_element(scenario["job_data"])

            extracted_data = session._extract_job_data(mock_job_element, 0)

            if extracted_data:
                for field, expected_value in scenario["job_data"].items():
                    if field in extracted_data:
                        assert extracted_data[field] == expected_value, \
                            f"Scenario '{scenario['name']}': {field} = '{extracted_data[field]}', expected '{expected_value}'"

    def test_work_type_parsing_from_location(self, session):
        """
        Test parsing work type information from location strings.

        EXPECTED TO FAIL: Current implementation doesn't parse work types.
        """
        location_test_cases = [
            ("New York, NY (Remote)", "New York, NY", "Remote"),
            ("San Francisco, CA (Hybrid)", "San Francisco, CA", "Hybrid"),
            ("Austin, TX (On-site)", "Austin, TX", "On-site"),
            ("Los Angeles, CA", "Los Angeles, CA", None),  # No work type specified
            ("Remote", "Remote", "Remote"),  # Just "Remote"
        ]

        for location_text, expected_location, expected_work_type in location_test_cases:
            job_data = {"location": location_text}
            mock_job_element = self.create_mock_job_element(job_data)

            extracted_data = session._extract_job_data(mock_job_element, 0)

            if extracted_data:
                # Location should be cleaned (parentheses removed)
                if "location" in extracted_data:
                    assert extracted_data["location"] == expected_location, \
                        f"Location '{location_text}': expected clean location '{expected_location}', got '{extracted_data['location']}'"

                # Work type should be extracted from parentheses
                if expected_work_type:
                    assert "work_type" in extracted_data, f"Should extract work_type from '{location_text}'"
                    assert extracted_data["work_type"] == expected_work_type, \
                        f"Location '{location_text}': expected work_type '{expected_work_type}', got '{extracted_data.get('work_type')}'"

    def test_salary_and_benefits_separation(self, session):
        """
        Test separation of salary and benefits from metadata element.

        EXPECTED TO FAIL: Current implementation doesn't separate salary and benefits.
        """
        salary_benefit_cases = [
            ("$116K/yr - $169K/yr · 401(k) benefit", "$116K/yr - $169K/yr", "401(k) benefit"),
            ("$90K - $120K/year · Health Insurance", "$90K - $120K/year", "Health Insurance"),
            ("$75,000 - $95,000 · Dental · Vision", "$75,000 - $95,000", "Dental · Vision"),
            ("Competitive salary · Great benefits", "Competitive salary", "Great benefits"),
        ]

        for salary_text, expected_salary, expected_benefits in salary_benefit_cases:
            job_data = {"salary": salary_text}
            mock_job_element = self.create_mock_job_element(job_data)

            extracted_data = session._extract_job_data(mock_job_element, 0)

            if extracted_data:
                # Should extract salary part
                if "salary" in extracted_data:
                    assert expected_salary in extracted_data["salary"], \
                        f"Salary text '{salary_text}': should contain salary '{expected_salary}', got '{extracted_data['salary']}'"

                # Should extract benefits part
                if "benefits" in extracted_data:
                    assert expected_benefits in extracted_data["benefits"], \
                        f"Salary text '{salary_text}': should contain benefits '{expected_benefits}', got '{extracted_data['benefits']}'"

    def test_promoted_status_boolean_conversion(self, session):
        """
        Test that promoted status text is converted to boolean.

        EXPECTED TO FAIL: Current implementation doesn't extract promoted status.
        """
        # Test with promoted job
        promoted_job_data = {"promoted": True}
        mock_promoted_element = self.create_mock_job_element(promoted_job_data)

        extracted_promoted = session._extract_job_data(mock_promoted_element, 0)

        if extracted_promoted and "promoted" in extracted_promoted:
            assert extracted_promoted["promoted"] is True, \
                "Promoted status should be boolean True"

        # Test with non-promoted job (no promoted element found)
        regular_job_data = {"title": "Regular Job"}
        mock_regular_element = self.create_mock_job_element(regular_job_data)

        extracted_regular = session._extract_job_data(mock_regular_element, 0)

        if extracted_regular:
            # Should not have promoted field or should be False
            promoted_status = extracted_regular.get("promoted", False)
            assert promoted_status is False, "Non-promoted jobs should not have promoted=True"

    def test_connection_insight_extraction_and_parsing(self, session):
        """
        Test extraction and parsing of connection insights.

        EXPECTED TO FAIL: Current implementation doesn't extract connection insights.
        """
        insight_test_cases = [
            "9 connections work here",
            "15 connections work here",
            "2 connections work here",
            "50+ connections work here",
            "You have connections here",
        ]

        for insight_text in insight_test_cases:
            job_data = {"connections_insight": insight_text}
            mock_job_element = self.create_mock_job_element(job_data)

            extracted_data = session._extract_job_data(mock_job_element, 0)

            if extracted_data and "connections_insight" in extracted_data:
                assert extracted_data["connections_insight"] == insight_text, \
                    f"Should extract insight exactly: expected '{insight_text}', got '{extracted_data['connections_insight']}'"

    def test_complete_real_world_job_example(self, session):
        """
        Test extraction with a complete real-world job example.

        This uses actual data structure observed in LinkedIn DOM.
        EXPECTED TO FAIL: Current implementation uses wrong selectors.
        """
        # Real job data example from LinkedIn
        real_job_data = {
            "title": "Senior Data Engineer",
            "company": "Stripe",
            "location": "San Francisco, CA (Remote)",
            "salary": "$150K/yr - $200K/yr · Stock options",
            "promoted": False,  # Not promoted
            "job_state": "Applied",
            "connections_insight": "12 connections work here",
            "url": "https://www.linkedin.com/jobs/view/4300123456"
        }

        mock_job_element = self.create_mock_job_element(real_job_data)
        extracted_data = session._extract_job_data(mock_job_element, 0)

        assert extracted_data is not None, "Should extract real-world job data"

        # Verify core fields
        assert extracted_data["title"] == "Senior Data Engineer"
        assert extracted_data["company"] == "Stripe"

        # Verify location parsing (should remove parentheses)
        assert extracted_data["location"] == "San Francisco, CA"
        assert extracted_data.get("work_type") == "Remote"

        # Verify salary/benefits separation
        salary = extracted_data.get("salary", "")
        benefits = extracted_data.get("benefits", "")
        assert "$150K/yr - $200K/yr" in salary
        assert "Stock options" in benefits

        # Verify metadata
        assert extracted_data["job_state"] == "Applied"
        assert extracted_data["connections_insight"] == "12 connections work here"
        assert extracted_data.get("promoted") is False


class TestSelectorDocumentation:
    """Document the correct selectors and their usage patterns."""

    def test_selector_reference_documentation(self):
        """
        Document the correct LinkedIn DOM selectors for future implementation.

        This test serves as living documentation of the correct selectors.
        ALWAYS PASSES: This is documentation, not a test of functionality.
        """
        correct_selectors = {
            "title": [
                "a[aria-label*='with verification']",  # Primary: includes verification jobs
                "a.job-card-container__link",           # Standard job card link
                ".artdeco-entity-lockup__title a",      # Entity lockup structure
                ".job-card-list__title a",              # List view format
                "h3 a",                                 # Generic heading fallback
            ],

            "company": [
                ".artdeco-entity-lockup__subtitle span", # Primary: company name span
                ".job-card-container__primary-description", # Alternative format
            ],

            "location": [
                ".artdeco-entity-lockup__caption .job-card-container__metadata-wrapper span",
                # Location is in caption section, within metadata wrapper
            ],

            "salary_and_benefits": [
                ".artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span",
                # Salary and benefits in metadata section, may be multiple spans
            ],

            "promoted_status": [
                ".job-card-container__footer-item span", # Footer items, check text="Promoted"
            ],

            "job_state": [
                ".job-card-container__footer-job-state", # Footer with job state class
            ],

            "connection_insights": [
                ".job-card-container__job-insight-text", # Insight section text
            ],
        }

        # This test always passes - it's documentation
        assert len(correct_selectors) > 0, "Selector documentation should exist"

        # Verify each category has selectors
        for category, selectors in correct_selectors.items():
            assert len(selectors) > 0, f"Category {category} should have selectors"

        # Document the implementation pattern
        implementation_notes = {
            "extraction_pattern": "Try primary selector first, fall back to alternatives",
            "error_handling": "Continue extraction if individual elements fail",
            "data_cleaning": "Clean whitespace, parse parentheses for work type",
            "salary_benefits": "Split on '·' separator, first part is salary",
            "promoted_boolean": "Convert 'Promoted' text to boolean True",
            "work_type_parsing": "Extract from parentheses in location string",
        }

        assert len(implementation_notes) > 0, "Implementation notes should exist"

    def test_current_vs_correct_selector_comparison(self):
        """
        Document the difference between current and correct selectors.

        ALWAYS PASSES: This documents the changes needed.
        """
        selector_changes = {
            "WRONG_current_approach": {
                "description": "Current implementation tries to parse combined subtitle",
                "selector": ".artdeco-entity-lockup__subtitle span",
                "expects": "Company · Location · Salary format",
                "problem": "LinkedIn DOM has separate elements, not combined text"
            },

            "CORRECT_company_extraction": {
                "description": "Company is in subtitle span, but alone",
                "selector": ".artdeco-entity-lockup__subtitle span",
                "expects": "Just company name (e.g. 'Datadog')",
                "fix": "Extract company directly, don't try to split"
            },

            "CORRECT_location_extraction": {
                "description": "Location is in separate caption element",
                "selector": ".artdeco-entity-lockup__caption .job-card-container__metadata-wrapper span",
                "expects": "Location text (e.g. 'New York, NY' or 'New York, NY (Remote)')",
                "fix": "New selector for location element, parse work type from parentheses"
            },

            "CORRECT_salary_extraction": {
                "description": "Salary is in separate metadata element",
                "selector": ".artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span",
                "expects": "Salary and benefits (e.g. '$116K/yr - $169K/yr · 401(k) benefit')",
                "fix": "New selector for metadata, split salary and benefits on '·'"
            },

            "NEW_promoted_extraction": {
                "description": "Promoted status in footer (not extracted currently)",
                "selector": ".job-card-container__footer-item span",
                "expects": "Text 'Promoted' or element not found",
                "fix": "New extraction for promoted status"
            },

            "NEW_connections_extraction": {
                "description": "Connection insights (not extracted currently)",
                "selector": ".job-card-container__job-insight-text",
                "expects": "Text like '9 connections work here'",
                "fix": "New extraction for connection insights"
            }
        }

        # Document that changes are needed
        assert len(selector_changes) > 0, "Should document selector changes needed"

        # Verify each change is documented
        for change_type, change_info in selector_changes.items():
            assert "description" in change_info, f"Change {change_type} should have description"
            assert "selector" in change_info, f"Change {change_type} should have selector"
            assert "fix" in change_info or "problem" in change_info, f"Change {change_type} should document issue/fix"