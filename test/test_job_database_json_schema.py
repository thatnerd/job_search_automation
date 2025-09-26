"""
Comprehensive tests for JSON-based database schema migration.

This test suite validates the transition from structured columns to JSON storage
with generated columns. Tests cover JSON field validation, generated column
extraction, salary parsing, and schema creation following TDD principles.
"""

import sqlite3
import json
import tempfile
import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, '.')
from lib.job_database import JobDatabase, JobRecord, ScrapeSession


class TestJSONSchemaCreation:
    """Test JSON-based schema creation and validation."""

    def test_fresh_database_json_schema(self):
        """
        Test creating fresh database with JSON-centric schema.

        Verifies that new databases use json_data field as primary storage
        with generated columns for all other fields.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "json_schema_test.db"
            db = JobDatabase(db_path=db_path)

            with sqlite3.connect(db_path) as conn:
                # Verify jobs table structure
                columns = conn.execute("PRAGMA table_info(jobs)").fetchall()
                column_info = {col[1]: {'type': col[2], 'notnull': col[3], 'pk': col[5]} for col in columns}

                # Verify json_data is the primary field
                assert 'json_data' in column_info
                assert column_info['json_data']['type'] == 'TEXT'
                assert column_info['json_data']['notnull'] == 1  # NOT NULL

                # Verify generated columns exist
                generated_columns = [
                    'job_id', 'title', 'company', 'work_type', 'location',
                    'salary', 'benefits', 'url', 'description', 'status', 'source'
                ]
                for col_name in generated_columns:
                    assert col_name in column_info, f"Generated column {col_name} should exist"

                # Verify salary parsing columns
                assert 'salary_min_yearly' in column_info
                assert 'salary_max_yearly' in column_info
                assert column_info['salary_min_yearly']['type'] == 'INTEGER'
                assert column_info['salary_max_yearly']['type'] == 'INTEGER'

                # Verify timestamp columns are still real columns
                assert 'first_seen' in column_info
                assert 'last_seen' in column_info
                assert 'created_at' in column_info
                assert 'updated_at' in column_info

    def test_json_schema_indexes(self):
        """
        Test that only job_id and location indexes are created.

        Verifies schema change removes unnecessary indexes and keeps only
        the essential ones for performance.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "index_test.db"
            db = JobDatabase(db_path=db_path)

            with sqlite3.connect(db_path) as conn:
                indexes = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name LIKE 'idx_%'
                """).fetchall()

                index_names = [row[0] for row in indexes]
                
                # Only these indexes should exist
                expected_indexes = ['idx_jobs_job_id', 'idx_jobs_location']
                
                for expected in expected_indexes:
                    assert expected in index_names, f"Expected index {expected} not found"

                # Verify removed indexes are gone
                removed_indexes = [
                    'idx_jobs_company', 'idx_jobs_work_type',
                    'idx_jobs_status', 'idx_jobs_salary_range'
                ]
                
                for removed in removed_indexes:
                    assert removed not in index_names, f"Index {removed} should have been removed"

    def test_generated_column_definitions(self):
        """
        Test generated column SQL definitions are correct.

        Verifies that generated columns properly extract JSON fields
        using SQLite JSON operators.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "generated_test.db"
            db = JobDatabase(db_path=db_path)

            with sqlite3.connect(db_path) as conn:
                # Test generated column extraction by inserting JSON data
                test_json = json.dumps({
                    "job_id": "test123",
                    "title": "Senior Python Developer", 
                    "company": "TechCorp Inc",
                    "work_type": "Remote",
                    "location": "San Francisco, CA",
                    "salary": "$120K/yr - $150K/yr",
                    "benefits": "Health, Dental, 401k",
                    "url": "https://example.com/job/test123",
                    "description": "Build amazing Python applications",
                    "status": "active",
                    "source": "linkedin"
                })

                conn.execute("""
                    INSERT INTO jobs (json_data, first_seen, last_seen, created_at, updated_at)
                    VALUES (?, datetime('now'), datetime('now'), datetime('now'), datetime('now'))
                """, (test_json,))

                # Verify generated columns extract correctly
                result = conn.execute("""
                    SELECT job_id, title, company, work_type, location, salary,
                           benefits, url, description, status, source
                    FROM jobs WHERE job_id = 'test123'
                """).fetchone()

                assert result[0] == "test123"  # job_id
                assert result[1] == "Senior Python Developer"  # title
                assert result[2] == "TechCorp Inc"  # company
                assert result[3] == "Remote"  # work_type
                assert result[4] == "San Francisco, CA"  # location
                assert result[5] == "$120K/yr - $150K/yr"  # salary
                assert result[6] == "Health, Dental, 401k"  # benefits
                assert result[7] == "https://example.com/job/test123"  # url
                assert result[8] == "Build amazing Python applications"  # description
                assert result[9] == "active"  # status
                assert result[10] == "linkedin"  # source


