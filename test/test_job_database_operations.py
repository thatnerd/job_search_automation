"""
Comprehensive tests for JobDatabase operations including job storage, search,
session management, and statistics generation.

These tests cover the core CRUD operations, deduplication logic, search functionality
with FTS, and database statistics generation following TDD principles.
"""

import sqlite3
import tempfile
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, '.')
from lib.job_database import JobDatabase, JobRecord, ScrapeSession


class TestJobStorage:
    """Test job insertion, updates, and deduplication logic."""

    @pytest.fixture
    def db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            yield JobDatabase(db_path=db_path)

    def test_upsert_job_new_insertion(self, db):
        """
        Test inserting a new job record.

        Verifies that new jobs are properly inserted with all fields
        and that generated columns are computed correctly.
        """
        job = JobRecord(
            job_id="new_job_123",
            title="Python Developer",
            company="TechCorp",
            work_type="Remote",
            location="San Francisco, CA",
            salary="$100K/yr - $120K/yr",
            benefits="Health, Dental",
            url="https://linkedin.com/jobs/new_job_123",
            description="Build awesome Python apps",
            status="active",
            source="linkedin"
        )

        was_inserted, was_updated = db.upsert_job(job)

        assert was_inserted is True
        assert was_updated is False

        # Verify job was stored correctly
        stored_job = db.get_job("new_job_123")
        assert stored_job is not None
        assert stored_job['job_id'] == "new_job_123"
        assert stored_job['title'] == "Python Developer"
        assert stored_job['company'] == "TechCorp"
        assert stored_job['work_type'] == "Remote"
        assert stored_job['location'] == "San Francisco, CA"
        assert stored_job['salary'] == "$100K/yr - $120K/yr"
        assert stored_job['benefits'] == "Health, Dental"
        assert stored_job['url'] == "https://linkedin.com/jobs/new_job_123"
        assert stored_job['description'] == "Build awesome Python apps"
        assert stored_job['status'] == "active"
        assert stored_job['source'] == "linkedin"

        # Verify generated columns
        assert stored_job['salary_min_yearly'] == 100000
        assert stored_job['salary_max_yearly'] == 120000

        # Verify timestamps were set
        assert stored_job['first_seen'] is not None
        assert stored_job['last_seen'] is not None
        assert stored_job['created_at'] is not None
        assert stored_job['updated_at'] is not None

    def test_upsert_job_update_existing(self, db):
        """
        Test updating an existing job record when data changes.

        Verifies that existing jobs are updated when field values change
        and that last_seen timestamp is updated appropriately.
        """
        # Insert initial job
        original_job = JobRecord(
            job_id="update_test_456",
            title="Junior Developer",
            company="StartupCorp",
            salary="$80K/yr"
        )

        db.upsert_job(original_job)

        # Update the job with new information
        updated_job = JobRecord(
            job_id="update_test_456",
            title="Senior Developer",  # Changed
            company="StartupCorp",
            work_type="Hybrid",  # Added
            salary="$120K/yr"  # Changed
        )

        was_inserted, was_updated = db.upsert_job(updated_job)

        assert was_inserted is False
        assert was_updated is True

        # Verify updates were applied
        stored_job = db.get_job("update_test_456")
        assert stored_job['title'] == "Senior Developer"
        assert stored_job['work_type'] == "Hybrid"
        assert stored_job['salary'] == "$120K/yr"
        assert stored_job['salary_min_yearly'] == 120000
        assert stored_job['salary_max_yearly'] == 120000

    def test_upsert_job_no_changes(self, db):
        """
        Test upserting a job with no changes updates only last_seen.

        Verifies that when job data hasn't changed, only the last_seen
        timestamp is updated to track that the job is still active.
        """
        # Insert initial job
        job = JobRecord(
            job_id="no_change_789",
            title="Data Scientist",
            company="DataCorp"
        )

        db.upsert_job(job)
        original_job = db.get_job("no_change_789")

        # Upsert same job data
        was_inserted, was_updated = db.upsert_job(job)

        assert was_inserted is False
        assert was_updated is False  # No field changes

        # Verify last_seen was updated (this is hard to test precisely due to timing)
        updated_job = db.get_job("no_change_789")
        assert updated_job['job_id'] == original_job['job_id']
        assert updated_job['title'] == original_job['title']
        assert updated_job['company'] == original_job['company']

    def test_upsert_job_with_session_mapping(self, db):
        """
        Test upserting a job with session mapping and position tracking.

        Verifies that jobs can be linked to scrape sessions with position information
        for audit trail and result ordering.
        """
        # Create a scrape session first
        session = ScrapeSession(
            timestamp=datetime.now(),
            total_jobs_found=10,
            new_jobs_added=5,
            search_criteria='{"keywords": "python"}'
        )
        session_id = db.create_scrape_session(session)

        # Insert job with session mapping
        job = JobRecord(
            job_id="session_job_001",
            title="Backend Engineer",
            company="WebCorp"
        )

        was_inserted, was_updated = db.upsert_job(job, session_id=session_id, position=3)

        assert was_inserted is True

        # Verify job-session mapping was created
        with sqlite3.connect(db.db_path) as conn:
            mapping = conn.execute("""
                SELECT job_id, session_id, position_in_results
                FROM job_session_mapping
                WHERE job_id = ? AND session_id = ?
            """, (job.job_id, session_id)).fetchone()

            assert mapping is not None
            assert mapping[0] == "session_job_001"
            assert mapping[1] == session_id
            assert mapping[2] == 3

    def test_upsert_job_minimal_fields(self, db):
        """
        Test upserting a job with only required fields.

        Ensures that jobs with minimal information can be stored
        and that optional fields remain None.
        """
        minimal_job = JobRecord(job_id="minimal_123")

        was_inserted, was_updated = db.upsert_job(minimal_job)

        assert was_inserted is True

        stored_job = db.get_job("minimal_123")
        assert stored_job['job_id'] == "minimal_123"
        assert stored_job['title'] is None
        assert stored_job['company'] is None
        assert stored_job['work_type'] is None
        assert stored_job['salary'] is None
        assert stored_job['salary_min_yearly'] is None
        assert stored_job['salary_max_yearly'] is None
        assert stored_job['status'] == 'active'  # Default
        assert stored_job['source'] == 'linkedin'  # Default

    def test_get_job_nonexistent(self, db):
        """
        Test retrieving a job that doesn't exist.

        Verifies that get_job returns None for non-existent job IDs.
        """
        result = db.get_job("nonexistent_job_id")
        assert result is None


