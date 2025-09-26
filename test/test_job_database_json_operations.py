"""
Comprehensive tests for database operations with JSON storage.

This test suite validates database operations using the new JSON-centric schema,
including upsert operations, search functionality, and data retrieval while
maintaining the existing external API.
"""

import sqlite3
import json
import tempfile
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, '.')
from lib.job_database import JobDatabase, JobRecord, ScrapeSession


class TestJSONUpsertOperations:
    """Test job upsert operations with JSON storage backend."""

    @pytest.fixture
    def db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "json_ops_test.db"
            yield JobDatabase(db_path=db_path)

    def test_upsert_job_new_json_insertion(self, db):
        """
        Test inserting new job using JSON storage internally.

        Verifies that JobRecord is converted to JSON and stored correctly
        while maintaining the external API contract.
        """
        job = JobRecord(
            job_id="json_upsert_001",
            title="Cloud Engineer",
            company="CloudTech Inc",
            work_type="Remote",
            location="Seattle, WA",
            salary="$110K/yr - $140K/yr",
            benefits="Health, Vision, 401k, Stock Options",
            url="https://cloudtech.com/jobs/json_upsert_001",
            description="Design and manage cloud infrastructure using AWS and Kubernetes",
            status="active",
            source="linkedin"
        )

        was_inserted, was_updated = db.upsert_job(job)

        assert was_inserted is True
        assert was_updated is False

        # Verify job was stored correctly via external API
        stored_job = db.get_job("json_upsert_001")
        assert stored_job is not None
        assert stored_job['job_id'] == "json_upsert_001"
        assert stored_job['title'] == "Cloud Engineer"
        assert stored_job['company'] == "CloudTech Inc"
        assert stored_job['work_type'] == "Remote"
        assert stored_job['location'] == "Seattle, WA"
        assert stored_job['salary'] == "$110K/yr - $140K/yr"
        assert stored_job['benefits'] == "Health, Vision, 401k, Stock Options"
        assert stored_job['url'] == "https://cloudtech.com/jobs/json_upsert_001"
        assert stored_job['description'] == "Design and manage cloud infrastructure using AWS and Kubernetes"
        assert stored_job['status'] == "active"
        assert stored_job['source'] == "linkedin"

        # Verify generated salary columns
        assert stored_job['salary_min_yearly'] == 110000
        assert stored_job['salary_max_yearly'] == 140000

        # Verify timestamps were set
        assert stored_job['first_seen'] is not None
        assert stored_job['last_seen'] is not None
        assert stored_job['created_at'] is not None
        assert stored_job['updated_at'] is not None

        # Verify internal JSON storage (implementation detail)
        with sqlite3.connect(db.db_path) as conn:
            json_data = conn.execute(
                "SELECT json_data FROM jobs WHERE job_id = ?",
                (job.job_id,)
            ).fetchone()[0]

            parsed_json = json.loads(json_data)
            assert parsed_json['job_id'] == "json_upsert_001"
            assert parsed_json['title'] == "Cloud Engineer"
            assert parsed_json['company'] == "CloudTech Inc"

    def test_upsert_job_update_json_data(self, db):
        """
        Test updating existing job modifies JSON data correctly.

        Verifies that job updates modify the underlying JSON while
        maintaining external API consistency.
        """
        # Insert initial job
        original_job = JobRecord(
            job_id="json_update_001",
            title="Junior DevOps",
            company="StartupCorp",
            work_type="On-site",
            salary="$75K/yr"
        )

        db.upsert_job(original_job)

        # Update the job with new information
        updated_job = JobRecord(
            job_id="json_update_001",
            title="Senior DevOps Engineer",  # Changed
            company="StartupCorp",
            work_type="Hybrid",  # Changed
            location="Austin, TX",  # Added
            salary="$105K/yr - $125K/yr",  # Changed
            benefits="Health, Dental, 401k",  # Added
            description="Lead DevOps initiatives and mentor junior engineers"  # Added
        )

        was_inserted, was_updated = db.upsert_job(updated_job)

        assert was_inserted is False
        assert was_updated is True

        # Verify updates via external API
        stored_job = db.get_job("json_update_001")
        assert stored_job['title'] == "Senior DevOps Engineer"
        assert stored_job['work_type'] == "Hybrid"
        assert stored_job['location'] == "Austin, TX"
        assert stored_job['salary'] == "$105K/yr - $125K/yr"
        assert stored_job['benefits'] == "Health, Dental, 401k"
        assert stored_job['description'] == "Lead DevOps initiatives and mentor junior engineers"

        # Verify generated columns updated
        assert stored_job['salary_min_yearly'] == 105000
        assert stored_job['salary_max_yearly'] == 125000

        # Verify JSON data was updated internally
        with sqlite3.connect(db.db_path) as conn:
            json_data = conn.execute(
                "SELECT json_data FROM jobs WHERE job_id = ?",
                (updated_job.job_id,)
            ).fetchone()[0]

            parsed_json = json.loads(json_data)
            assert parsed_json['title'] == "Senior DevOps Engineer"
            assert parsed_json['work_type'] == "Hybrid"
            assert parsed_json['location'] == "Austin, TX"
            assert parsed_json['salary'] == "$105K/yr - $125K/yr"

    def test_upsert_job_partial_update(self, db):
        """
        Test updating job with partial data preserves existing fields.

        Verifies that partial updates only modify specified fields
        and preserve other data in JSON storage.
        """
        # Insert complete job
        complete_job = JobRecord(
            job_id="partial_update_001",
            title="Data Engineer",
            company="DataCorp",
            work_type="Remote",
            location="Chicago, IL",
            salary="$95K/yr - $115K/yr",
            benefits="Health, Dental",
            url="https://datacorp.com/jobs/partial_update_001",
            description="Build data pipelines and analytics systems"
        )

        db.upsert_job(complete_job)

        # Update with partial data (only title and salary)
        partial_job = JobRecord(
            job_id="partial_update_001",
            title="Senior Data Engineer",  # Updated
            salary="$115K/yr - $135K/yr",  # Updated
            # Other fields should be preserved from original
        )

        # Mock the implementation to handle partial updates correctly
        # This test defines the expected behavior - implementation needs to preserve existing fields
        was_inserted, was_updated = db.upsert_job(partial_job, preserve_existing=True)

        assert was_inserted is False
        assert was_updated is True

        # Verify updated fields changed and others preserved
        stored_job = db.get_job("partial_update_001")
        assert stored_job['title'] == "Senior Data Engineer"  # Updated
        assert stored_job['salary'] == "$115K/yr - $135K/yr"  # Updated

        # These should be preserved from original
        assert stored_job['company'] == "DataCorp"
        assert stored_job['work_type'] == "Remote"
        assert stored_job['location'] == "Chicago, IL"
        assert stored_job['benefits'] == "Health, Dental"
        assert stored_job['url'] == "https://datacorp.com/jobs/partial_update_001"
        assert stored_job['description'] == "Build data pipelines and analytics systems"

    def test_upsert_job_with_session_mapping_json(self, db):
        """
        Test job upsert with session mapping using JSON storage.

        Verifies that session mapping works correctly with JSON backend
        and maintains referential integrity.
        """
        # Create scrape session
        session = ScrapeSession(
            timestamp=datetime.now(),
            total_jobs_found=5,
            new_jobs_added=3,
            search_criteria='{"keywords": "python", "location": "remote"}'
        )
        session_id = db.create_scrape_session(session)

        # Insert job with session mapping
        job = JobRecord(
            job_id="session_json_001",
            title="Python API Developer",
            company="APItech",
            work_type="Remote",
            salary="$100K/yr - $120K/yr"
        )

        was_inserted, was_updated = db.upsert_job(job, session_id=session_id, position=2)

        assert was_inserted is True

        # Verify job exists and is accessible
        stored_job = db.get_job("session_json_001")
        assert stored_job['job_id'] == "session_json_001"
        assert stored_job['title'] == "Python API Developer"

        # Verify session mapping
        with sqlite3.connect(db.db_path) as conn:
            mapping = conn.execute("""
                SELECT job_id, session_id, position_in_results
                FROM job_session_mapping
                WHERE job_id = ? AND session_id = ?
            """, (job.job_id, session_id)).fetchone()

            assert mapping is not None
            assert mapping[0] == "session_json_001"
            assert mapping[1] == session_id
            assert mapping[2] == 2

    def test_upsert_job_minimal_json(self, db):
        """
        Test upserting job with minimal data using JSON storage.

        Verifies that minimal JobRecord data is correctly stored
        in JSON format with appropriate null handling.
        """
        minimal_job = JobRecord(job_id="minimal_json_001")

        was_inserted, was_updated = db.upsert_job(minimal_job)

        assert was_inserted is True

        # Verify via external API
        stored_job = db.get_job("minimal_json_001")
        assert stored_job['job_id'] == "minimal_json_001"
        assert stored_job['title'] is None
        assert stored_job['company'] is None
        assert stored_job['work_type'] is None
        assert stored_job['location'] is None
        assert stored_job['salary'] is None
        assert stored_job['benefits'] is None
        assert stored_job['url'] is None
        assert stored_job['description'] is None
        assert stored_job['status'] == 'active'  # Default
        assert stored_job['source'] == 'linkedin'  # Default

        # Verify JSON structure internally
        with sqlite3.connect(db.db_path) as conn:
            json_data = conn.execute(
                "SELECT json_data FROM jobs WHERE job_id = ?",
                (minimal_job.job_id,)
            ).fetchone()[0]

            parsed_json = json.loads(json_data)
            assert parsed_json['job_id'] == "minimal_json_001"
            assert parsed_json['status'] == "active"
            assert parsed_json['source'] == "linkedin"
            # Null/missing fields should be handled appropriately