class TestJSONFieldValidation:
    """Test JSON field validation and error handling."""

    @pytest.fixture
    def db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "validation_test.db"
            yield JobDatabase(db_path=db_path)

    def test_valid_json_insertion(self, db):
        """
        Test inserting valid JSON data into json_data field.

        Verifies that well-formed JSON with all expected fields
        is accepted and stored correctly.
        """
        valid_json = {
            "job_id": "valid_001",
            "title": "Software Engineer",
            "company": "ValidCorp",
            "work_type": "Hybrid",
            "location": "Austin, TX", 
            "salary": "$90K/yr - $110K/yr",
            "benefits": "Health, Vision, 401k",
            "url": "https://validcorp.com/jobs/valid_001",
            "description": "Join our engineering team"
        }

        with sqlite3.connect(db.db_path) as conn:
            # Should not raise any exceptions
            conn.execute("""
                INSERT INTO jobs (json_data, first_seen, last_seen, created_at, updated_at)
                VALUES (?, datetime('now'), datetime('now'), datetime('now'), datetime('now'))
            """, (json.dumps(valid_json),))

            # Verify data was stored and extracted correctly
            result = conn.execute("""
                SELECT job_id, title, company FROM jobs WHERE job_id = 'valid_001'
            """).fetchone()

            assert result[0] == "valid_001"
            assert result[1] == "Software Engineer"
            assert result[2] == "ValidCorp"

    def test_minimal_json_insertion(self, db):
        """
        Test inserting minimal JSON with only required fields.

        Verifies that JSON with only job_id works correctly
        and missing fields are handled gracefully.
        """
        minimal_json = {"job_id": "minimal_001"}

        with sqlite3.connect(db.db_path) as conn:
            conn.execute("""
                INSERT INTO jobs (json_data, first_seen, last_seen, created_at, updated_at)
                VALUES (?, datetime('now'), datetime('now'), datetime('now'), datetime('now'))
            """, (json.dumps(minimal_json),))

            # Verify generated columns handle missing fields
            result = conn.execute("""
                SELECT job_id, title, company, work_type, location, salary
                FROM jobs WHERE job_id = 'minimal_001'
            """).fetchone()

            assert result[0] == "minimal_001"  # job_id exists
            assert result[1] is None  # title is NULL
            assert result[2] is None  # company is NULL
            assert result[3] is None  # work_type is NULL
            assert result[4] is None  # location is NULL
            assert result[5] is None  # salary is NULL

    def test_malformed_json_handling(self, db):
        """
        Test handling of malformed JSON data.

        Verifies that invalid JSON is rejected appropriately
        and doesn't corrupt the database.
        """
        with sqlite3.connect(db.db_path) as conn:
            # Malformed JSON should cause SQLite error
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("""
                    INSERT INTO jobs (json_data, first_seen, last_seen, created_at, updated_at)
                    VALUES (?, datetime('now'), datetime('now'), datetime('now'), datetime('now'))
                """, ("invalid json string",))

    def test_null_json_field_extraction(self, db):
        """
        Test generated column behavior with NULL/missing JSON fields.

        Verifies that missing or null JSON fields result in NULL
        generated column values rather than errors.
        """
        json_with_nulls = {
            "job_id": "null_test_001",
            "title": None,
            "company": "",  # Empty string
            # Missing fields: work_type, location, etc.
        }

        with sqlite3.connect(db.db_path) as conn:
            conn.execute("""
                INSERT INTO jobs (json_data, first_seen, last_seen, created_at, updated_at)
                VALUES (?, datetime('now'), datetime('now'), datetime('now'), datetime('now'))
            """, (json.dumps(json_with_nulls),))

            result = conn.execute("""
                SELECT job_id, title, company, work_type, location
                FROM jobs WHERE job_id = 'null_test_001'
            """).fetchone()

            assert result[0] == "null_test_001"  # job_id
            assert result[1] is None  # null title becomes NULL
            assert result[2] == ""  # empty string preserved 
            assert result[3] is None  # missing work_type becomes NULL
            assert result[4] is None  # missing location becomes NULL


