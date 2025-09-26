"""
Tests for CLI database commands: search-jobs and db-stats.

These tests cover the command-line interface functionality for searching jobs
from the database and displaying database statistics. Following TDD principles
to ensure robust CLI behavior and proper error handling.
"""

import json
import sys
from io import StringIO
from unittest.mock import patch, MagicMock, call

import pytest

# Import the main function that needs testing
sys.path.insert(0, '.')
from script.linkedin_auth import main


class TestSearchJobsCLI:
    """Test the search-jobs CLI command functionality."""

    def test_search_jobs_basic_query(self):
        """
        Test basic job search with query term only.

        Verifies that the search-jobs command properly calls the database
        and displays results in the expected format.
        """
        # Mock database and search results
        mock_jobs = [
            {
                'job_id': 'cli_test_1',
                'title': 'Python Developer',
                'company': 'TechCorp',
                'work_type': 'Remote',
                'location': 'San Francisco, CA',
                'salary': '$100K/yr - $120K/yr',
                'salary_min_yearly': 100000,
                'salary_max_yearly': 120000,
                'status': 'active',
                'first_seen': '2024-01-15 10:30:00',
                'url': 'https://linkedin.com/jobs/view/cli_test_1'
            }
        ]

        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.JobDatabase') as mock_db_class:
                # Mock command arguments
                mock_docopt.return_value = {
                    'search-jobs': True,
                    '<query>': 'python developer',
                    '--company': None,
                    '--location': None,
                    '--work-type': None,
                    '--min-salary': None,
                    '--max-salary': None,
                    '--limit': '100',
                    'login': False,
                    'db-stats': False,
                    'decrypt-cookies': False
                }

                # Mock database instance and search method
                mock_db_instance = MagicMock()
                mock_db_class.return_value = mock_db_instance
                mock_db_instance.search_jobs.return_value = mock_jobs

                # Capture stdout
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    main()

                # Verify database was called correctly
                mock_db_instance.search_jobs.assert_called_once_with(
                    query='python developer',
                    company=None,
                    location=None,
                    work_type=None,
                    min_salary=None,
                    max_salary=None,
                    limit=100
                )

                # Verify output format
                output = mock_stdout.getvalue()
                assert "=== Found 1 matching jobs ===" in output
                assert "Job ID: cli_test_1" in output
                assert "Title: Python Developer" in output
                assert "Company: TechCorp" in output
                assert "Work Type: Remote" in output
                assert "Location: San Francisco, CA" in output
                assert "Salary: $100K/yr - $120K/yr" in output
                assert "Parsed Salary: $100,000 - $120,000" in output
                assert "Status: active" in output

    def test_search_jobs_all_filters(self):
        """
        Test job search with all filter parameters.

        Verifies that all CLI filter options are properly parsed and
        passed to the database search method.
        """
        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.JobDatabase') as mock_db_class:
                # Mock command arguments with all filters
                mock_docopt.return_value = {
                    'search-jobs': True,
                    '<query>': 'senior engineer',
                    '--company': 'TechCorp',
                    '--location': 'remote',
                    '--work-type': 'Remote',
                    '--min-salary': '120000',
                    '--max-salary': '180000',
                    '--limit': '50',
                    'login': False,
                    'db-stats': False,
                    'decrypt-cookies': False
                }

                mock_db_instance = MagicMock()
                mock_db_class.return_value = mock_db_instance
                mock_db_instance.search_jobs.return_value = []

                with patch('sys.stdout', new_callable=StringIO):
                    main()

                # Verify all parameters were passed correctly
                mock_db_instance.search_jobs.assert_called_once_with(
                    query='senior engineer',
                    company='TechCorp',
                    location='remote',
                    work_type='Remote',
                    min_salary=120000,
                    max_salary=180000,
                    limit=50
                )

    def test_search_jobs_salary_parsing_errors(self):
        """
        Test error handling for invalid salary values.

        Verifies that non-numeric salary values are properly handled
        with appropriate error messages.
        """
        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.sys.exit') as mock_exit:
                # Test invalid min salary
                mock_docopt.return_value = {
                    'search-jobs': True,
                    '<query>': None,
                    '--company': None,
                    '--location': None,
                    '--work-type': None,
                    '--min-salary': 'invalid',
                    '--max-salary': None,
                    '--limit': '100',
                    'login': False,
                    'db-stats': False,
                    'decrypt-cookies': False
                }

                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    main()

                # Should show error and exit
                output = mock_stdout.getvalue()
                assert "Error: --min-salary must be an integer" in output
                mock_exit.assert_called_once_with(1)

        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.sys.exit') as mock_exit:
                # Test invalid max salary
                mock_docopt.return_value = {
                    'search-jobs': True,
                    '<query>': None,
                    '--company': None,
                    '--location': None,
                    '--work-type': None,
                    '--min-salary': None,
                    '--max-salary': 'also_invalid',
                    '--limit': '100',
                    'login': False,
                    'db-stats': False,
                    'decrypt-cookies': False
                }

                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    main()

                # Should show error and exit
                output = mock_stdout.getvalue()
                assert "Error: --max-salary must be an integer" in output
                mock_exit.assert_called_once_with(1)

    def test_search_jobs_no_results(self):
        """
        Test search results display when no jobs are found.

        Verifies that empty search results are handled gracefully
        with appropriate messaging.
        """
        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.JobDatabase') as mock_db_class:
                mock_docopt.return_value = {
                    'search-jobs': True,
                    '<query>': 'nonexistent technology',
                    '--company': None,
                    '--location': None,
                    '--work-type': None,
                    '--min-salary': None,
                    '--max-salary': None,
                    '--limit': '100',
                    'login': False,
                    'db-stats': False,
                    'decrypt-cookies': False
                }

                mock_db_instance = MagicMock()
                mock_db_class.return_value = mock_db_instance
                mock_db_instance.search_jobs.return_value = []

                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    main()

                output = mock_stdout.getvalue()
                assert "=== Found 0 matching jobs ===" in output

    def test_search_jobs_database_error(self):
        """
        Test error handling when database operations fail.

        Verifies that database connection errors and search failures
        are properly caught and reported.
        """
        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.JobDatabase') as mock_db_class:
                with patch('script.linkedin_auth.sys.exit') as mock_exit:
                    mock_docopt.return_value = {
                        'search-jobs': True,
                        '<query>': 'test',
                        '--company': None,
                        '--location': None,
                        '--work-type': None,
                        '--min-salary': None,
                        '--max-salary': None,
                        '--limit': '100',
                        'login': False,
                        'db-stats': False,
                        'decrypt-cookies': False
                    }

                    # Mock database creation failure
                    mock_db_class.side_effect = Exception("Database connection failed")

                    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                        main()

                    output = mock_stdout.getvalue()
                    assert "Error searching jobs: Database connection failed" in output
                    mock_exit.assert_called_once_with(1)

    def test_search_jobs_multiple_results_formatting(self):
        """
        Test formatting of multiple search results.

        Verifies that multiple job results are properly formatted
        and separated in the output.
        """
        mock_jobs = [
            {
                'job_id': 'multi_1',
                'title': 'Senior Python Developer',
                'company': 'TechCorp',
                'work_type': 'Remote',
                'location': 'Remote',
                'salary': '$130K/yr - $150K/yr',
                'salary_min_yearly': 130000,
                'salary_max_yearly': 150000,
                'status': 'active',
                'first_seen': '2024-01-15 10:30:00',
                'url': 'https://linkedin.com/jobs/view/multi_1'
            },
            {
                'job_id': 'multi_2',
                'title': 'Data Scientist',
                'company': 'DataCorp',
                'work_type': None,  # Test None work_type
                'location': 'New York, NY',
                'salary': None,  # Test None salary
                'salary_min_yearly': None,
                'salary_max_yearly': None,
                'status': 'active',
                'first_seen': '2024-01-15 11:00:00',
                'url': 'https://linkedin.com/jobs/view/multi_2'
            }
        ]

        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.JobDatabase') as mock_db_class:
                mock_docopt.return_value = {
                    'search-jobs': True,
                    '<query>': 'python OR data',
                    '--company': None,
                    '--location': None,
                    '--work-type': None,
                    '--min-salary': None,
                    '--max-salary': None,
                    '--limit': '100',
                    'login': False,
                    'db-stats': False,
                    'decrypt-cookies': False
                }

                mock_db_instance = MagicMock()
                mock_db_class.return_value = mock_db_instance
                mock_db_instance.search_jobs.return_value = mock_jobs

                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    main()

                output = mock_stdout.getvalue()

                # Should show correct count
                assert "=== Found 2 matching jobs ===" in output

                # Should show both jobs
                assert "Job ID: multi_1" in output
                assert "Job ID: multi_2" in output
                assert "Title: Senior Python Developer" in output
                assert "Title: Data Scientist" in output

                # Should handle optional fields correctly
                assert "Work Type: Remote" in output  # First job has work_type
                # Second job should not show work_type line since it's None

                assert "$130K/yr - $150K/yr" in output  # First job has salary
                # Second job should not show salary lines since it's None


