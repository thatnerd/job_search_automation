"""
Integration tests for LinkedIn job scraping functionality.

These tests use real LinkedIn credentials and authenticate against LinkedIn
to test the actual job scraping functionality. They are designed to fail
initially to follow TDD principles.

NOTE: These tests require:
- Valid LinkedIn credentials in .env file
- Network connectivity to LinkedIn
- May take longer to run due to browser automation
"""

import os
import pytest
import re
from typing import List, Dict, Any
import sys

# Add project root to path
sys.path.insert(0, '.')
from lib.linkedin_session import LinkedInSession


class TestJobScrapingIntegration:
    """Integration tests for job scraping against real LinkedIn."""

    @pytest.fixture
    def authenticated_session(self):
        """Create and authenticate a LinkedIn session using real credentials."""
        # Skip if credentials not available
        if not os.getenv("LINKEDIN_EMAIL") or not os.getenv("LINKEDIN_PASSWORD"):
            pytest.skip("LinkedIn credentials not available in environment")

        # Use headless mode for CI/automated testing
        session = LinkedInSession(headless=True)

        try:
            # Authenticate using existing cookies if possible
            success = session.login(force_fresh=False)
            if not success:
                pytest.fail("Could not authenticate with LinkedIn")

            yield session

        finally:
            session.close_session()

    def test_job_ids_are_not_generic_search_string(self, authenticated_session):
        """
        Test that job IDs are actual LinkedIn job IDs, not generic strings.

        EXPECTED TO FAIL: Current implementation returns "search" for all job_ids.
        Should extract actual LinkedIn job IDs (typically 10-digit numbers).
        """
        jobs = authenticated_session.scrape_jobs(show_all=False)

        # Should have at least some jobs
        assert len(jobs) > 0, "Should find at least one job"

        # Check job IDs
        for i, job in enumerate(jobs[:5]):  # Check first 5 jobs
            job_id = job.get("job_id")

            # Should not be the generic "search" string
            assert job_id != "search", f"Job {i+1} has generic 'search' job_id instead of actual LinkedIn job ID"

            # Should be a numeric string (LinkedIn job IDs are typically numbers)
            if job_id:
                assert job_id.isdigit(), f"Job {i+1} job_id '{job_id}' should be numeric"
                assert len(job_id) >= 8, f"Job {i+1} job_id '{job_id}' should be at least 8 digits (typical LinkedIn format)"

    def test_job_titles_do_not_contain_verification_text(self, authenticated_session):
        """
        Test that job titles are clean and don't contain "with verification" text.

        EXPECTED TO FAIL: Current implementation includes "with verification" in titles.
        Should extract clean job titles without LinkedIn UI elements.
        """
        jobs = authenticated_session.scrape_jobs(show_all=False)

        # Should have at least some jobs
        assert len(jobs) > 0, "Should find at least one job"

        # Check job titles
        for i, job in enumerate(jobs[:5]):  # Check first 5 jobs
            title = job.get("title", "")

            # Should not contain verification text
            assert "with verification" not in title.lower(), \
                f"Job {i+1} title '{title}' contains 'with verification' text that should be filtered out"

            # Title should not be empty
            assert title.strip(), f"Job {i+1} should have a non-empty title"

            # Title should be reasonable length (not just whitespace or single words)
            assert len(title.strip()) > 5, f"Job {i+1} title '{title}' seems too short"

    def test_company_information_is_extracted(self, authenticated_session):
        """
        Test that company/employer information is properly extracted.

        EXPECTED TO FAIL: Current implementation may not capture company info correctly.
        Should extract the actual employer name clearly visible in the UI.
        """
        jobs = authenticated_session.scrape_jobs(show_all=False)

        # Should have at least some jobs
        assert len(jobs) > 0, "Should find at least one job"

        # Check company information
        companies_found = 0
        for i, job in enumerate(jobs[:10]):  # Check first 10 jobs
            company = job.get("company", "")

            if company and company.strip():
                companies_found += 1

                # Company should not contain verification text
                assert "with verification" not in company.lower(), \
                    f"Job {i+1} company '{company}' contains verification text"

                # Company should be reasonable length
                assert len(company.strip()) > 1, f"Job {i+1} company '{company}' seems too short"

                # Company should not be just numbers or single characters
                assert not company.strip().isdigit(), f"Job {i+1} company '{company}' is just numbers"

        # Should find company info for most jobs
        assert companies_found >= len(jobs) * 0.7, \
            f"Only found company info for {companies_found}/{len(jobs)} jobs. Should find for at least 70%"

    def test_location_information_is_extracted(self, authenticated_session):
        """
        Test that location information is properly extracted.

        EXPECTED TO FAIL: Current implementation may not capture location correctly.
        Should extract readable location strings (city, state, country, or "Remote").
        """
        jobs = authenticated_session.scrape_jobs(show_all=False)

        # Should have at least some jobs
        assert len(jobs) > 0, "Should find at least one job"

        # Check location information
        locations_found = 0
        for i, job in enumerate(jobs[:10]):  # Check first 10 jobs
            location = job.get("location", "")

            if location and location.strip():
                locations_found += 1

                # Location should not contain verification text
                assert "with verification" not in location.lower(), \
                    f"Job {i+1} location '{location}' contains verification text"

                # Location should be reasonable length
                assert len(location.strip()) > 1, f"Job {i+1} location '{location}' seems too short"

                # Location should not be just numbers
                assert not location.strip().isdigit(), f"Job {i+1} location '{location}' is just numbers"

        # Should find location info for most jobs
        assert locations_found >= len(jobs) * 0.8, \
            f"Only found location info for {locations_found}/{len(jobs)} jobs. Should find for at least 80%"

    def test_salary_information_is_extracted_when_available(self, authenticated_session):
        """
        Test that salary information is extracted when visible.

        EXPECTED TO FAIL: Current implementation doesn't extract salary data.
        Should extract salary ranges when they are displayed in the job listings.
        """
        jobs = authenticated_session.scrape_jobs(show_all=False)

        # Should have at least some jobs
        assert len(jobs) > 0, "Should find at least one job"

        # Check for salary information
        salaries_found = 0
        for i, job in enumerate(jobs[:20]):  # Check first 20 jobs
            salary = job.get("salary")

            if salary and salary.strip():
                salaries_found += 1

                # Salary should look reasonable (contain numbers and currency/range indicators)
                salary_pattern = re.compile(r'[\$€£¥]|[0-9]|hour|year|annual|range|to|\-', re.IGNORECASE)
                assert salary_pattern.search(salary), \
                    f"Job {i+1} salary '{salary}' doesn't look like valid salary information"

        # Note: Not all jobs show salary, but some should if the UI displays them
        # This test documents the current state - if LinkedIn shows salaries in UI,
        # our scraper should capture at least some of them
        print(f"Found salary info for {salaries_found}/{len(jobs)} jobs")

        # This assertion will likely fail initially, which is expected for TDD
        assert salaries_found > 0, \
            f"No salary information found in any of {len(jobs)} jobs, but LinkedIn UI shows salary data"

    def test_job_data_structure_completeness(self, authenticated_session):
        """
        Test that the overall job data structure captures key information.

        EXPECTED TO FAIL: Current implementation may miss key fields.
        Should have proper structure with all expected fields populated.
        """
        jobs = authenticated_session.scrape_jobs(show_all=False)

        # Should have at least some jobs
        assert len(jobs) > 0, "Should find at least one job"

        # Check data structure for first few jobs
        for i, job in enumerate(jobs[:5]):  # Check first 5 jobs
            # Required fields that should always be present
            assert "title" in job, f"Job {i+1} missing title field"
            assert "company" in job, f"Job {i+1} missing company field"
            assert "location" in job, f"Job {i+1} missing location field"
            assert "job_id" in job, f"Job {i+1} missing job_id field"

            # Fields should not be empty strings
            assert job["title"].strip(), f"Job {i+1} has empty title"
            assert job["company"].strip(), f"Job {i+1} has empty company"
            assert job["location"].strip(), f"Job {i+1} has empty location"
            assert job["job_id"].strip(), f"Job {i+1} has empty job_id"

            # Index should be reasonable
            expected_index = i + 1
            actual_index = job.get("index")
            assert actual_index == expected_index, \
                f"Job {i+1} has incorrect index {actual_index}, expected {expected_index}"

    def test_jobs_have_valid_linkedin_urls(self, authenticated_session):
        """
        Test that job URLs are valid LinkedIn job links.

        EXPECTED TO FAIL: Current implementation may not extract proper URLs.
        Should have LinkedIn job URLs that match the job_id.
        """
        jobs = authenticated_session.scrape_jobs(show_all=False)

        # Should have at least some jobs
        assert len(jobs) > 0, "Should find at least one job"

        urls_found = 0
        for i, job in enumerate(jobs[:5]):  # Check first 5 jobs
            url = job.get("url")
            job_id = job.get("job_id")

            if url:
                urls_found += 1

                # Should be a LinkedIn URL
                assert "linkedin.com" in url, f"Job {i+1} URL '{url}' is not a LinkedIn URL"

                # Should be a job view URL
                assert "/jobs/view/" in url or "/jobs/" in url, \
                    f"Job {i+1} URL '{url}' doesn't look like a LinkedIn job URL"

                # If we have a job_id, it should match the URL
                if job_id and job_id != "search" and job_id.isdigit():
                    assert job_id in url, \
                        f"Job {i+1} job_id '{job_id}' doesn't match URL '{url}'"

        # Should find URLs for most jobs
        assert urls_found >= len(jobs[:5]) * 0.8, \
            f"Only found URLs for {urls_found}/{min(5, len(jobs))} jobs. Should find for at least 80%"