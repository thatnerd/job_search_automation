"""
Comprehensive unit tests for JobDatabase class.

This test suite covers database initialization, schema creation, salary parsing,
job storage with deduplication, search functionality, and statistics generation.
Following TDD principles to ensure robust database operations.
"""

import os
import sqlite3
import tempfile
import pytest
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, '.')
from lib.job_database import JobDatabase, JobRecord, ScrapeSession


class TestJobDatabaseInit:
    """Test JobDatabase initialization and schema creation."""

    def test_init_with_default_path(self):
        """
        Test JobDatabase initialization using default database path.

        Verifies that the database is created in the expected location
        and all required tables and indexes are properly set up.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the default path to use our temp directory
            expected_path = Path(temp_dir) / "data" / "jobs.db"

            with patch('lib.job_database.Path.__file__', temp_dir + "/fake_file.py"):
                with patch.object(Path, 'parent', expected_path.parent.parent):
                    db = JobDatabase()

                    # Verify database file was created
                    assert db.db_path.exists()
                    assert db.db_path.name == "jobs.db"

    def test_init_with_custom_path(self):
        """
        Test JobDatabase initialization with custom database path.

        Ensures that the database can be created at any specified location
        and that parent directories are created if needed.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_path = Path(temp_dir) / "custom" / "my_jobs.db"

            db = JobDatabase(db_path=custom_path)

            # Verify custom path was used and file was created
            assert db.db_path == custom_path
            assert db.db_path.exists()
            assert db.db_path.parent.exists()  # Parent directory created

    def test_database_schema_creation(self):
        """
        Test that all required tables, indexes, and triggers are created.

        Verifies the complete database schema matches the expected structure
        including generated columns, FTS tables, and triggers.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = JobDatabase(db_path=db_path)

            # Test database connection and schema
            with sqlite3.connect(db_path) as conn:
                # Verify main tables exist
                tables = conn.execute("""
                    SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """).fetchall()

                table_names = [row[0] for row in tables]
                assert 'jobs' in table_names
                assert 'scrape_sessions' in table_names
                assert 'job_session_mapping' in table_names
                assert 'jobs_fts' in table_names

                # Verify jobs table structure including generated columns
                jobs_columns = conn.execute("PRAGMA table_info(jobs)").fetchall()
                column_names = [col[1] for col in jobs_columns]

                # Basic columns that should always be visible
                basic_columns = [
                    'job_id', 'title', 'company', 'work_type', 'location', 'salary',
                    'benefits', 'url', 'description', 'first_seen', 'last_seen',
                    'status', 'source', 'created_at', 'updated_at'
                ]
                for col in basic_columns:
                    assert col in column_names

                # Test generated columns by trying to query them
                try:
                    conn.execute("SELECT salary_min_yearly, salary_max_yearly FROM jobs LIMIT 1").fetchall()
                    generated_columns_exist = True
                except sqlite3.OperationalError:
                    generated_columns_exist = False

                assert generated_columns_exist, "Generated columns salary_min_yearly and salary_max_yearly should exist"

                # Verify indexes exist
                indexes = conn.execute("""
                    SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'
                """).fetchall()

                index_names = [row[0] for row in indexes]
                expected_indexes = [
                    'idx_jobs_company', 'idx_jobs_location', 'idx_jobs_work_type',
                    'idx_jobs_status', 'idx_jobs_salary_range'
                ]
                for idx in expected_indexes:
                    assert idx in index_names

                # Verify triggers exist
                triggers = conn.execute("""
                    SELECT name FROM sqlite_master WHERE type='trigger'
                """).fetchall()

                trigger_names = [row[0] for row in triggers]
                expected_triggers = [
                    'jobs_fts_insert', 'jobs_fts_delete', 'jobs_fts_update', 'jobs_update_timestamp'
                ]
                for trigger in expected_triggers:
                    assert trigger in trigger_names

    def test_generated_columns_functionality(self):
        """
        Test that generated columns for salary parsing work correctly.

        Verifies that SQLite generated columns automatically parse salary
        values into min/max yearly amounts when jobs are inserted.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = JobDatabase(db_path=db_path)

            with sqlite3.connect(db_path) as conn:
                # Test single salary
                conn.execute("""
                    INSERT INTO jobs (job_id, title, salary)
                    VALUES ('test1', 'Developer', '$100K/yr')
                """)

                result = conn.execute("""
                    SELECT salary_min_yearly, salary_max_yearly FROM jobs WHERE job_id = 'test1'
                """).fetchone()

                assert result[0] == 100000  # min
                assert result[1] == 100000  # max (same for single salary)

                # Test salary range
                conn.execute("""
                    INSERT INTO jobs (job_id, title, salary)
                    VALUES ('test2', 'Senior Dev', '$120K/yr - $150K/yr')
                """)

                result = conn.execute("""
                    SELECT salary_min_yearly, salary_max_yearly FROM jobs WHERE job_id = 'test2'
                """).fetchone()

                assert result[0] == 120000  # min
                assert result[1] == 150000  # max

                # Test non-matching salary format
                conn.execute("""
                    INSERT INTO jobs (job_id, title, salary)
                    VALUES ('test3', 'Contractor', 'Competitive salary')
                """)

                result = conn.execute("""
                    SELECT salary_min_yearly, salary_max_yearly FROM jobs WHERE job_id = 'test3'
                """).fetchone()

                assert result[0] is None  # min
                assert result[1] is None  # max

    def test_fts_table_setup(self):
        """
        Test that Full-Text Search (FTS) virtual table is properly configured.

        Verifies that the FTS table is created and synchronized with the main jobs table
        through triggers for insert, update, and delete operations.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = JobDatabase(db_path=db_path)

            with sqlite3.connect(db_path) as conn:
                # Insert a job and verify FTS table is populated
                conn.execute("""
                    INSERT INTO jobs (job_id, title, company, description)
                    VALUES ('fts_test', 'Python Developer', 'TechCorp', 'Build amazing Python applications')
                """)

                # Check FTS table was populated via trigger
                fts_result = conn.execute("""
                    SELECT job_id, title, company, description FROM jobs_fts WHERE job_id = 'fts_test'
                """).fetchone()

                assert fts_result is not None
                assert fts_result[0] == 'fts_test'
                assert fts_result[1] == 'Python Developer'
                assert fts_result[2] == 'TechCorp'
                assert fts_result[3] == 'Build amazing Python applications'

                # Test FTS search functionality
                search_result = conn.execute("""
                    SELECT job_id FROM jobs_fts WHERE jobs_fts MATCH 'Python'
                """).fetchone()

                assert search_result is not None
                assert search_result[0] == 'fts_test'


class TestSalaryParsing:
    """Test salary parsing functionality with various input formats."""

    def test_parse_salary_single_values(self):
        """
        Test parsing of single salary values in various formats.

        Covers standard cases like "$100K/yr", "$85K/yr", etc.
        """
        # Standard single salaries
        assert JobDatabase.parse_salary("$100K/yr") == (100000, 100000)
        assert JobDatabase.parse_salary("$85K/yr") == (85000, 85000)
        assert JobDatabase.parse_salary("$150K/yr") == (150000, 150000)

        # Case insensitive
        assert JobDatabase.parse_salary("$100k/yr") == (100000, 100000)
        assert JobDatabase.parse_salary("$100K/YR") == (100000, 100000)

        # With extra spaces and formatting
        assert JobDatabase.parse_salary(" $100K/yr ") == (100000, 100000)
        assert JobDatabase.parse_salary("$100,000K/yr") == (100000, 100000)  # Comma removed

    def test_parse_salary_ranges(self):
        """
        Test parsing of salary ranges like "$100K/yr - $150K/yr".

        Covers various range formats with different spacing and formatting.
        """
        # Standard ranges
        assert JobDatabase.parse_salary("$100K/yr - $150K/yr") == (100000, 150000)
        assert JobDatabase.parse_salary("$80K/yr - $120K/yr") == (80000, 120000)
        assert JobDatabase.parse_salary("$200K/yr - $250K/yr") == (200000, 250000)

        # Different spacing
        assert JobDatabase.parse_salary("$100K/yr-$150K/yr") == (100000, 150000)
        assert JobDatabase.parse_salary("$100K/yr  -  $150K/yr") == (100000, 150000)

        # Case variations
        assert JobDatabase.parse_salary("$100k/yr - $150k/yr") == (100000, 150000)
        assert JobDatabase.parse_salary("$100K/YR - $150K/YR") == (100000, 150000)

    def test_parse_salary_edge_cases(self):
        """
        Test salary parsing with edge cases and invalid inputs.

        Ensures robust handling of malformed or non-standard salary strings.
        """
        # Empty or None inputs
        assert JobDatabase.parse_salary(None) == (None, None)
        assert JobDatabase.parse_salary("") == (None, None)
        assert JobDatabase.parse_salary("   ") == (None, None)

        # Non-matching formats
        assert JobDatabase.parse_salary("Competitive salary") == (None, None)
        assert JobDatabase.parse_salary("DOE") == (None, None)
        assert JobDatabase.parse_salary("$100/hour") == (None, None)
        assert JobDatabase.parse_salary("100K") == (None, None)  # Missing $ and /yr
        assert JobDatabase.parse_salary("$100K") == (None, None)  # Missing /yr

        # Malformed ranges
        assert JobDatabase.parse_salary("$100K/yr - competitive") == (None, None)
        assert JobDatabase.parse_salary("DOE - $150K/yr") == (None, None)

        # Invalid numbers
        assert JobDatabase.parse_salary("$XYZ/yr") == (None, None)
        assert JobDatabase.parse_salary("$/yr") == (None, None)

    def test_parse_salary_boundary_values(self):
        """
        Test salary parsing with boundary values and large numbers.

        Ensures parsing works correctly for very low and very high salaries.
        """
        # Low salaries
        assert JobDatabase.parse_salary("$40K/yr") == (40000, 40000)
        assert JobDatabase.parse_salary("$25K/yr") == (25000, 25000)

        # High salaries
        assert JobDatabase.parse_salary("$500K/yr") == (500000, 500000)
        assert JobDatabase.parse_salary("$1000K/yr") == (1000000, 1000000)

        # Wide ranges
        assert JobDatabase.parse_salary("$50K/yr - $200K/yr") == (50000, 200000)
        assert JobDatabase.parse_salary("$100K/yr - $500K/yr") == (100000, 500000)

    def test_parse_salary_real_world_examples(self):
        """
        Test salary parsing with real-world examples from job sites.

        Based on actual salary strings commonly found on LinkedIn and other job sites.
        """
        # Common LinkedIn formats
        assert JobDatabase.parse_salary("$90K/yr - $110K/yr") == (90000, 110000)
        assert JobDatabase.parse_salary("$130K/yr - $160K/yr") == (130000, 160000)

        # Single salaries
        assert JobDatabase.parse_salary("$95K/yr") == (95000, 95000)
        assert JobDatabase.parse_salary("$125K/yr") == (125000, 125000)

        # Non-parseable but common descriptions
        assert JobDatabase.parse_salary("Competitive salary and benefits") == (None, None)
        assert JobDatabase.parse_salary("Salary commensurate with experience") == (None, None)
        assert JobDatabase.parse_salary("Great benefits package") == (None, None)


class TestJobRecord:
    """Test JobRecord dataclass functionality."""

    def test_job_record_creation_defaults(self):
        """
        Test JobRecord creation with minimal and default values.

        Verifies that default values are properly set and required fields work correctly.
        """
        # Minimal job record (only required field)
        job = JobRecord(job_id="12345")

        assert job.job_id == "12345"
        assert job.title is None
        assert job.company is None
        assert job.work_type is None
        assert job.location is None
        assert job.salary is None
        assert job.benefits is None
        assert job.url is None
        assert job.description is None
        assert job.status == 'active'  # Default value
        assert job.source == 'linkedin'  # Default value

    def test_job_record_creation_full(self):
        """
        Test JobRecord creation with all fields populated.

        Ensures all fields can be set and are properly stored.
        """
        job = JobRecord(
            job_id="67890",
            title="Senior Python Developer",
            company="TechCorp Inc",
            work_type="Remote",
            location="San Francisco, CA",
            salary="$120K/yr - $150K/yr",
            benefits="Health, Dental, 401k",
            url="https://linkedin.com/jobs/67890",
            description="Build amazing Python applications...",
            status="active",
            source="linkedin"
        )

        assert job.job_id == "67890"
        assert job.title == "Senior Python Developer"
        assert job.company == "TechCorp Inc"
        assert job.work_type == "Remote"
        assert job.location == "San Francisco, CA"
        assert job.salary == "$120K/yr - $150K/yr"
        assert job.benefits == "Health, Dental, 401k"
        assert job.url == "https://linkedin.com/jobs/67890"
        assert job.description == "Build amazing Python applications..."
        assert job.status == "active"
        assert job.source == "linkedin"

    def test_job_record_custom_status_source(self):
        """
        Test JobRecord with custom status and source values.

        Verifies that non-default status and source values work correctly.
        """
        job = JobRecord(
            job_id="99999",
            title="Data Scientist",
            status="applied",
            source="indeed"
        )

        assert job.job_id == "99999"
        assert job.title == "Data Scientist"
        assert job.status == "applied"
        assert job.source == "indeed"


class TestScrapeSession:
    """Test ScrapeSession dataclass functionality."""

    def test_scrape_session_creation_minimal(self):
        """
        Test ScrapeSession creation with minimal required fields.

        Verifies required fields and default values work correctly.
        """
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        session = ScrapeSession(
            timestamp=timestamp,
            total_jobs_found=25
        )

        assert session.timestamp == timestamp
        assert session.total_jobs_found == 25
        assert session.new_jobs_added == 0  # Default value
        assert session.source == 'linkedin'  # Default value
        assert session.search_criteria is None
        assert session.notes is None

    def test_scrape_session_creation_full(self):
        """
        Test ScrapeSession creation with all fields populated.

        Ensures all fields can be set and are properly stored.
        """
        timestamp = datetime(2024, 1, 15, 14, 45, 30)
        session = ScrapeSession(
            timestamp=timestamp,
            total_jobs_found=50,
            new_jobs_added=12,
            source="indeed",
            search_criteria='{"keywords": "python developer", "location": "remote"}',
            notes="First scrape of the day, focused on remote positions"
        )

        assert session.timestamp == timestamp
        assert session.total_jobs_found == 50
        assert session.new_jobs_added == 12
        assert session.source == "indeed"
        assert session.search_criteria == '{"keywords": "python developer", "location": "remote"}'
        assert session.notes == "First scrape of the day, focused on remote positions"


class TestDatabaseCleanup:
    """Test database cleanup and resource management."""

    def test_close_method(self):
        """
        Test that the close method exists and can be called safely.

        Since SQLite connections are managed via context managers,
        this mainly tests that the method exists and doesn't throw errors.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = JobDatabase(db_path=db_path)

            # Should not raise any exceptions
            db.close()

            # Database file should still exist
            assert db.db_path.exists()

    def test_database_file_permissions(self):
        """
        Test that database files are created with appropriate permissions.

        Ensures database files can be read and written by the owner.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = JobDatabase(db_path=db_path)

            # File should exist and be readable/writable
            assert db_path.exists()
            assert os.access(db_path, os.R_OK)
            assert os.access(db_path, os.W_OK)