class TestDbStatsCLI:
    """Test the db-stats CLI command functionality."""

    def test_db_stats_complete_display(self):
        """
        Test complete database statistics display.

        Verifies that all database statistics are properly formatted
        and displayed in the expected structure.
        """
        mock_stats = {
            'total_jobs': 150,
            'active_jobs': 120,
            'jobs_seen_last_7_days': 25,
            'total_sessions': 10,
            'jobs_by_status': {
                'active': 120,
                'removed': 20,
                'applied': 8,
                'rejected': 2
            },
            'work_types': {
                'Remote': 45,
                'Hybrid': 30,
                'On-site': 25,
                'Unknown': 20
            },
            'top_companies': {
                'TechCorp': 15,
                'DataCorp': 12,
                'WebCorp': 10,
                'CloudCorp': 8,
                'StartupCorp': 5
            }
        }

        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.JobDatabase') as mock_db_class:
                mock_docopt.return_value = {
                    'search-jobs': False,
                    'db-stats': True,
                    'login': False,
                    'decrypt-cookies': False
                }

                mock_db_instance = MagicMock()
                mock_db_class.return_value = mock_db_instance
                mock_db_instance.get_stats.return_value = mock_stats

                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    main()

                output = mock_stdout.getvalue()

                # Verify main statistics section
                assert "=== Database Statistics ===" in output
                assert "Total Jobs: 150" in output
                assert "Active Jobs: 120" in output
                assert "Jobs Seen (Last 7 days): 25" in output
                assert "Total Scrape Sessions: 10" in output

                # Verify jobs by status section
                assert "Jobs by Status:" in output
                assert "  active: 120" in output
                assert "  removed: 20" in output
                assert "  applied: 8" in output
                assert "  rejected: 2" in output

                # Verify work types section
                assert "Work Types:" in output
                assert "  Remote: 45" in output
                assert "  Hybrid: 30" in output
                assert "  On-site: 25" in output
                assert "  Unknown: 20" in output

                # Verify top companies section
                assert "Top Companies:" in output
                assert "  TechCorp: 15" in output
                assert "  DataCorp: 12" in output
                assert "  WebCorp: 10" in output
                assert "  CloudCorp: 8" in output
                assert "  StartupCorp: 5" in output

    def test_db_stats_empty_database(self):
        """
        Test database statistics display with empty database.

        Verifies that empty statistics are handled gracefully
        without errors or malformed output.
        """
        mock_empty_stats = {
            'total_jobs': 0,
            'active_jobs': 0,
            'jobs_seen_last_7_days': 0,
            'total_sessions': 0,
            'jobs_by_status': {},
            'work_types': {},
            'top_companies': {}
        }

        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.JobDatabase') as mock_db_class:
                mock_docopt.return_value = {
                    'search-jobs': False,
                    'db-stats': True,
                    'login': False,
                    'decrypt-cookies': False
                }

                mock_db_instance = MagicMock()
                mock_db_class.return_value = mock_db_instance
                mock_db_instance.get_stats.return_value = mock_empty_stats

                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    main()

                output = mock_stdout.getvalue()

                # Should show zero counts
                assert "Total Jobs: 0" in output
                assert "Active Jobs: 0" in output
                assert "Jobs Seen (Last 7 days): 0" in output
                assert "Total Scrape Sessions: 0" in output

                # Should show section headers even when empty
                assert "Jobs by Status:" in output
                assert "Work Types:" in output
                assert "Top Companies:" in output

    def test_db_stats_database_error(self):
        """
        Test error handling when database statistics retrieval fails.

        Verifies that database errors are properly caught and reported
        with appropriate exit codes.
        """
        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.JobDatabase') as mock_db_class:
                with patch('script.linkedin_auth.sys.exit') as mock_exit:
                    mock_docopt.return_value = {
                        'search-jobs': False,
                        'db-stats': True,
                        'login': False,
                        'decrypt-cookies': False
                    }

                    # Mock database statistics failure
                    mock_db_instance = MagicMock()
                    mock_db_class.return_value = mock_db_instance
                    mock_db_instance.get_stats.side_effect = Exception("Database query failed")

                    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                        main()

                    output = mock_stdout.getvalue()
                    assert "Error getting database stats: Database query failed" in output
                    mock_exit.assert_called_once_with(1)

    def test_db_stats_database_creation_error(self):
        """
        Test error handling when database creation fails.

        Verifies that database initialization errors are handled properly.
        """
        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.JobDatabase') as mock_db_class:
                with patch('script.linkedin_auth.sys.exit') as mock_exit:
                    mock_docopt.return_value = {
                        'search-jobs': False,
                        'db-stats': True,
                        'login': False,
                        'decrypt-cookies': False
                    }

                    # Mock database creation failure
                    mock_db_class.side_effect = Exception("Cannot access database file")

                    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                        main()

                    output = mock_stdout.getvalue()
                    assert "Error getting database stats: Cannot access database file" in output
                    mock_exit.assert_called_once_with(1)

    def test_db_stats_partial_data(self):
        """
        Test database statistics display with partial/missing data.

        Verifies that missing or incomplete statistics sections
        are handled gracefully without errors.
        """
        mock_partial_stats = {
            'total_jobs': 50,
            'active_jobs': 45,
            'jobs_seen_last_7_days': 10,
            'total_sessions': 3,
            'jobs_by_status': {
                'active': 45,
                'removed': 5
            },
            'work_types': {
                'Remote': 25,
                'Unknown': 20
            },
            'top_companies': {
                'SingleCorp': 50  # All jobs from one company
            }
        }

        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.JobDatabase') as mock_db_class:
                mock_docopt.return_value = {
                    'search-jobs': False,
                    'db-stats': True,
                    'login': False,
                    'decrypt-cookies': False
                }

                mock_db_instance = MagicMock()
                mock_db_class.return_value = mock_db_instance
                mock_db_instance.get_stats.return_value = mock_partial_stats

                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    main()

                output = mock_stdout.getvalue()

                # Should display available data correctly
                assert "Total Jobs: 50" in output
                assert "Active Jobs: 45" in output

                # Should show only available status types
                assert "  active: 45" in output
                assert "  removed: 5" in output

                # Should show only available work types
                assert "  Remote: 25" in output
                assert "  Unknown: 20" in output

                # Should show single company
                assert "  SingleCorp: 50" in output


