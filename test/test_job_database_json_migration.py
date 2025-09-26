"""
Comprehensive tests for database migration to JSON schema.

This test suite validates the transition from column-based to JSON-based storage,
including fresh database creation, schema migration, and data preservation during
the transition process.
"""

import sqlite3
import json
import tempfile
import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, '.')
from lib.job_database import JobDatabase, JobRecord, ScrapeSession


class TestFreshDatabaseCreation:
    """Test creating fresh databases with JSON schema from scratch."""

    def test_fresh_database_json_schema_creation(self):
        """
        Test creating a completely fresh database with JSON schema.

        Verifies that new databases are created with JSON-centric structure
        including proper tables, indexes, and generated columns.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "fresh_json.db"

            # Ensure database doesn't exist
            assert not db_path.exists()

            # Create fresh database
            db = JobDatabase(db_path=db_path)

            # Verify database was created
            assert db_path.exists()

            with sqlite3.connect(db_path) as conn:
                # Verify jobs table has JSON structure
                cursor = conn.execute("PRAGMA table_info(jobs)")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]

                # Must have json_data as primary storage
                assert 'json_data' in column_names

                # Must have generated columns for all job fields
                expected_generated = [
                    'job_id', 'title', 'company', 'work_type', 'location',
                    'salary', 'benefits', 'url', 'description', 'status', 'source'
                ]
                for col in expected_generated:
                    assert col in column_names, f"Generated column {col} missing"

                # Must have salary parsing columns
                assert 'salary_min_yearly' in column_names
                assert 'salary_max_yearly' in column_names

                # Must have timestamp columns (not generated)
                assert 'first_seen' in column_names
                assert 'last_seen' in column_names
                assert 'created_at' in column_names
                assert 'updated_at' in column_names

    def test_fresh_database_index_creation(self):
        """
        Test that fresh databases create only necessary indexes.

        Verifies that only job_id and location indexes are created,
        following the simplified indexing strategy.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "fresh_indexes.db"
            db = JobDatabase(db_path=db_path)

            with sqlite3.connect(db_path) as conn:
                # Get all custom indexes (exclude SQLite auto-indexes)
                indexes = conn.execute("""
                    SELECT name, tbl_name, sql FROM sqlite_master
                    WHERE type='index' AND name LIKE 'idx_%'
                """).fetchall()

                index_info = {idx[0]: {'table': idx[1], 'sql': idx[2]} for idx in indexes}

                # Should have exactly these indexes
                expected_indexes = {
                    'idx_jobs_job_id': 'jobs',
                    'idx_jobs_location': 'jobs'
                }

                assert len(index_info) == len(expected_indexes)

                for idx_name, table_name in expected_indexes.items():
                    assert idx_name in index_info, f"Index {idx_name} not found"
                    assert index_info[idx_name]['table'] == table_name

                # Verify specific indexes were NOT created
                removed_indexes = [
                    'idx_jobs_company', 'idx_jobs_work_type',
                    'idx_jobs_status', 'idx_jobs_salary_range'
                ]

                for removed_idx in removed_indexes:
                    assert removed_idx not in index_info, f"Index {removed_idx} should not exist"

    def test_fresh_database_fts_setup(self):
        """
        Test that fresh databases create FTS tables compatible with JSON.

        Verifies that FTS5 virtual tables are created and properly
        configured to work with generated columns from JSON data.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "fresh_fts.db"
            db = JobDatabase(db_path=db_path)

            with sqlite3.connect(db_path) as conn:
                # Verify FTS table exists
                fts_tables = conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name LIKE '%_fts'
                """).fetchall()

                assert len(fts_tables) > 0
                fts_table_name = fts_tables[0][0]

                # Test FTS integration with generated columns
                # Insert a job via JSON
                test_json = json.dumps({
                    "job_id": "fts_test_001",
                    "title": "Python Developer",
                    "company": "TestCorp",
                    "description": "Build amazing Python applications"
                })

                conn.execute("""
                    INSERT INTO jobs (json_data, first_seen, last_seen, created_at, updated_at)
                    VALUES (?, datetime('now'), datetime('now'), datetime('now'), datetime('now'))
                """, (test_json,))

                # Verify FTS can find the job
                fts_results = conn.execute(f"""
                    SELECT job_id FROM {fts_table_name} WHERE {fts_table_name} MATCH 'Python'
                """).fetchall()

                assert len(fts_results) == 1
                assert fts_results[0][0] == "fts_test_001"

    def test_fresh_database_triggers_setup(self):
        """
        Test that fresh databases create triggers for JSON data synchronization.

        Verifies that triggers are created to maintain FTS and other
        auxiliary data structures when JSON data changes.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "fresh_triggers.db"
            db = JobDatabase(db_path=db_path)

            with sqlite3.connect(db_path) as conn:
                # Get all triggers
                triggers = conn.execute("""
                    SELECT name, tbl_name FROM sqlite_master WHERE type='trigger'
                """).fetchall()

                trigger_info = {trig[0]: trig[1] for trig in triggers}

                # Should have FTS synchronization triggers
                expected_triggers = [
                    'jobs_fts_insert', 'jobs_fts_delete', 'jobs_fts_update',
                    'jobs_update_timestamp'
                ]

                for trigger_name in expected_triggers:
                    assert trigger_name in trigger_info, f"Trigger {trigger_name} missing"
                    assert trigger_info[trigger_name] == 'jobs'

    def test_fresh_database_schema_version(self):
        """
        Test that fresh databases are marked with correct schema version.

        Verifies that new databases include schema version metadata
        to track future migrations if needed.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "fresh_version.db"
            db = JobDatabase(db_path=db_path)

            with sqlite3.connect(db_path) as conn:
                # Check if schema version tracking exists
                # This could be implemented as a separate table or pragma
                try:
                    version = conn.execute("PRAGMA user_version").fetchone()[0]
                    # Expect a specific version number for JSON schema
                    assert version > 0, "Schema version should be set for JSON schema"
                except sqlite3.OperationalError:
                    # Alternative: check for schema_version table
                    try:
                        version_result = conn.execute("""
                            SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1
                        """).fetchone()
                        assert version_result is not None
                    except sqlite3.OperationalError:
                        pytest.skip("Schema versioning not yet implemented")