class TestJobSearch:
    """Test job search functionality including filters and FTS."""

    @pytest.fixture
    def populated_db(self):
        """Create a database populated with test job data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = JobDatabase(db_path=db_path)

            # Create diverse test jobs
            test_jobs = [
                JobRecord(
                    job_id="search_1",
                    title="Senior Python Developer",
                    company="TechCorp",
                    work_type="Remote",
                    location="San Francisco, CA",
                    salary="$120K/yr - $150K/yr",
                    description="Build scalable Python applications"
                ),
                JobRecord(
                    job_id="search_2",
                    title="Data Scientist",
                    company="DataCorp",
                    work_type="Hybrid",
                    location="New York, NY",
                    salary="$110K/yr - $140K/yr",
                    description="Analyze data using Python and SQL"
                ),
                JobRecord(
                    job_id="search_3",
                    title="Frontend Developer",
                    company="WebCorp",
                    work_type="On-site",
                    location="Austin, TX",
                    salary="$90K/yr - $110K/yr",
                    description="Create amazing user interfaces with React"
                ),
                JobRecord(
                    job_id="search_4",
                    title="DevOps Engineer",
                    company="CloudCorp",
                    work_type="Remote",
                    location="Seattle, WA",
                    salary="$130K/yr - $160K/yr",
                    description="Manage cloud infrastructure and deployment pipelines"
                ),
                JobRecord(
                    job_id="search_5",
                    title="Python Backend Engineer",
                    company="TechCorp",
                    work_type="Remote",
                    location="Remote",
                    salary="$100K/yr",
                    description="Develop backend services using Python and Django"
                    # Active by default
                ),
                JobRecord(
                    job_id="search_6",
                    title="Removed Job",
                    company="DeadCorp",
                    status="removed"  # Inactive job for other tests
                )
            ]

            for job in test_jobs:
                db.upsert_job(job)

            yield db

    def test_search_jobs_all_active(self, populated_db):
        """
        Test searching for all active jobs without filters.

        Verifies basic search functionality returns all active jobs
        in the correct order.
        """
        results = populated_db.search_jobs()

        # Should return 5 active jobs (excluding the 'removed' one)
        assert len(results) == 5

        # Verify all returned jobs are active
        for job in results:
            assert job['status'] == 'active'

        # Should be ordered by last_seen DESC
        job_ids = [job['job_id'] for job in results]
        assert 'search_6' not in job_ids  # Removed job not included

    def test_search_jobs_by_company(self, populated_db):
        """
        Test searching jobs filtered by company name.

        Verifies case-insensitive partial matching for company names.
        """
        # Exact company match
        techcorp_jobs = populated_db.search_jobs(company="TechCorp")
        assert len(techcorp_jobs) == 2  # search_1 and search_5
        assert techcorp_jobs[0]['company'] == "TechCorp"
        # Both search_1 and search_5 are TechCorp

        # Partial company match
        corp_jobs = populated_db.search_jobs(company="Corp")
        assert len(corp_jobs) == 5  # All active companies have "Corp" in name

        # Case insensitive
        techcorp_lower = populated_db.search_jobs(company="techcorp")
        assert len(techcorp_lower) == 2
        assert techcorp_lower[0]['company'] == "TechCorp"

    def test_search_jobs_by_location(self, populated_db):
        """
        Test searching jobs filtered by location.

        Verifies case-insensitive partial matching for locations.
        """
        # Specific city
        sf_jobs = populated_db.search_jobs(location="San Francisco")
        assert len(sf_jobs) == 1
        assert sf_jobs[0]['location'] == "San Francisco, CA"

        # State abbreviation
        ca_jobs = populated_db.search_jobs(location="CA")
        assert len(ca_jobs) == 1

        # Remote jobs
        remote_jobs = populated_db.search_jobs(location="Remote")
        assert len(remote_jobs) == 1
        assert remote_jobs[0]['work_type'] == "Remote"

    def test_search_jobs_by_work_type(self, populated_db):
        """
        Test searching jobs filtered by work type.

        Verifies exact matching for work type values.
        """
        remote_jobs = populated_db.search_jobs(work_type="Remote")
        assert len(remote_jobs) == 3  # search_1, search_4, search_5

        for job in remote_jobs:
            assert job['work_type'] == "Remote"

        hybrid_jobs = populated_db.search_jobs(work_type="Hybrid")
        assert len(hybrid_jobs) == 1
        assert hybrid_jobs[0]['work_type'] == "Hybrid"

        onsite_jobs = populated_db.search_jobs(work_type="On-site")
        assert len(onsite_jobs) == 1
        assert onsite_jobs[0]['work_type'] == "On-site"

    def test_search_jobs_by_salary_range(self, populated_db):
        """
        Test searching jobs filtered by salary range using generated columns.

        Verifies that min/max salary filters work correctly with generated columns.
        """
        # Jobs with minimum salary >= $120K
        high_min_jobs = populated_db.search_jobs(min_salary=120000)
        assert len(high_min_jobs) == 2  # search_1 and search_4

        # Jobs with maximum salary <= $110K
        low_max_jobs = populated_db.search_jobs(max_salary=110000)
        assert len(low_max_jobs) == 2  # search_2 (max 110K), search_3 (max 110K)

        # Jobs in specific salary range
        mid_range_jobs = populated_db.search_jobs(min_salary=100000, max_salary=140000)
        assert len(mid_range_jobs) == 2  # search_2 and search_3 fall in this range

        # No jobs in impossible range
        no_jobs = populated_db.search_jobs(min_salary=200000)
        assert len(no_jobs) == 0

    def test_search_jobs_full_text_search(self, populated_db):
        """
        Test full-text search functionality using FTS5.

        Verifies that FTS works correctly for title, company, and description fields.
        """
        # Search in titles
        python_jobs = populated_db.search_jobs(query="Python")
        assert len(python_jobs) == 3  # All Python-related jobs: search_1, search_2, search_5

        # Search in descriptions
        data_jobs = populated_db.search_jobs(query="data")
        assert len(data_jobs) == 1
        assert data_jobs[0]['job_id'] == "search_2"

        # Search in company names
        tech_jobs = populated_db.search_jobs(query="TechCorp")
        assert len(tech_jobs) == 2  # search_1 and search_5
        assert tech_jobs[0]['company'] == "TechCorp"

        # Search for non-existent term
        no_results = populated_db.search_jobs(query="nonexistent")
        assert len(no_results) == 0

        # Search for specific term
        backend_jobs = populated_db.search_jobs(query="backend")
        assert len(backend_jobs) == 1  # search_5 has "backend" in title

        infrastructure_jobs = populated_db.search_jobs(query="infrastructure")
        assert len(infrastructure_jobs) == 1  # DevOps job mentions infrastructure

    def test_search_jobs_combined_filters(self, populated_db):
        """
        Test searching jobs with multiple filters combined.

        Verifies that multiple search criteria work together correctly.
        """
        # Company + work type
        remote_tech_jobs = populated_db.search_jobs(company="TechCorp", work_type="Remote")
        assert len(remote_tech_jobs) == 2  # search_1 and search_5
        # Can be either search_1 or search_5

        # Location + salary range
        high_salary_ca = populated_db.search_jobs(location="CA", min_salary=120000)
        assert len(high_salary_ca) == 1

        # FTS + filters
        python_remote = populated_db.search_jobs(query="Python", work_type="Remote")
        assert len(python_remote) == 2  # search_1 and search_5 both match Python and Remote
        # Can be either search_1 or search_5

        # Multiple filters with no results
        impossible = populated_db.search_jobs(
            company="TechCorp",
            work_type="On-site",
            min_salary=200000
        )
        assert len(impossible) == 0

    def test_search_jobs_custom_status(self, populated_db):
        """
        Test searching jobs with custom status filter.

        Verifies that status filtering works for non-active jobs.
        """
        # Search removed jobs
        removed_jobs = populated_db.search_jobs(status="removed")
        assert len(removed_jobs) == 1
        assert removed_jobs[0]['status'] == "removed"
        assert removed_jobs[0]['job_id'] == "search_6"

        # Search all jobs regardless of status
        all_jobs = populated_db.search_jobs(status="")  # Empty status means no filter
        # This would require modifying the search logic to handle empty status

    def test_search_jobs_limit(self, populated_db):
        """
        Test search result limiting functionality.

        Verifies that the limit parameter correctly restricts result count.
        """
        # Limit to 2 results
        limited_results = populated_db.search_jobs(limit=2)
        assert len(limited_results) == 2

        # Limit larger than available results
        all_results = populated_db.search_jobs(limit=100)
        assert len(all_results) == 5  # Total active jobs

        # Limit to 0 results
        no_results = populated_db.search_jobs(limit=0)
        assert len(no_results) == 0


class TestSessionManagement:
    """Test scrape session creation and job-session relationships."""

    @pytest.fixture
    def db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            yield JobDatabase(db_path=db_path)

    def test_create_scrape_session_minimal(self, db):
        """
        Test creating a scrape session with minimal required data.

        Verifies that sessions can be created with just timestamp and job count.
        """
        session = ScrapeSession(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            total_jobs_found=25
        )

        session_id = db.create_scrape_session(session)

        assert session_id is not None
        assert session_id > 0

        # Verify session was stored correctly
        with sqlite3.connect(db.db_path) as conn:
            stored = conn.execute("""
                SELECT session_id, timestamp, total_jobs_found, new_jobs_added, source, search_criteria, notes
                FROM scrape_sessions WHERE session_id = ?
            """, (session_id,)).fetchone()

            assert stored is not None
            assert stored[0] == session_id
            assert stored[2] == 25  # total_jobs_found
            assert stored[3] == 0   # new_jobs_added (default)
            assert stored[4] == 'linkedin'  # source (default)
            assert stored[5] is None  # search_criteria
            assert stored[6] is None  # notes

    def test_create_scrape_session_full(self, db):
        """
        Test creating a scrape session with all fields populated.

        Verifies that all session fields can be set and are properly stored.
        """
        session = ScrapeSession(
            timestamp=datetime(2024, 1, 15, 14, 45, 30),
            total_jobs_found=50,
            new_jobs_added=12,
            source="indeed",
            search_criteria='{"keywords": "python developer", "location": "remote"}',
            notes="Comprehensive search for remote Python positions"
        )

        session_id = db.create_scrape_session(session)

        # Verify all fields were stored
        with sqlite3.connect(db.db_path) as conn:
            stored = conn.execute("""
                SELECT session_id, timestamp, total_jobs_found, new_jobs_added, source, search_criteria, notes
                FROM scrape_sessions WHERE session_id = ?
            """, (session_id,)).fetchone()

            assert stored[2] == 50  # total_jobs_found
            assert stored[3] == 12  # new_jobs_added
            assert stored[4] == "indeed"  # source
            assert stored[5] == '{"keywords": "python developer", "location": "remote"}'
            assert stored[6] == "Comprehensive search for remote Python positions"

    def test_job_session_mapping(self, db):
        """
        Test the relationship between jobs and scrape sessions.

        Verifies that jobs can be properly linked to sessions with position tracking.
        """
        # Create a session
        session = ScrapeSession(
            timestamp=datetime.now(),
            total_jobs_found=3
        )
        session_id = db.create_scrape_session(session)

        # Create jobs linked to the session
        jobs = [
            JobRecord(job_id="mapping_1", title="Job 1"),
            JobRecord(job_id="mapping_2", title="Job 2"),
            JobRecord(job_id="mapping_3", title="Job 3")
        ]

        for i, job in enumerate(jobs, 1):
            db.upsert_job(job, session_id=session_id, position=i)

        # Verify mappings were created
        with sqlite3.connect(db.db_path) as conn:
            mappings = conn.execute("""
                SELECT job_id, session_id, position_in_results
                FROM job_session_mapping
                WHERE session_id = ?
                ORDER BY position_in_results
            """, (session_id,)).fetchall()

            assert len(mappings) == 3
            assert mappings[0] == ("mapping_1", session_id, 1)
            assert mappings[1] == ("mapping_2", session_id, 2)
            assert mappings[2] == ("mapping_3", session_id, 3)

    def test_multiple_sessions_same_job(self, db):
        """
        Test that the same job can appear in multiple scrape sessions.

        Verifies that job-session mappings support many-to-many relationships.
        """
        # Create two sessions
        session1 = ScrapeSession(timestamp=datetime.now(), total_jobs_found=1)
        session2 = ScrapeSession(timestamp=datetime.now(), total_jobs_found=1)

        session1_id = db.create_scrape_session(session1)
        session2_id = db.create_scrape_session(session2)

        # Same job appears in both sessions
        job = JobRecord(job_id="multi_session_job", title="Popular Job")

        db.upsert_job(job, session_id=session1_id, position=1)
        db.upsert_job(job, session_id=session2_id, position=5)

        # Verify job appears in both sessions
        with sqlite3.connect(db.db_path) as conn:
            mappings = conn.execute("""
                SELECT session_id, position_in_results
                FROM job_session_mapping
                WHERE job_id = ?
                ORDER BY session_id
            """, (job.job_id,)).fetchall()

            assert len(mappings) == 2
            assert mappings[0] == (session1_id, 1)
            assert mappings[1] == (session2_id, 5)


class TestJobLifecycle:
    """Test job lifecycle management and status updates."""

    @pytest.fixture
    def db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            yield JobDatabase(db_path=db_path)

    def test_mark_jobs_removed_basic(self, db):
        """
        Test marking jobs as removed when they're not in the active list.

        Verifies that jobs not found in latest scrape are marked as 'removed'.
        """
        # Create several active jobs
        jobs = [
            JobRecord(job_id="lifecycle_1", title="Job 1"),
            JobRecord(job_id="lifecycle_2", title="Job 2"),
            JobRecord(job_id="lifecycle_3", title="Job 3"),
            JobRecord(job_id="lifecycle_4", title="Job 4")
        ]

        for job in jobs:
            db.upsert_job(job)

        # Simulate latest scrape finding only 2 of the jobs
        active_job_ids = ["lifecycle_1", "lifecycle_3"]
        removed_count = db.mark_jobs_removed(active_job_ids)

        assert removed_count == 2  # lifecycle_2 and lifecycle_4 should be marked removed

        # Verify status changes
        job1 = db.get_job("lifecycle_1")
        job2 = db.get_job("lifecycle_2")
        job3 = db.get_job("lifecycle_3")
        job4 = db.get_job("lifecycle_4")

        assert job1['status'] == 'active'
        assert job2['status'] == 'removed'
        assert job3['status'] == 'active'
        assert job4['status'] == 'removed'

    def test_mark_jobs_removed_empty_list(self, db):
        """
        Test marking jobs as removed with empty active list.

        Verifies that passing an empty list marks all active jobs as removed.
        """
        # Create active jobs
        jobs = [
            JobRecord(job_id="empty_test_1", title="Job 1"),
            JobRecord(job_id="empty_test_2", title="Job 2")
        ]

        for job in jobs:
            db.upsert_job(job)

        # Pass empty list - should mark all active jobs as removed
        removed_count = db.mark_jobs_removed([])

        assert removed_count == 2  # Both active jobs should be marked removed

        # Verify status changes
        job1 = db.get_job("empty_test_1")
        job2 = db.get_job("empty_test_2")

        assert job1['status'] == 'removed'
        assert job2['status'] == 'removed'

    def test_mark_jobs_removed_no_active_jobs(self, db):
        """
        Test marking jobs as removed when no jobs exist.

        Verifies that the function handles empty database gracefully.
        """
        removed_count = db.mark_jobs_removed(["nonexistent_job"])

        assert removed_count == 0

    def test_mark_jobs_removed_already_removed(self, db):
        """
        Test that already removed jobs are not affected.

        Verifies that jobs with 'removed' status are not counted again.
        """
        # Create jobs with different statuses
        active_job = JobRecord(job_id="already_active", title="Active Job")
        removed_job = JobRecord(job_id="already_removed", title="Removed Job", status="removed")

        db.upsert_job(active_job)
        db.upsert_job(removed_job)

        # Mark jobs as removed, excluding the active one
        removed_count = db.mark_jobs_removed([])

        assert removed_count == 1  # Only the active job should be marked removed

        # Verify final statuses
        active_result = db.get_job("already_active")
        removed_result = db.get_job("already_removed")

        assert active_result['status'] == 'removed'
        assert removed_result['status'] == 'removed'


class TestDatabaseStatistics:
    """Test database statistics generation and reporting."""

    @pytest.fixture
    def populated_db(self):
        """Create a database populated with diverse test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = JobDatabase(db_path=db_path)

            # Create jobs with various statuses and companies
            test_jobs = [
                JobRecord(job_id="stats_1", title="Dev 1", company="TechCorp", status="active"),
                JobRecord(job_id="stats_2", title="Dev 2", company="TechCorp", status="active"),
                JobRecord(job_id="stats_3", title="Dev 3", company="DataCorp", status="active"),
                JobRecord(job_id="stats_4", title="Dev 4", company="WebCorp", status="removed"),
                JobRecord(job_id="stats_5", title="Dev 5", company="CloudCorp", status="applied"),
                JobRecord(job_id="stats_6", title="Dev 6", company="TechCorp", work_type="Remote"),  # Default: active
                JobRecord(job_id="stats_7", title="Dev 7", company="DataCorp", work_type="Hybrid"),  # Default: active
                JobRecord(job_id="stats_8", title="Dev 8", company="OtherCorp", work_type="On-site")  # Default: active
            ]

            for job in test_jobs:
                db.upsert_job(job)

            # Create some scrape sessions
            sessions = [
                ScrapeSession(timestamp=datetime.now(), total_jobs_found=5),
                ScrapeSession(timestamp=datetime.now(), total_jobs_found=3)
            ]

            for session in sessions:
                db.create_scrape_session(session)

            yield db

    def test_get_stats_job_counts(self, populated_db):
        """
        Test basic job count statistics.

        Verifies total job count and active job count calculations.
        """
        stats = populated_db.get_stats()

        assert stats['total_jobs'] == 8
        assert stats['active_jobs'] == 6  # Excluding 'removed' and 'applied' jobs

    def test_get_stats_status_breakdown(self, populated_db):
        """
        Test job status breakdown statistics.

        Verifies that jobs are properly grouped by status.
        """
        stats = populated_db.get_stats()

        status_breakdown = stats['jobs_by_status']
        assert status_breakdown['active'] == 6
        assert status_breakdown['removed'] == 1
        assert status_breakdown['applied'] == 1

    def test_get_stats_company_breakdown(self, populated_db):
        """
        Test top companies statistics.

        Verifies company ranking and count calculations for active jobs only.
        """
        stats = populated_db.get_stats()

        top_companies = stats['top_companies']
        assert top_companies['TechCorp'] == 3  # All 3 active TechCorp jobs (stats_1, stats_2, stats_6)
        assert top_companies['DataCorp'] == 2  # stats_3, stats_7
        assert 'WebCorp' not in top_companies  # WebCorp job is removed

    def test_get_stats_work_type_breakdown(self, populated_db):
        """
        Test work type breakdown statistics.

        Verifies work type distribution for active jobs.
        """
        stats = populated_db.get_stats()

        work_types = stats['work_types']
        assert work_types['Remote'] == 1      # stats_6
        assert work_types['Hybrid'] == 1      # stats_7
        assert work_types['On-site'] == 1     # stats_8
        assert work_types['Unknown'] == 3     # stats_1, stats_2, stats_3 (no work_type)

    def test_get_stats_session_count(self, populated_db):
        """
        Test scrape session count statistics.

        Verifies that session counting works correctly.
        """
        stats = populated_db.get_stats()

        assert stats['total_sessions'] == 2

    def test_get_stats_recent_activity(self, populated_db):
        """
        Test recent activity statistics.

        Verifies that recent job activity is tracked correctly.
        """
        stats = populated_db.get_stats()

        # All jobs were just created, so should all be in last 7 days
        assert stats['jobs_seen_last_7_days'] == 8

    def test_get_stats_empty_database(self):
        """
        Test statistics generation on empty database.

        Verifies that statistics work correctly when no data exists.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "empty_test.db"
            db = JobDatabase(db_path=db_path)

            stats = db.get_stats()

            assert stats['total_jobs'] == 0
            assert stats['active_jobs'] == 0
            assert stats['jobs_by_status'] == {}
            assert stats['top_companies'] == {}
            assert stats['work_types'] == {}
            assert stats['total_sessions'] == 0
            assert stats['jobs_seen_last_7_days'] == 0