class TestCLIIntegration:
    """Test CLI integration scenarios and edge cases."""

    def test_docopt_version_handling(self):
        """
        Test that CLI version information is properly configured.

        Verifies that the docopt version parameter works correctly.
        """
        with patch('script.linkedin_auth.docopt') as mock_docopt:
            # Mock version request
            mock_docopt.return_value = {'--version': True}

            # The docopt version should be called with version parameter
            main()

            mock_docopt.assert_called_once_with(
                patch.ANY,  # The docstring
                version="LinkedIn Auth 1.0"
            )

    def test_multiple_command_conflict_handling(self):
        """
        Test CLI behavior when multiple commands are specified.

        Verifies that the CLI handles conflicting command arguments correctly
        by following the expected precedence order.
        """
        # This test verifies the actual command precedence in the CLI
        # The real CLI should handle precedence through docopt configuration

        with patch('script.linkedin_auth.docopt') as mock_docopt:
            with patch('script.linkedin_auth.LinkedInSession') as mock_session_class:
                # Mock scenario where multiple commands might be true
                # (This shouldn't happen with proper docopt usage, but tests edge cases)
                mock_docopt.return_value = {
                    'login': True,
                    'search-jobs': False,  # Should be handled first due to elif structure
                    'db-stats': False,
                    'decrypt-cookies': False,
                    # Login-specific arguments
                    '--force-fresh-login': False,
                    '--headless': False,
                    '--with-descriptions': False,
                    '--max-descriptions': '5',
                    '--no-database': False,
                    '<filename>': None
                }

                mock_session = MagicMock()
                mock_session_class.return_value = mock_session
                mock_session.login.return_value = True

                with patch('sys.stdout', new_callable=StringIO):
                    with patch.dict('os.environ', {'TESTING': '1'}):  # Skip input prompt
                        main()

                # Should execute login command (first in elif chain)
                mock_session.login.assert_called_once()

    def test_cli_help_documentation_completeness(self):
        """
        Test that CLI help documentation includes all required information.

        Verifies that the docstring includes all commands and options
        that are implemented in the CLI.
        """
        # Import the docstring from the script
        from script.linkedin_auth import __doc__ as cli_doc

        # Verify all commands are documented
        assert 'search-jobs' in cli_doc
        assert 'db-stats' in cli_doc
        assert 'login' in cli_doc
        assert 'decrypt-cookies' in cli_doc

        # Verify search-jobs options are documented
        assert '--company' in cli_doc
        assert '--location' in cli_doc
        assert '--work-type' in cli_doc
        assert '--min-salary' in cli_doc
        assert '--max-salary' in cli_doc
        assert '--limit' in cli_doc

        # Verify login options are documented
        assert '--force-fresh-login' in cli_doc
        assert '--headless' in cli_doc
        assert '--with-descriptions' in cli_doc
        assert '--max-descriptions' in cli_doc
        assert '--no-database' in cli_doc

        # Verify examples are provided
        assert 'Examples:' in cli_doc
        assert 'linkedin_auth.py search-jobs' in cli_doc
        assert 'linkedin_auth.py db-stats' in cli_doc