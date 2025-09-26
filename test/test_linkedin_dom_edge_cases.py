"""
Edge case tests for LinkedIn job data extraction from DOM structure.

These tests cover edge cases and error handling scenarios for the LinkedIn
job data extraction functionality, focusing on the actual DOM structure issues:

1. Missing optional elements (salary, promoted status, etc.)
2. Malformed or empty element content
3. Multiple elements with same selector
4. HTML entities and special characters in text
5. Fallback selector behavior when primary selectors fail

These tests help ensure robust extraction that handles real-world LinkedIn
page variations and edge cases gracefully.
"""

import pytest
import sys
from unittest.mock import MagicMock, patch
from selenium.common.exceptions import NoSuchElementException
from typing import List

# Add project root to path
sys.path.insert(0, '.')
from lib.linkedin_session import LinkedInSession


class TestLinkedInDOMEdgeCases:
    """Test edge cases in LinkedIn job data extraction."""

    @pytest.fixture
    def session(self):
        """Create a LinkedInSession instance for testing."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                return LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=', headless=True)

    def test_missing_optional_elements_handled_gracefully(self, session):
        """
        Test that missing optional elements don't break extraction.

        Not all jobs have salary, promoted status, or connection insights.
        The extraction should work with only required fields (title, company).

        EXPECTED TO FAIL: Current implementation might crash on missing elements.
        """
        # Mock job element with only basic fields
        mock_job_element = MagicMock()

        # Mock only title and company elements (minimum required)
        mock_title_element = MagicMock()
        mock_title_element.text = "Software Engineer"
        mock_title_element.get_attribute.return_value = "https://linkedin.com/jobs/view/12345"

        mock_company_element = MagicMock()
        mock_company_element.text = "Tech Corp"

        def mock_find_element_side_effect(by, selector):
            if selector == "a.job-card-container__link":
                return mock_title_element
            elif selector == ".artdeco-entity-lockup__subtitle span":
                return mock_company_element
            else:
                # All optional elements missing
                raise NoSuchElementException(f"Optional element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Should not crash when optional elements are missing
        job_data = session._extract_job_data(mock_job_element, 0)

        # Should still extract basic data
        assert job_data is not None, "Extraction should succeed with missing optional elements"
        assert job_data["title"] == "Software Engineer"
        assert job_data["company"] == "Tech Corp"

        # Optional fields should be missing or None, not cause errors
        optional_fields = ["location", "salary", "promoted", "connections_insight", "work_type", "benefits"]
        for field in optional_fields:
            if field in job_data:
                # If present, should not be empty string or cause errors
                assert job_data[field] is None or isinstance(job_data[field], (str, bool))

    def test_empty_or_whitespace_only_element_content(self, session):
        """
        Test handling of elements with empty or whitespace-only content.

        LinkedIn DOM sometimes has elements with only whitespace, HTML comments,
        or empty content. These should be handled gracefully.

        EXPECTED TO FAIL: Current implementation might not handle empty content properly.
        """
        # Mock job element with empty content
        mock_job_element = MagicMock()

        # Mock elements with various empty content patterns
        mock_title_element = MagicMock()
        mock_title_element.text = "Valid Title"
        mock_title_element.get_attribute.return_value = "https://linkedin.com/jobs/view/12345"

        mock_company_element = MagicMock()
        mock_company_element.text = "   "  # Only whitespace

        mock_location_element = MagicMock()
        mock_location_element.text = ""  # Empty string

        mock_salary_element = MagicMock()
        mock_salary_element.text = "\\n\\t   \\n"  # Whitespace with newlines/tabs

        def mock_find_element_side_effect(by, selector):
            element_map = {
                "a.job-card-container__link": mock_title_element,
                ".artdeco-entity-lockup__subtitle span": mock_company_element,
                ".artdeco-entity-lockup__caption .job-card-container__metadata-wrapper span": mock_location_element,
                ".artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span": mock_salary_element,
            }
            if selector in element_map:
                return element_map[selector]
            else:
                raise NoSuchElementException(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        job_data = session._extract_job_data(mock_job_element, 0)

        # Should handle empty content gracefully
        assert job_data is not None, "Should not crash on empty element content"
        assert job_data["title"] == "Valid Title"  # Valid content preserved

        # Empty/whitespace content should be cleaned up or excluded
        company = job_data.get("company", "")
        location = job_data.get("location", "")
        salary = job_data.get("salary", "")

        # Should not contain only whitespace
        if company:
            assert company.strip() != "", "Company should not be only whitespace"
        if location:
            assert location.strip() != "", "Location should not be only whitespace"
        if salary:
            assert salary.strip() != "", "Salary should not be only whitespace"

    def test_html_entities_and_special_characters_in_content(self, session):
        """
        Test handling of HTML entities and special characters in element text.

        LinkedIn content may contain HTML entities (&amp;, &lt;, etc.) and
        special characters that need proper handling.

        EXPECTED TO FAIL: Current implementation might not handle HTML entities.
        """
        # Mock job element with HTML entities and special characters
        mock_job_element = MagicMock()

        mock_title_element = MagicMock()
        mock_title_element.text = "Senior Developer @ Tech &amp; Innovation Corp"
        mock_title_element.get_attribute.return_value = "https://linkedin.com/jobs/view/12345"

        mock_company_element = MagicMock()
        mock_company_element.text = "R&amp;D Solutions Inc."

        mock_location_element = MagicMock()
        mock_location_element.text = "San José, CA"  # Unicode characters

        mock_salary_element = MagicMock()
        mock_salary_element.text = "$75K–$100K/year • Health &amp; Dental"

        def mock_find_element_side_effect(by, selector):
            element_map = {
                "a.job-card-container__link": mock_title_element,
                ".artdeco-entity-lockup__subtitle span": mock_company_element,
                ".artdeco-entity-lockup__caption .job-card-container__metadata-wrapper span": mock_location_element,
                ".artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span": mock_salary_element,
            }
            if selector in element_map:
                return element_map[selector]
            else:
                raise NoSuchElementException(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        job_data = session._extract_job_data(mock_job_element, 0)

        assert job_data is not None, "Should handle HTML entities and special characters"

        # Should properly decode HTML entities (if implemented)
        # Note: This test will likely fail initially if HTML decoding isn't implemented
        title = job_data.get("title", "")
        company = job_data.get("company", "")
        salary = job_data.get("salary", "")

        # Check that content is preserved (even if entities aren't decoded yet)
        assert len(title) > 10, f"Title should be preserved: '{title}'"
        assert len(company) > 3, f"Company should be preserved: '{company}'"
        assert "$" in salary, f"Salary should contain currency: '{salary}'"

    def test_multiple_metadata_spans_prioritization(self, session):
        """
        Test handling when multiple spans exist in metadata wrapper.

        LinkedIn metadata sections can have multiple spans. The extraction
        should prioritize salary-like content and handle multiple benefits.

        EXPECTED TO FAIL: Current implementation doesn't handle multiple spans.
        """
        # Mock job element
        mock_job_element = MagicMock()

        # Mock multiple spans in metadata
        mock_span1 = MagicMock()
        mock_span1.text = "$90K/yr - $120K/yr"  # Salary

        mock_span2 = MagicMock()
        mock_span2.text = "Health Insurance"  # Benefit 1

        mock_span3 = MagicMock()
        mock_span3.text = "401(k) matching"  # Benefit 2

        mock_span4 = MagicMock()
        mock_span4.text = "Remote work options"  # Benefit 3

        # Mock find_elements to return multiple spans
        def mock_find_elements_side_effect(by, selector):
            if selector == ".artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span":
                return [mock_span1, mock_span2, mock_span3, mock_span4]
            else:
                return []

        # Mock find_element for other selectors
        def mock_find_element_side_effect(by, selector):
            raise NoSuchElementException(f"Element not found: {selector}")

        mock_job_element.find_elements.side_effect = mock_find_elements_side_effect
        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        job_data = session._extract_job_data(mock_job_element, 0)

        # Should identify and prioritize salary information
        assert job_data is not None, "Should handle multiple metadata spans"

        if "salary" in job_data:
            salary = job_data["salary"]
            # Should extract the salary span (first one with money indicators)
            assert "$90K/yr - $120K/yr" in salary, f"Should extract salary: '{salary}'"

        if "benefits" in job_data:
            benefits = job_data["benefits"]
            # Should combine or reference benefit spans
            benefit_keywords = ["Health Insurance", "401(k) matching", "Remote work"]
            has_benefit_info = any(keyword in benefits for keyword in benefit_keywords)
            assert has_benefit_info, f"Should extract benefit information: '{benefits}'"

    def test_fallback_selector_chain_for_title_extraction(self, session):
        """
        Test that title extraction uses fallback selectors when primary fails.

        Different LinkedIn page layouts may use different selectors for job titles.
        Should try multiple selectors in priority order.

        EXPECTED TO FAIL: Current implementation might not have comprehensive fallbacks.
        """
        # Mock job element
        mock_job_element = MagicMock()

        # Mock that primary title selector fails
        mock_fallback_title_element = MagicMock()
        mock_fallback_title_element.text = "Backend Developer"
        mock_fallback_title_element.get_attribute.return_value = "https://linkedin.com/jobs/view/54321"

        call_count = 0

        def mock_find_element_side_effect(by, selector):
            nonlocal call_count
            call_count += 1

            # First few selectors fail
            if call_count <= 2:
                raise NoSuchElementException(f"Primary selector failed: {selector}")
            # Fallback selector succeeds
            elif selector in [".artdeco-entity-lockup__title a", ".job-card-list__title", "h3 a"]:
                return mock_fallback_title_element
            else:
                raise NoSuchElementException(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        job_data = session._extract_job_data(mock_job_element, 0)

        # Should successfully extract title using fallback selectors
        assert job_data is not None, "Should use fallback selectors for title"
        assert "title" in job_data, "Should extract title field"
        assert job_data["title"] == "Backend Developer", f"Expected fallback title, got '{job_data.get('title')}'"

        # Should have attempted multiple selectors
        assert call_count > 2, f"Should try multiple selectors, only tried {call_count}"

    def test_job_rejection_when_no_title_found(self, session):
        """
        Test that jobs without extractable titles are rejected.

        If no title can be found using any selector, the job should be rejected
        (return None) rather than returning incomplete data.

        EXPECTED TO PASS: Current implementation should already do this.
        """
        # Mock job element where no title selectors work
        mock_job_element = MagicMock()

        def mock_find_element_side_effect(by, selector):
            # No title selectors work
            if any(title_keyword in selector.lower() for title_keyword in ["title", "lockup__title", "job-card-container__link"]):
                raise NoSuchElementException(f"No title element found: {selector}")
            else:
                # Other elements might exist
                mock_element = MagicMock()
                mock_element.text = "Some data"
                return mock_element

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        job_data = session._extract_job_data(mock_job_element, 0)

        # Should reject job without title
        assert job_data is None, "Should reject job when no title can be extracted"

    def test_location_with_complex_formatting(self, session):
        """
        Test location extraction with complex formatting and work types.

        LinkedIn locations can have various formats:
        - "City, State"
        - "City, State (Remote)"
        - "City, Country"
        - "Remote"
        - "Multiple locations"

        EXPECTED TO FAIL: Current implementation might not handle all variations.
        """
        test_cases = [
            ("New York, NY (Remote)", "New York, NY", "Remote"),
            ("San Francisco, CA (Hybrid)", "San Francisco, CA", "Hybrid"),
            ("London, United Kingdom", "London, United Kingdom", None),
            ("Remote", "Remote", "Remote"),
            ("Multiple locations", "Multiple locations", None),
            ("Toronto, ON (On-site)", "Toronto, ON", "On-site"),
        ]

        for location_text, expected_location, expected_work_type in test_cases:
            # Mock job element for each test case
            mock_job_element = MagicMock()

            mock_location_element = MagicMock()
            mock_location_element.text = location_text

            def mock_find_element_side_effect(by, selector):
                if selector == ".artdeco-entity-lockup__caption .job-card-container__metadata-wrapper span":
                    return mock_location_element
                else:
                    raise NoSuchElementException(f"Element not found: {selector}")

            mock_job_element.find_element.side_effect = mock_find_element_side_effect

            job_data = session._extract_job_data(mock_job_element, 0)

            # Check location extraction
            if job_data:
                location = job_data.get("location", "")
                work_type = job_data.get("work_type")

                assert location == expected_location, \
                    f"Location '{location_text}': expected location '{expected_location}', got '{location}'"

                if expected_work_type:
                    assert work_type == expected_work_type, \
                        f"Location '{location_text}': expected work_type '{expected_work_type}', got '{work_type}'"

    def test_salary_format_variations_handling(self, session):
        """
        Test handling of various salary format variations.

        LinkedIn shows salaries in different formats:
        - "$75K - $90K/yr"
        - "$50/hr - $75/hr"
        - "$120,000 - $150,000/year"
        - "Competitive salary"
        - "Up to $100K"

        EXPECTED TO FAIL: Current implementation might not recognize all formats.
        """
        salary_test_cases = [
            "$75K - $90K/yr",
            "$50/hr - $75/hr",
            "$120,000 - $150,000/year",
            "€45,000 - €60,000/year",  # European format
            "£40K - £55K per annum",   # UK format
            "Competitive salary",
            "Up to $100K",
            "$25.00 - $35.00/hour",
            "¥8,000,000 - ¥12,000,000/year",  # Japanese Yen
        ]

        for salary_text in salary_test_cases:
            # Mock job element for each salary format
            mock_job_element = MagicMock()

            mock_salary_element = MagicMock()
            mock_salary_element.text = salary_text

            def mock_find_element_side_effect(by, selector):
                if selector == ".artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span":
                    return mock_salary_element
                else:
                    raise NoSuchElementException(f"Element not found: {selector}")

            mock_job_element.find_element.side_effect = mock_find_element_side_effect

            job_data = session._extract_job_data(mock_job_element, 0)

            # Should recognize as salary information
            if job_data and "salary" in job_data:
                extracted_salary = job_data["salary"]
                assert extracted_salary == salary_text, \
                    f"Salary format '{salary_text}': expected exact match, got '{extracted_salary}'"

    def test_error_recovery_during_extraction(self, session):
        """
        Test that extraction continues after individual element extraction errors.

        If extracting one field fails (due to unexpected DOM changes), other
        fields should still be extracted successfully.

        EXPECTED TO FAIL: Current implementation might not have proper error recovery.
        """
        # Mock job element
        mock_job_element = MagicMock()

        # Mock successful title extraction
        mock_title_element = MagicMock()
        mock_title_element.text = "Data Scientist"
        mock_title_element.get_attribute.return_value = "https://linkedin.com/jobs/view/99999"

        # Mock successful company extraction
        mock_company_element = MagicMock()
        mock_company_element.text = "Analytics Corp"

        call_count = 0

        def mock_find_element_side_effect(by, selector):
            nonlocal call_count
            call_count += 1

            if selector == "a.job-card-container__link":
                return mock_title_element
            elif selector == ".artdeco-entity-lockup__subtitle span":
                return mock_company_element
            elif selector == ".artdeco-entity-lockup__caption .job-card-container__metadata-wrapper span":
                # Simulate unexpected error during location extraction
                raise Exception("Unexpected DOM structure change")
            else:
                raise NoSuchElementException(f"Element not found: {selector}")

        mock_job_element.find_element.side_effect = mock_find_element_side_effect

        # Should not crash due to location extraction error
        job_data = session._extract_job_data(mock_job_element, 0)

        # Should still extract successfully extracted fields
        assert job_data is not None, "Should recover from individual field extraction errors"
        assert job_data["title"] == "Data Scientist", "Should extract title despite location error"
        assert job_data["company"] == "Analytics Corp", "Should extract company despite location error"

        # Location might be missing due to error, but that's acceptable
        location = job_data.get("location")
        assert location is None or location == "", "Location should be missing/empty due to extraction error"


class TestSelectorValidationAndFallbacks:
    """Test CSS selector validation and fallback mechanisms."""

    @pytest.fixture
    def session(self):
        """Create a LinkedInSession instance for testing."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                return LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=', headless=True)

    def test_comprehensive_title_selector_fallbacks(self, session):
        """
        Test comprehensive fallback chain for title extraction.

        Should try multiple selectors in priority order and succeed with any valid one.

        EXPECTED TO FAIL: Current implementation might not have all fallback selectors.
        """
        # Define expected selector priority order
        expected_title_selectors = [
            "a[aria-label*='with verification']",  # Primary with verification
            "a.job-card-container__link",          # Standard job link
            ".artdeco-entity-lockup__title a",     # Entity lockup title
            ".job-card-list__title",               # List view title
            "h3 a",                                # Generic heading link
            "[data-job-id] h3 a",                  # Job ID context title
            ".job-card-container__title a"         # Container title
        ]

        # Test that each selector in the chain can work
        for i, working_selector in enumerate(expected_title_selectors):
            mock_job_element = MagicMock()

            mock_title_element = MagicMock()
            mock_title_element.text = f"Test Title {i+1}"
            mock_title_element.get_attribute.return_value = f"https://linkedin.com/jobs/view/{i+1}"

            def mock_find_element_side_effect(by, selector):
                if selector == working_selector:
                    return mock_title_element
                else:
                    # All other selectors fail
                    raise NoSuchElementException(f"Not the working selector: {selector}")

            mock_job_element.find_element.side_effect = mock_find_element_side_effect

            job_data = session._extract_job_data(mock_job_element, 0)

            # Should successfully extract with any selector in the chain
            assert job_data is not None, f"Should work with selector {i+1}: {working_selector}"
            assert job_data["title"] == f"Test Title {i+1}", \
                f"Wrong title extracted with {working_selector}"

    def test_metadata_element_detection_priorities(self, session):
        """
        Test priority handling when multiple metadata elements exist.

        Should prioritize salary information over other metadata types.

        EXPECTED TO FAIL: Current implementation might not prioritize correctly.
        """
        # Mock job element
        mock_job_element = MagicMock()

        # Mock multiple metadata elements with different priorities
        mock_benefit_span = MagicMock()
        mock_benefit_span.text = "Health benefits"

        mock_salary_span = MagicMock()  # This should be prioritized
        mock_salary_span.text = "$80K - $100K/yr"

        mock_other_span = MagicMock()
        mock_other_span.text = "Full-time"

        # Return in non-priority order (salary should still be detected)
        def mock_find_elements_side_effect(by, selector):
            if selector == ".artdeco-entity-lockup__metadata .job-card-container__metadata-wrapper span":
                return [mock_benefit_span, mock_salary_span, mock_other_span]
            else:
                return []

        mock_job_element.find_elements.side_effect = mock_find_elements_side_effect
        mock_job_element.find_element.side_effect = lambda by, selector: NoSuchElementException("Not found")

        job_data = session._extract_job_data(mock_job_element, 0)

        # Should prioritize salary information
        if job_data and "salary" in job_data:
            assert "$80K - $100K/yr" in job_data["salary"], \
                "Should prioritize salary span over other metadata"