class TestSalaryParsingGeneratedColumns:
    """Test salary parsing with generated INTEGER columns."""

    @pytest.fixture
    def db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "salary_test.db"
            yield JobDatabase(db_path=db_path)

    def test_salary_range_parsing(self, db):
        """
        Test parsing salary ranges into min/max INTEGER columns.

        Verifies that salary strings like "$100K/yr - $120K/yr" are parsed
        into separate salary_min_yearly and salary_max_yearly integers.
        """
        test_cases = [
            ("$100K/yr - $120K/yr", 100000, 120000),
            ("$80K/yr - $95K/yr", 80000, 95000),
            ("$150K/yr - $200K/yr", 150000, 200000),
            ("$90k/yr - $110k/yr", 90000, 110000),  # lowercase k
            ("$100K/YR - $120K/YR", 100000, 120000),  # uppercase YR
        ]

        with sqlite3.connect(db.db_path) as conn:
            for i, (salary_str, expected_min, expected_max) in enumerate(test_cases):
                job_data = {
                    "job_id": f"salary_range_{i}",
                    "title": "Test Job",
                    "salary": salary_str
                }

                conn.execute("""
                    INSERT INTO jobs (json_data, first_seen, last_seen, created_at, updated_at)
                    VALUES (?, datetime('now'), datetime('now'), datetime('now'), datetime('now'))
                """, (json.dumps(job_data),))

                result = conn.execute("""
                    SELECT salary_min_yearly, salary_max_yearly
                    FROM jobs WHERE job_id = ?
                """, (f"salary_range_{i}",)).fetchone()

                assert result[0] == expected_min, f"Min salary mismatch for {salary_str}"
                assert result[1] == expected_max, f"Max salary mismatch for {salary_str}"

    def test_single_salary_parsing(self, db):
        """
        Test parsing single salary values.

        Verifies that single salaries like "$100K/yr" set both
        min and max to the same value.
        """
        test_cases = [
            ("$100K/yr", 100000, 100000),
            ("$85K/yr", 85000, 85000),
            ("$150k/yr", 150000, 150000),  # lowercase
            ("$200K/YR", 200000, 200000),  # uppercase YR
        ]

        with sqlite3.connect(db.db_path) as conn:
            for i, (salary_str, expected_min, expected_max) in enumerate(test_cases):
                job_data = {
                    "job_id": f"salary_single_{i}",
                    "title": "Test Job", 
                    "salary": salary_str
                }

                conn.execute("""
                    INSERT INTO jobs (json_data, first_seen, last_seen, created_at, updated_at)
                    VALUES (?, datetime('now'), datetime('now'), datetime('now'), datetime('now'))
                """, (json.dumps(job_data),))

                result = conn.execute("""
                    SELECT salary_min_yearly, salary_max_yearly
                    FROM jobs WHERE job_id = ?
                """, (f"salary_single_{i}",)).fetchone()

                assert result[0] == expected_min
                assert result[1] == expected_max

    def test_unparseable_salary_handling(self, db):
        """
        Test handling of unparseable salary strings.

        Verifies that non-standard salary formats result in NULL
        values for min/max salary columns.
        """
        unparseable_cases = [
            "Competitive salary",
            "DOE",
            "$100/hour",
            "100K",  # Missing $ and /yr
            "$100K",  # Missing /yr
            "Salary commensurate with experience",
            "",  # Empty string
            "$XYZ/yr",  # Invalid number
        ]

        with sqlite3.connect(db.db_path) as conn:
            for i, salary_str in enumerate(unparseable_cases):
                job_data = {
                    "job_id": f"salary_unparseable_{i}",
                    "title": "Test Job",
                    "salary": salary_str
                }

                conn.execute("""
                    INSERT INTO jobs (json_data, first_seen, last_seen, created_at, updated_at)
                    VALUES (?, datetime('now'), datetime('now'), datetime('now'), datetime('now'))
                """, (json.dumps(job_data),))

                result = conn.execute("""
                    SELECT salary_min_yearly, salary_max_yearly
                    FROM jobs WHERE job_id = ?
                """, (f"salary_unparseable_{i}",)).fetchone()

                assert result[0] is None, f"Min salary should be NULL for '{salary_str}'"
                assert result[1] is None, f"Max salary should be NULL for '{salary_str}'"

    def test_missing_salary_field(self, db):
        """
        Test salary parsing when salary field is missing from JSON.

        Verifies that missing salary field results in NULL min/max values.
        """
        job_data = {
            "job_id": "no_salary_001",
            "title": "Test Job",
            "company": "TestCorp"
            # No salary field
        }

        with sqlite3.connect(db.db_path) as conn:
            conn.execute("""
                INSERT INTO jobs (json_data, first_seen, last_seen, created_at, updated_at)
                VALUES (?, datetime('now'), datetime('now'), datetime('now'), datetime('now'))
            """, (json.dumps(job_data),))

            result = conn.execute("""
                SELECT salary, salary_min_yearly, salary_max_yearly
                FROM jobs WHERE job_id = 'no_salary_001'
            """).fetchone()

            assert result[0] is None  # salary field is NULL
            assert result[1] is None  # salary_min_yearly is NULL
            assert result[2] is None  # salary_max_yearly is NULL