class TestJSONSearchOperations:
    """Test search operations with JSON storage backend."""

    @pytest.fixture
    def populated_json_db(self):
        """Create database with test data stored as JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "json_search_test.db"
            db = JobDatabase(db_path=db_path)

            # Create diverse test jobs that will be stored as JSON
            test_jobs = [
                JobRecord(
                    job_id="json_search_1",
                    title="Senior Python Developer",
                    company="TechCorp",
                    work_type="Remote",
                    location="San Francisco, CA",
                    salary="$120K/yr - $150K/yr",
                    description="Build scalable Python web applications"
                ),
                JobRecord(
                    job_id="json_search_2",
                    title="Machine Learning Engineer",
                    company="AITech",
                    work_type="Hybrid",
                    location="New York, NY",
                    salary="$130K/yr - $170K/yr",
                    description="Develop ML models using Python and TensorFlow"
                ),
                JobRecord(
                    job_id="json_search_3",
                    title="DevOps Engineer",
                    company="CloudCorp",
                    work_type="Remote",
                    location="Austin, TX",
                    salary="$105K/yr - $125K/yr",
                    description="Manage cloud infrastructure and CI/CD pipelines"
                ),
                JobRecord(
                    job_id="json_search_4",
                    title="Frontend Developer",
                    company="WebTech",
                    work_type="On-site",
                    location="Seattle, WA",
                    salary="$90K/yr - $110K/yr",
                    description="Create responsive web interfaces using React"
                ),
                JobRecord(
                    job_id="json_search_5",
                    title="Data Scientist",
                    company="DataCorp",
                    work_type="Hybrid",
                    location="Boston, MA",
                    salary="$115K/yr - $140K/yr",
                    description="Analyze data and build predictive models with Python"
                )
            ]

            for job in test_jobs:
                db.upsert_job(job)

            yield db

    def test_search_jobs_json_backend_compatibility(self, populated_json_db):
        """
        Test that search functionality works with JSON storage.

        Verifies that existing search API returns correct results
        when data is stored internally as JSON.
        """
        # Search all active jobs
        all_jobs = populated_json_db.search_jobs()
        assert len(all_jobs) == 5

        # All should be active
        for job in all_jobs:
            assert job['status'] == 'active'

        # Verify generated columns work in search results
        for job in all_jobs:
            if job['salary']:
                assert job['salary_min_yearly'] is not None
                assert job['salary_max_yearly'] is not None

    def test_search_jobs_by_generated_column(self, populated_json_db):
        """
        Test searching by generated columns works with JSON backend.

        Verifies that generated columns are properly indexed and searchable
        even when source data is in JSON format.
        """
        # Search by company (generated column from JSON)
        techcorp_jobs = populated_json_db.search_jobs(company="TechCorp")
        assert len(techcorp_jobs) == 1
        assert techcorp_jobs[0]['company'] == "TechCorp"
        assert techcorp_jobs[0]['job_id'] == "json_search_1"

        # Search by work type (generated column from JSON)
        remote_jobs = populated_json_db.search_jobs(work_type="Remote")
        assert len(remote_jobs) == 2  # json_search_1 and json_search_3

        remote_job_ids = {job['job_id'] for job in remote_jobs}
        assert remote_job_ids == {"json_search_1", "json_search_3"}

    def test_search_jobs_by_salary_json_generated(self, populated_json_db):
        """
        Test salary range search with JSON-generated salary columns.

        Verifies that salary parsing from JSON works correctly
        for search operations.
        """
        # Jobs with minimum salary >= $120K
        high_salary_jobs = populated_json_db.search_jobs(min_salary=120000)
        assert len(high_salary_jobs) == 2  # json_search_1 ($120K-$150K) and json_search_2 ($130K-$170K)

        high_salary_ids = {job['job_id'] for job in high_salary_jobs}
        assert high_salary_ids == {"json_search_1", "json_search_2"}

        # Jobs with maximum salary <= $125K
        low_max_jobs = populated_json_db.search_jobs(max_salary=125000)
        assert len(low_max_jobs) == 2  # json_search_3 ($105K-$125K) and json_search_4 ($90K-$110K)

        low_max_ids = {job['job_id'] for job in low_max_jobs}
        assert low_max_ids == {"json_search_3", "json_search_4"}

    def test_search_jobs_fts_with_json(self, populated_json_db):
        """
        Test full-text search functionality with JSON storage.

        Verifies that FTS works correctly when job data is stored as JSON
        and extracted via generated columns.
        """
        # Search for Python in descriptions/titles
        python_jobs = populated_json_db.search_jobs(query="Python")
        assert len(python_jobs) == 3  # json_search_1, json_search_2, json_search_5

        python_job_ids = {job['job_id'] for job in python_jobs}
        assert python_job_ids == {"json_search_1", "json_search_2", "json_search_5"}

        # Search for specific company
        techcorp_fts = populated_json_db.search_jobs(query="TechCorp")
        assert len(techcorp_fts) == 1
        assert techcorp_fts[0]['job_id'] == "json_search_1"

        # Search in descriptions
        ml_jobs = populated_json_db.search_jobs(query="machine learning")
        assert len(ml_jobs) == 1
        assert ml_jobs[0]['job_id'] == "json_search_2"

    def test_search_jobs_combined_filters_json(self, populated_json_db):
        """
        Test combined search filters with JSON backend.

        Verifies that multiple search criteria work together correctly
        when data is stored as JSON.
        """
        # Company + work type + salary range
        filtered_jobs = populated_json_db.search_jobs(
            work_type="Hybrid",
            min_salary=115000,
            max_salary=150000
        )

        # Should find json_search_2 (ML Engineer, Hybrid, $130K-$170K) and
        # json_search_5 (Data Scientist, Hybrid, $115K-$140K)
        assert len(filtered_jobs) == 2

        filtered_ids = {job['job_id'] for job in filtered_jobs}
        assert filtered_ids == {"json_search_2", "json_search_5"}

        # FTS + location filter
        python_west_coast = populated_json_db.search_jobs(
            query="Python",
            location="CA"
        )
        assert len(python_west_coast) == 1
        assert python_west_coast[0]['job_id'] == "json_search_1"


class TestJSONRetrievalOperations:
    """Test data retrieval operations with JSON storage."""

    @pytest.fixture
    def db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "json_retrieval_test.db"
            yield JobDatabase(db_path=db_path)

    def test_get_job_json_to_dict_conversion(self, db):
        """
        Test get_job returns proper dictionary from JSON storage.

        Verifies that JSON data is correctly converted to dictionary
        format expected by external API.
        """
        # Store job that will be saved as JSON internally
        job = JobRecord(
            job_id="retrieval_001",
            title="Site Reliability Engineer",
            company="InfraTech",
            work_type="Remote",
            location="Portland, OR",
            salary="$125K/yr - $145K/yr",
            benefits="Health, Dental, Vision, 401k, Stock Options",
            url="https://infratech.com/jobs/retrieval_001",
            description="Ensure system reliability and performance at scale",
            status="active",
            source="indeed"
        )

        db.upsert_job(job)

        # Retrieve and verify format
        retrieved = db.get_job("retrieval_001")

        assert retrieved is not None
        assert isinstance(retrieved, dict)

        # Verify all expected fields are present and correct
        expected_fields = [
            'job_id', 'title', 'company', 'work_type', 'location',
            'salary', 'benefits', 'url', 'description', 'status', 'source',
            'salary_min_yearly', 'salary_max_yearly',
            'first_seen', 'last_seen', 'created_at', 'updated_at'
        ]

        for field in expected_fields:
            assert field in retrieved, f"Field {field} missing from retrieved job"

        assert retrieved['job_id'] == "retrieval_001"
        assert retrieved['title'] == "Site Reliability Engineer"
        assert retrieved['company'] == "InfraTech"
        assert retrieved['salary_min_yearly'] == 125000
        assert retrieved['salary_max_yearly'] == 145000

    def test_get_job_nonexistent_json(self, db):
        """
        Test retrieving non-existent job with JSON storage.

        Verifies that get_job returns None for non-existent jobs
        even with JSON backend.
        """
        result = db.get_job("nonexistent_job_json")
        assert result is None

    def test_get_job_handles_json_null_fields(self, db):
        """
        Test get_job properly handles NULL JSON fields.

        Verifies that NULL or missing JSON fields are properly
        converted to None in the returned dictionary.
        """
        # Store job with many NULL fields
        job = JobRecord(
            job_id="null_fields_001",
            title="Minimal Job"
            # Most fields will be None/NULL
        )

        db.upsert_job(job)

        retrieved = db.get_job("null_fields_001")

        assert retrieved is not None
        assert retrieved['job_id'] == "null_fields_001"
        assert retrieved['title'] == "Minimal Job"
        assert retrieved['company'] is None
        assert retrieved['work_type'] is None
        assert retrieved['location'] is None
        assert retrieved['salary'] is None
        assert retrieved['benefits'] is None
        assert retrieved['url'] is None
        assert retrieved['description'] is None
        assert retrieved['status'] == 'active'  # Default
        assert retrieved['source'] == 'linkedin'  # Default
        assert retrieved['salary_min_yearly'] is None
        assert retrieved['salary_max_yearly'] is None

    def test_batch_job_retrieval_json(self, db):
        """
        Test retrieving multiple jobs efficiently with JSON storage.

        Verifies that batch operations work correctly with JSON backend
        and maintain performance characteristics.
        """
        # Store multiple jobs
        jobs = [
            JobRecord(job_id=f"batch_{i}", title=f"Job {i}", company=f"Company{i}")
            for i in range(5)
        ]

        for job in jobs:
            db.upsert_job(job)

        # Retrieve all jobs
        all_jobs = db.search_jobs()
        assert len(all_jobs) == 5

        # Verify all jobs are properly formatted
        for i, job in enumerate(all_jobs):
            assert job['job_id'] in [f"batch_{j}" for j in range(5)]
            assert job['title'] in [f"Job {j}" for j in range(5)]
            assert isinstance(job, dict)
            assert all(key in job for key in ['job_id', 'title', 'company', 'status', 'source'])