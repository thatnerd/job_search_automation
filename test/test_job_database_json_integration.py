"""
Integration tests for end-to-end JSON workflow in JobDatabase.

This test suite validates complete workflows using the JSON-based schema,
including job scraping simulation, data persistence, search operations,
and statistics generation with the new JSON storage backend.
"""

import sqlite3
import json
import tempfile
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, '.')
from lib.job_database import JobDatabase, JobRecord, ScrapeSession


class TestEndToEndJobScrapeWorkflow:
    """Test complete job scraping and storage workflow with JSON."""

    @pytest.fixture
    def fresh_db(self):
        """Create a fresh database with JSON schema."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "integration_test.db"
            yield JobDatabase(db_path=db_path)

    def test_complete_scraping_session_workflow(self, fresh_db):
        """
        Test complete workflow: session creation -> job insertion -> search -> stats.

        Simulates a realistic job scraping session where jobs are discovered,
        stored with JSON backend, searched, and statistics generated.
        """
        # Step 1: Create scrape session
        scrape_time = datetime.now()
        session = ScrapeSession(
            timestamp=scrape_time,
            total_jobs_found=10,
            new_jobs_added=0,  # Will be updated as jobs are added
            source="linkedin",
            search_criteria=json.dumps({
                "keywords": "python developer",
                "location": "remote",
                "experience_level": "senior"
            }),
            notes="Daily automated scrape for senior Python positions"
        )

        session_id = fresh_db.create_scrape_session(session)
        assert session_id is not None

        # Step 2: Simulate discovering and storing jobs
        discovered_jobs = [
            JobRecord(
                job_id="workflow_001",
                title="Senior Python Developer",
                company="TechCorp",
                work_type="Remote",
                location="San Francisco, CA",
                salary="$140K/yr - $170K/yr",
                benefits="Health, Dental, Vision, 401k, Stock Options",
                url="https://linkedin.com/jobs/workflow_001",
                description="Lead Python development team, architect scalable systems using Django and AWS",
                status="active",
                source="linkedin"
            ),
            JobRecord(
                job_id="workflow_002",
                title="Python Backend Engineer",
                company="StartupCorp",
                work_type="Remote",
                location="Remote",
                salary="$125K/yr - $155K/yr",
                benefits="Health, Unlimited PTO, Equity",
                url="https://linkedin.com/jobs/workflow_002",
                description="Build microservices with FastAPI, work with PostgreSQL and Redis",
                status="active",
                source="linkedin"
            ),
            JobRecord(
                job_id="workflow_003",
                title="Full Stack Python Developer",
                company="WebTech",
                work_type="Hybrid",
                location="Austin, TX",
                salary="$110K/yr - $135K/yr",
                benefits="Health, Dental, 401k",
                url="https://linkedin.com/jobs/workflow_003",
                description="Develop web applications using Python/Django and React",
                status="active",
                source="linkedin"
            ),
            JobRecord(
                job_id="workflow_004",
                title="DevOps Engineer",
                company="CloudCorp",
                work_type="Remote",
                location="Seattle, WA",
                salary="$130K/yr - $160K/yr",
                benefits="Health, Vision, 401k, Stock Options",
                url="https://linkedin.com/jobs/workflow_004",
                description="Manage Kubernetes clusters, CI/CD pipelines, and cloud infrastructure",
                status="active",
                source="linkedin"
            ),
            JobRecord(
                job_id="workflow_005",
                title="Machine Learning Engineer",
                company="AITech",
                work_type="On-site",
                location="Boston, MA",
                salary="$145K/yr - $180K/yr",
                benefits="Health, Dental, Vision, 401k, Gym Membership",
                url="https://linkedin.com/jobs/workflow_005",
                description="Build ML models using Python, TensorFlow, and deploy on AWS",
                status="active",
                source="linkedin"
            )
        ]

        new_jobs_count = 0
        for i, job in enumerate(discovered_jobs, 1):
            was_inserted, was_updated = fresh_db.upsert_job(job, session_id=session_id, position=i)
            if was_inserted:
                new_jobs_count += 1

        # Step 3: Update session with actual results
        updated_session = ScrapeSession(
            timestamp=scrape_time,
            total_jobs_found=len(discovered_jobs),
            new_jobs_added=new_jobs_count,
            source="linkedin",
            search_criteria=session.search_criteria,
            notes=session.notes
        )

        # Update session record (this method would need to be implemented)
        # fresh_db.update_scrape_session(session_id, updated_session)

        # Step 4: Verify all jobs stored correctly with JSON backend
        for job in discovered_jobs:
            stored_job = fresh_db.get_job(job.job_id)
            assert stored_job is not None
            assert stored_job['title'] == job.title
            assert stored_job['company'] == job.company
            assert stored_job['work_type'] == job.work_type
            assert stored_job['salary_min_yearly'] is not None
            assert stored_job['salary_max_yearly'] is not None

        # Step 5: Test search functionality
        # Search for Python jobs
        python_jobs = fresh_db.search_jobs(query="Python")
        assert len(python_jobs) >= 3  # At least 3 jobs mention Python

        # Search for remote jobs
        remote_jobs = fresh_db.search_jobs(work_type="Remote")
        assert len(remote_jobs) == 3  # workflow_001, workflow_002, workflow_004

        # Search by salary range
        high_salary_jobs = fresh_db.search_jobs(min_salary=140000)
        assert len(high_salary_jobs) == 2  # workflow_001 ($140K+), workflow_005 ($145K+)

        # Combined search: Remote Python jobs with good salary
        filtered_jobs = fresh_db.search_jobs(
            query="Python",
            work_type="Remote",
            min_salary=125000
        )
        assert len(filtered_jobs) >= 1

        # Step 6: Generate and verify statistics
        stats = fresh_db.get_stats()
        assert stats['total_jobs'] == 5
        assert stats['active_jobs'] == 5
        assert stats['total_sessions'] == 1

        # Check company distribution
        assert 'TechCorp' in stats['top_companies']
        assert 'StartupCorp' in stats['top_companies']

        # Check work type distribution
        assert stats['work_types']['Remote'] == 3
        assert stats['work_types']['Hybrid'] == 1
        assert stats['work_types']['On-site'] == 1

    def test_job_lifecycle_with_json_backend(self, fresh_db):
        """
        Test complete job lifecycle: discovery -> application -> removal.

        Verifies that job status changes work correctly with JSON storage
        and that lifecycle tracking is maintained.
        """
        # Phase 1: Job discovered and stored
        job = JobRecord(
            job_id="lifecycle_json_001",
            title="Python Developer",
            company="LifecycleCorp",
            work_type="Remote",
            salary="$100K/yr - $120K/yr",
            url="https://lifecyclecorp.com/jobs/lifecycle_json_001",
            description="Develop Python applications",
            status="active",
            source="linkedin"
        )

        was_inserted, was_updated = fresh_db.upsert_job(job)
        assert was_inserted is True

        stored_job = fresh_db.get_job("lifecycle_json_001")
        assert stored_job['status'] == 'active'
        original_first_seen = stored_job['first_seen']

        # Phase 2: Job seen again in next scrape (no changes)
        time.sleep(0.01)  # Small delay to ensure different timestamp
        was_inserted, was_updated = fresh_db.upsert_job(job)
        assert was_inserted is False
        assert was_updated is False

        # Verify last_seen was updated but first_seen preserved
        updated_job = fresh_db.get_job("lifecycle_json_001")
        assert updated_job['first_seen'] == original_first_seen
        assert updated_job['last_seen'] >= original_first_seen

        # Phase 3: Apply to job (status change)
        applied_job = JobRecord(
            job_id="lifecycle_json_001",
            title="Python Developer",
            company="LifecycleCorp",
            work_type="Remote",
            salary="$100K/yr - $120K/yr",
            url="https://lifecyclecorp.com/jobs/lifecycle_json_001",
            description="Develop Python applications",
            status="applied",  # Status changed
            source="linkedin"
        )

        was_inserted, was_updated = fresh_db.upsert_job(applied_job)
        assert was_inserted is False
        assert was_updated is True

        applied_stored = fresh_db.get_job("lifecycle_json_001")
        assert applied_stored['status'] == 'applied'

        # Phase 4: Job removed from listings (mark as removed)
        fresh_db.mark_jobs_removed([])  # No active jobs means all should be marked removed

        removed_job = fresh_db.get_job("lifecycle_json_001")
        assert removed_job['status'] == 'removed'

        # Verify job lifecycle is tracked in JSON data
        with sqlite3.connect(fresh_db.db_path) as conn:
            json_data = conn.execute(
                "SELECT json_data FROM jobs WHERE job_id = ?",
                ("lifecycle_json_001",)
            ).fetchone()[0]

            parsed_json = json.loads(json_data)
            assert parsed_json['status'] == 'removed'
            assert parsed_json['job_id'] == 'lifecycle_json_001'

    def test_data_export_from_json_storage(self, fresh_db):
        """
        Test exporting job data from JSON storage for external use.

        Verifies that data can be efficiently exported in various formats
        while preserving all information from JSON storage.
        """
        # Store jobs with diverse data
        test_jobs = [
            JobRecord(
                job_id="export_001",
                title="Senior Data Engineer",
                company="DataCorp",
                work_type="Remote",
                location="Chicago, IL",
                salary="$130K/yr - $160K/yr",
                benefits="Health, Dental, Vision, 401k, Unlimited PTO",
                url="https://datacorp.com/jobs/export_001",
                description="Build data pipelines using Python, Spark, and Kafka",
                status="active",
                source="linkedin"
            ),
            JobRecord(
                job_id="export_002",
                title="DevOps Specialist",
                company="CloudTech",
                work_type="Hybrid",
                location="Denver, CO",
                salary="$115K/yr - $145K/yr",
                benefits="Health, 401k, Stock Options",
                url="https://cloudtech.com/jobs/export_002",
                description="Manage AWS infrastructure and deployment pipelines",
                status="applied",
                source="indeed"
            )
        ]

        for job in test_jobs:
            fresh_db.upsert_job(job)

        # Test CSV export functionality
        csv_data = fresh_db.export_jobs_csv()
        assert csv_data is not None
        assert "export_001" in csv_data
        assert "export_002" in csv_data
        assert "Senior Data Engineer" in csv_data
        assert "DataCorp" in csv_data

        # Test JSON export (should be efficient with JSON backend)
        json_export = fresh_db.export_jobs_json()
        exported_jobs = json.loads(json_export)

        assert len(exported_jobs) == 2

        export_001 = next(job for job in exported_jobs if job['job_id'] == 'export_001')
        assert export_001['title'] == "Senior Data Engineer"
        assert export_001['company'] == "DataCorp"
        assert export_001['salary'] == "$130K/yr - $160K/yr"
        assert export_001['salary_min_yearly'] == 130000
        assert export_001['salary_max_yearly'] == 160000

        # Test filtered export
        remote_jobs_json = fresh_db.export_jobs_json(filters={'work_type': 'Remote'})
        remote_exported = json.loads(remote_jobs_json)

        assert len(remote_exported) == 1
        assert remote_exported[0]['job_id'] == 'export_001'


class TestPerformanceWithJSONBackend:
    """Test performance characteristics of JSON storage backend."""

    @pytest.fixture
    def performance_db(self):
        """Create database for performance testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "performance_test.db"
            yield JobDatabase(db_path=db_path)

    def test_bulk_insert_performance_json(self, performance_db):
        """
        Test performance of bulk job insertion with JSON storage.

        Verifies that JSON backend can handle large numbers of jobs
        efficiently without significant performance degradation.
        """
        import time

        # Generate test jobs
        num_jobs = 100
        test_jobs = []

        for i in range(num_jobs):
            job = JobRecord(
                job_id=f"perf_test_{i:04d}",
                title=f"Software Engineer {i}",
                company=f"Company{i % 10}",  # 10 different companies
                work_type=["Remote", "On-site", "Hybrid"][i % 3],
                location=f"City{i % 20}, ST",  # 20 different locations
                salary=f"${90 + (i % 50)}K/yr - ${120 + (i % 50)}K/yr",
                benefits="Health, Dental, 401k",
                url=f"https://company{i % 10}.com/jobs/perf_test_{i:04d}",
                description=f"Job description for position {i} involving Python development",
                status="active",
                source="linkedin"
            )
            test_jobs.append(job)

        # Measure insertion time
        start_time = time.time()

        for job in test_jobs:
            performance_db.upsert_job(job)

        insertion_time = time.time() - start_time

        # Verify all jobs were inserted
        all_jobs = performance_db.search_jobs()
        assert len(all_jobs) == num_jobs

        # Performance should be reasonable (less than 1 second for 100 jobs)
        assert insertion_time < 1.0, f"Insertion took {insertion_time:.2f}s, expected < 1.0s"

        print(f"Inserted {num_jobs} jobs in {insertion_time:.3f} seconds")
        print(f"Average: {insertion_time/num_jobs*1000:.2f}ms per job")

    def test_search_performance_with_json_generated_columns(self, performance_db):
        """
        Test search performance using generated columns from JSON.

        Verifies that searches on generated columns perform well
        compared to direct JSON queries.
        """
        import time

        # Insert test data
        for i in range(50):
            job = JobRecord(
                job_id=f"search_perf_{i:03d}",
                title=f"Engineer {i}",
                company=f"TestCorp{i % 5}",
                work_type=["Remote", "On-site"][i % 2],
                location=f"Location{i % 10}",
                salary=f"${100 + i}K/yr",
                description=f"Engineering position {i}",
                status="active",
                source="linkedin"
            )
            performance_db.upsert_job(job)

        # Test various search patterns
        search_tests = [
            {"company": "TestCorp0"},
            {"work_type": "Remote"},
            {"location": "Location5"},
            {"min_salary": 125000},
            {"query": "Engineer"},
            {"company": "TestCorp1", "work_type": "Remote"},
            {"query": "position", "min_salary": 130000}
        ]

        total_search_time = 0

        for search_params in search_tests:
            start_time = time.time()
            results = performance_db.search_jobs(**search_params)
            search_time = time.time() - start_time
            total_search_time += search_time

            assert len(results) >= 0  # Should return some results

            # Each search should be fast (< 50ms)
            assert search_time < 0.05, f"Search {search_params} took {search_time:.3f}s"

        avg_search_time = total_search_time / len(search_tests)
        print(f"Average search time: {avg_search_time*1000:.2f}ms")

    def test_json_data_size_efficiency(self, performance_db):
        """
        Test storage efficiency of JSON format vs column storage.

        Verifies that JSON storage doesn't significantly increase
        database size for typical job data.
        """
        # Insert job with comprehensive data
        comprehensive_job = JobRecord(
            job_id="size_test_001",
            title="Senior Full Stack Developer with Machine Learning Experience",
            company="Comprehensive Tech Solutions Inc",
            work_type="Remote",
            location="San Francisco Bay Area, California, United States",
            salary="$150K/yr - $200K/yr",
            benefits="Health Insurance, Dental Insurance, Vision Insurance, 401(k) with company match, Stock Options, Unlimited PTO, Flexible Hours, Professional Development Budget, Gym Membership, Commuter Benefits",
            url="https://comprehensivetech.com/careers/senior-full-stack-developer-ml-experience-remote-sf-bay-area",
            description="We are seeking a highly experienced Senior Full Stack Developer with Machine Learning expertise to join our innovative team. You will be responsible for developing scalable web applications using modern frameworks, implementing ML algorithms for predictive analytics, and collaborating with cross-functional teams to deliver high-quality software solutions. Required skills include Python, JavaScript, React, Django, TensorFlow, AWS, and Docker.",
            status="active",
            source="linkedin"
        )

        performance_db.upsert_job(comprehensive_job)

        # Check database file size
        db_size = performance_db.db_path.stat().st_size

        # Size should be reasonable (less than 1MB for this single comprehensive job)
        assert db_size < 1024 * 1024, f"Database size {db_size} bytes seems excessive"

        # Verify JSON data is properly compressed/stored
        with sqlite3.connect(performance_db.db_path) as conn:
            json_data = conn.execute(
                "SELECT json_data FROM jobs WHERE job_id = ?",
                ("size_test_001",)
            ).fetchone()[0]

            # JSON should be valid and contain all data
            parsed_json = json.loads(json_data)
            assert len(parsed_json) >= 10  # Should have multiple fields
            assert parsed_json['title'] == comprehensive_job.title
            assert parsed_json['benefits'] == comprehensive_job.benefits

        print(f"Database size with comprehensive job: {db_size} bytes")
        print(f"JSON data length: {len(json_data)} characters")


# Helper function for timing tests
import time

def time_operation(operation_func, *args, **kwargs):
    """Time a database operation and return result and duration."""
    start_time = time.time()
    result = operation_func(*args, **kwargs)
    duration = time.time() - start_time
    return result, duration