class TestJobRecordJSONConversion:
    """Test JobRecord dataclass to JSON conversion and validation."""

    def test_job_record_to_json_full(self):
        """
        Test converting complete JobRecord to JSON format.

        Verifies that all JobRecord fields are properly serialized
        to JSON format expected by the database schema.
        """
        job = JobRecord(
            job_id="json_conv_001",
            title="Senior Python Developer",
            company="TechCorp Inc",
            work_type="Remote",
            location="San Francisco, CA",
            salary="$120K/yr - $150K/yr",
            benefits="Health, Dental, Vision, 401k",
            url="https://techcorp.com/jobs/json_conv_001",
            description="Build scalable Python applications using Django and FastAPI",
            status="active",
            source="linkedin"
        )

        # This method would be implemented in the JobRecord class or JobDatabase
        expected_json = {
            "job_id": "json_conv_001",
            "title": "Senior Python Developer",
            "company": "TechCorp Inc",
            "work_type": "Remote",
            "location": "San Francisco, CA",
            "salary": "$120K/yr - $150K/yr",
            "benefits": "Health, Dental, Vision, 401k",
            "url": "https://techcorp.com/jobs/json_conv_001",
            "description": "Build scalable Python applications using Django and FastAPI",
            "status": "active",
            "source": "linkedin"
        }

        # Test the conversion method (needs to be implemented)
        actual_json = job.to_json_dict()  # This method needs to be added to JobRecord
        assert actual_json == expected_json

    def test_job_record_to_json_minimal(self):
        """
        Test converting minimal JobRecord to JSON.

        Verifies that JobRecord with only required fields converts correctly
        and optional fields are handled appropriately.
        """
        minimal_job = JobRecord(job_id="minimal_json_001")

        expected_json = {
            "job_id": "minimal_json_001",
            "title": None,
            "company": None,
            "work_type": None,
            "location": None,
            "salary": None,
            "benefits": None,
            "url": None,
            "description": None,
            "status": "active",  # Default value
            "source": "linkedin"  # Default value
        }

        actual_json = minimal_job.to_json_dict()
        assert actual_json == expected_json

    def test_job_record_to_json_with_defaults(self):
        """
        Test JobRecord conversion preserves default values.

        Verifies that default status and source values are included
        in JSON representation.
        """
        job_with_defaults = JobRecord(
            job_id="defaults_001",
            title="Data Scientist",
            company="DataCorp"
            # status and source will use defaults
        )

        json_data = job_with_defaults.to_json_dict()

        assert json_data["status"] == "active"
        assert json_data["source"] == "linkedin"
        assert json_data["job_id"] == "defaults_001"
        assert json_data["title"] == "Data Scientist"
        assert json_data["company"] == "DataCorp"

    def test_job_record_from_json_dict(self):
        """
        Test creating JobRecord from JSON dictionary.

        Verifies bidirectional conversion between JobRecord and JSON
        for data retrieval from database.
        """
        json_data = {
            "job_id": "from_json_001",
            "title": "Backend Engineer",
            "company": "WebCorp",
            "work_type": "Hybrid",
            "location": "Austin, TX",
            "salary": "$95K/yr - $115K/yr",
            "benefits": "Health, 401k",
            "url": "https://webcorp.com/careers/from_json_001",
            "description": "Build web services with Python and PostgreSQL",
            "status": "active",
            "source": "indeed"
        }

        # This class method would be implemented in JobRecord
        job = JobRecord.from_json_dict(json_data)

        assert job.job_id == "from_json_001"
        assert job.title == "Backend Engineer"
        assert job.company == "WebCorp"
        assert job.work_type == "Hybrid"
        assert job.location == "Austin, TX"
        assert job.salary == "$95K/yr - $115K/yr"
        assert job.benefits == "Health, 401k"
        assert job.url == "https://webcorp.com/careers/from_json_001"
        assert job.description == "Build web services with Python and PostgreSQL"
        assert job.status == "active"
        assert job.source == "indeed"

    def test_job_record_from_json_missing_fields(self):
        """
        Test creating JobRecord from incomplete JSON data.

        Verifies that missing fields are handled gracefully
        and use appropriate default values.
        """
        incomplete_json = {
            "job_id": "incomplete_001",
            "title": "DevOps Engineer",
            # Missing many fields
            "status": "applied"
        }

        job = JobRecord.from_json_dict(incomplete_json)

        assert job.job_id == "incomplete_001"
        assert job.title == "DevOps Engineer"
        assert job.company is None  # Missing field becomes None
        assert job.work_type is None
        assert job.location is None
        assert job.salary is None
        assert job.benefits is None
        assert job.url is None
        assert job.description is None
        assert job.status == "applied"  # Explicit value
        assert job.source == "linkedin"  # Default value when missing

    def test_json_roundtrip_conversion(self):
        """
        Test round-trip conversion: JobRecord -> JSON -> JobRecord.

        Verifies that converting to JSON and back preserves all data
        without loss or corruption.
        """
        original_job = JobRecord(
            job_id="roundtrip_001",
            title="Full Stack Developer",
            company="StartupCorp",
            work_type="On-site",
            location="New York, NY",
            salary="$110K/yr",
            benefits="Health, Dental, Stock Options",
            url="https://startupcorp.com/jobs/roundtrip_001",
            description="Work on our cutting-edge web platform",
            status="applied",
            source="company_website"
        )

        # Convert to JSON and back
        json_data = original_job.to_json_dict()
        reconstructed_job = JobRecord.from_json_dict(json_data)

        # Verify all fields match
        assert reconstructed_job.job_id == original_job.job_id
        assert reconstructed_job.title == original_job.title
        assert reconstructed_job.company == original_job.company
        assert reconstructed_job.work_type == original_job.work_type
        assert reconstructed_job.location == original_job.location
        assert reconstructed_job.salary == original_job.salary
        assert reconstructed_job.benefits == original_job.benefits
        assert reconstructed_job.url == original_job.url
        assert reconstructed_job.description == original_job.description
        assert reconstructed_job.status == original_job.status
        assert reconstructed_job.source == original_job.source