class TestDatabaseMigrationPreparation:
    """Test preparation for migrating existing databases to JSON schema."""

    def test_detect_existing_schema_structure(self):
        """
        Test detection of existing column-based schema.

        Verifies that migration logic can identify existing databases
        and determine if they need to be migrated to JSON structure.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "existing_schema.db"

            # Create database with old schema structure
            with sqlite3.connect(db_path) as conn:
                # Create old-style schema (separate columns)
                conn.execute("""
                    CREATE TABLE jobs (
                        job_id TEXT PRIMARY KEY,
                        title TEXT,
                        company TEXT,
                        work_type TEXT,
                        location TEXT,
                        salary TEXT,
                        benefits TEXT,
                        url TEXT,
                        description TEXT,
                        status TEXT DEFAULT 'active',
                        source TEXT DEFAULT 'linkedin',
                        salary_min_yearly INTEGER,
                        salary_max_yearly INTEGER,
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Add some test data
                conn.execute("""
                    INSERT INTO jobs (job_id, title, company, salary)
                    VALUES ('old_schema_001', 'Test Job', 'TestCorp', '$100K/yr')
                """)

            # Test schema detection
            db = JobDatabase(db_path=db_path)

            # This method should be implemented to detect schema type
            schema_type = db.detect_schema_type()
            assert schema_type == "column_based", "Should detect old column-based schema"

            # Verify data is still accessible
            job = db.get_job('old_schema_001')
            assert job is not None
            assert job['title'] == 'Test Job'

    def test_backup_before_migration(self):
        """
        Test that database backup is created before migration.

        Verifies that migration process creates backup copy
        of existing database before making changes.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            original_path = Path(temp_dir) / "original.db"
            backup_path = Path(temp_dir) / "original.db.backup"

            # Create original database
            with sqlite3.connect(original_path) as conn:
                conn.execute("CREATE TABLE test (id INTEGER, data TEXT)")
                conn.execute("INSERT INTO test VALUES (1, 'test data')")

            db = JobDatabase(db_path=original_path)

            # This method should create backup before migration
            backup_created = db.create_migration_backup()

            assert backup_created is True
            assert backup_path.exists()

            # Verify backup contains original data
            with sqlite3.connect(backup_path) as conn:
                result = conn.execute("SELECT data FROM test WHERE id = 1").fetchone()
                assert result[0] == "test data"

    def test_migration_safety_checks(self):
        """
        Test safety checks before migration execution.

        Verifies that migration process validates database state
        and ensures safe migration conditions.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "safety_check.db"

            # Create database with potential issues
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE jobs (
                        job_id TEXT PRIMARY KEY,
                        title TEXT,
                        -- Missing some expected columns
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

            db = JobDatabase(db_path=db_path)

            # This method should perform pre-migration validation
            safety_check = db.validate_migration_safety()

            # Should identify issues with schema
            assert safety_check['safe'] is False
            assert 'missing_columns' in safety_check['issues']
            assert len(safety_check['issues']['missing_columns']) > 0


class TestDataPreservationDuringMigration:
    """Test that existing data is preserved during migration to JSON."""

    def test_migrate_existing_job_data_to_json(self):
        """
        Test migration of existing job records to JSON format.

        Verifies that all existing job data is correctly converted
        to JSON storage while preserving all field values.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "migrate_data.db"

            # Create database with old schema and data
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE jobs (
                        job_id TEXT PRIMARY KEY,
                        title TEXT,
                        company TEXT,
                        work_type TEXT,
                        location TEXT,
                        salary TEXT,
                        benefits TEXT,
                        url TEXT,
                        description TEXT,
                        status TEXT DEFAULT 'active',
                        source TEXT DEFAULT 'linkedin',
                        salary_min_yearly INTEGER,
                        salary_max_yearly INTEGER,
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Add test data with various field combinations
                test_data = [
                    {
                        'job_id': 'migrate_001',
                        'title': 'Senior Developer',
                        'company': 'TechCorp',
                        'work_type': 'Remote',
                        'location': 'San Francisco, CA',
                        'salary': '$120K/yr - $150K/yr',
                        'benefits': 'Health, Dental, 401k',
                        'url': 'https://techcorp.com/jobs/migrate_001',
                        'description': 'Build scalable applications',
                        'status': 'active',
                        'source': 'linkedin',
                        'salary_min_yearly': 120000,
                        'salary_max_yearly': 150000
                    },
                    {
                        'job_id': 'migrate_002',
                        'title': 'Data Analyst',
                        'company': 'DataCorp',
                        # Some fields missing/NULL
                        'work_type': None,
                        'location': 'Remote',
                        'salary': 'Competitive',
                        'benefits': None,
                        'url': None,
                        'description': 'Analyze business data',
                        'status': 'applied',
                        'source': 'indeed',
                        'salary_min_yearly': None,
                        'salary_max_yearly': None
                    }
                ]

                for job_data in test_data:
                    columns = ', '.join(job_data.keys())
                    placeholders = ', '.join(['?' for _ in job_data])
                    conn.execute(f"INSERT INTO jobs ({columns}) VALUES ({placeholders})",
                               list(job_data.values()))

            # Perform migration
            db = JobDatabase(db_path=db_path)
            migration_result = db.migrate_to_json_schema()

            assert migration_result['success'] is True
            assert migration_result['jobs_migrated'] == 2

            # Verify migrated data via API
            job1 = db.get_job('migrate_001')
            assert job1 is not None
            assert job1['title'] == 'Senior Developer'
            assert job1['company'] == 'TechCorp'
            assert job1['work_type'] == 'Remote'
            assert job1['location'] == 'San Francisco, CA'
            assert job1['salary'] == '$120K/yr - $150K/yr'
            assert job1['benefits'] == 'Health, Dental, 401k'
            assert job1['url'] == 'https://techcorp.com/jobs/migrate_001'
            assert job1['description'] == 'Build scalable applications'
            assert job1['status'] == 'active'
            assert job1['source'] == 'linkedin'
            assert job1['salary_min_yearly'] == 120000
            assert job1['salary_max_yearly'] == 150000

            job2 = db.get_job('migrate_002')
            assert job2 is not None
            assert job2['title'] == 'Data Analyst'
            assert job2['company'] == 'DataCorp'
            assert job2['work_type'] is None
            assert job2['location'] == 'Remote'
            assert job2['salary'] == 'Competitive'
            assert job2['benefits'] is None
            assert job2['url'] is None
            assert job2['description'] == 'Analyze business data'
            assert job2['status'] == 'applied'
            assert job2['source'] == 'indeed'
            assert job2['salary_min_yearly'] is None
            assert job2['salary_max_yearly'] is None

    def test_migrate_scrape_sessions_preservation(self):
        """
        Test that scrape sessions are preserved during migration.

        Verifies that session data and job-session relationships
        remain intact after schema migration.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "migrate_sessions.db"

            # Create old schema with sessions
            with sqlite3.connect(db_path) as conn:
                # Create tables matching old schema
                conn.execute("""
                    CREATE TABLE jobs (
                        job_id TEXT PRIMARY KEY,
                        title TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.execute("""
                    CREATE TABLE scrape_sessions (
                        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP NOT NULL,
                        total_jobs_found INTEGER NOT NULL,
                        new_jobs_added INTEGER DEFAULT 0,
                        source TEXT DEFAULT 'linkedin',
                        search_criteria TEXT,
                        notes TEXT
                    )
                """)

                conn.execute("""
                    CREATE TABLE job_session_mapping (
                        job_id TEXT,
                        session_id INTEGER,
                        position_in_results INTEGER,
                        FOREIGN KEY (job_id) REFERENCES jobs (job_id),
                        FOREIGN KEY (session_id) REFERENCES scrape_sessions (session_id)
                    )
                """)

                # Add test data
                conn.execute("INSERT INTO jobs (job_id, title) VALUES ('session_job_1', 'Test Job')")
                conn.execute("""
                    INSERT INTO scrape_sessions (timestamp, total_jobs_found, new_jobs_added, notes)
                    VALUES (datetime('now'), 5, 2, 'Test session')
                """)
                session_id = conn.lastrowid
                conn.execute("""
                    INSERT INTO job_session_mapping (job_id, session_id, position_in_results)
                    VALUES ('session_job_1', ?, 1)
                """, (session_id,))

            # Perform migration
            db = JobDatabase(db_path=db_path)
            migration_result = db.migrate_to_json_schema()

            assert migration_result['success'] is True

            # Verify session data preserved
            with sqlite3.connect(db_path) as conn:
                session = conn.execute("""
                    SELECT timestamp, total_jobs_found, new_jobs_added, notes
                    FROM scrape_sessions WHERE session_id = ?
                """, (session_id,)).fetchone()

                assert session is not None
                assert session[1] == 5  # total_jobs_found
                assert session[2] == 2  # new_jobs_added
                assert session[3] == 'Test session'  # notes

                # Verify mapping preserved
                mapping = conn.execute("""
                    SELECT job_id, position_in_results
                    FROM job_session_mapping WHERE session_id = ?
                """, (session_id,)).fetchone()

                assert mapping is not None
                assert mapping[0] == 'session_job_1'
                assert mapping[1] == 1

    def test_migration_rollback_capability(self):
        """
        Test ability to rollback failed migrations.

        Verifies that if migration fails partway through,
        the database can be restored to original state.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "rollback_test.db"
            backup_path = Path(temp_dir) / "rollback_test.db.backup"

            # Create original database
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE jobs (job_id TEXT PRIMARY KEY, title TEXT)")
                conn.execute("INSERT INTO jobs VALUES ('rollback_001', 'Original Job')")

            db = JobDatabase(db_path=db_path)

            # Simulate migration failure
            with patch.object(db, '_perform_migration') as mock_migration:
                mock_migration.side_effect = Exception("Migration failed!")

                try:
                    db.migrate_to_json_schema()
                except Exception:
                    pass  # Expected to fail

                # Should trigger rollback
                rollback_result = db.rollback_migration()

                assert rollback_result['success'] is True

                # Verify original data restored
                with sqlite3.connect(db_path) as conn:
                    result = conn.execute("SELECT title FROM jobs WHERE job_id = 'rollback_001'").fetchone()
                    assert result[0] == "Original Job"