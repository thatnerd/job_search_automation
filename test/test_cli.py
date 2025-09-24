"""
Unit and integration tests for the LinkedIn authentication CLI script.

These tests cover command-line argument parsing, main function execution,
and integration with the LinkedInSession class.
"""

import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

# Add the project root to the path for imports
sys.path.insert(0, '.')
from script.linkedin_auth import main
import script.linkedin_auth as cli_module


class TestLinkedInAuthCLI:
    """Test LinkedIn authentication CLI script functionality."""
    
    def test_main_login_success(self, capsys):
        """
        Test successful CLI login execution.
        
        This test verifies that the main function correctly handles a successful
        login command and displays appropriate success messages.
        """
        # Mock command line arguments for login
        test_args = ['linkedin_auth.py', 'login']
        
        with patch('sys.argv', test_args):
            with patch('script.linkedin_auth.LinkedInSession') as mock_session_class:
                # Mock successful login
                mock_session = MagicMock()
                mock_session.login.return_value = True
                mock_session_class.return_value = mock_session
                
                main()
                
                # Verify session was created with correct parameters
                mock_session_class.assert_called_once_with(headless=False)
                
                # Verify login was called with correct parameters
                mock_session.login.assert_called_once_with(force_fresh=False)
                
                # Verify session was closed
                mock_session.close_session.assert_called_once()
                
                # Check success message
                captured = capsys.readouterr()
                assert "✓ LinkedIn authentication completed successfully!" in captured.out
                assert "Session cookies have been saved" in captured.out
    
    def test_main_login_failure(self, capsys):
        """
        Test CLI login failure handling.
        
        This test verifies that login failures are properly handled with
        appropriate error messages and exit codes.
        """
        test_args = ['linkedin_auth.py', 'login']
        
        with patch('sys.argv', test_args):
            with patch('script.linkedin_auth.LinkedInSession') as mock_session_class:
                with patch('sys.exit') as mock_exit:
                    # Mock failed login
                    mock_session = MagicMock()
                    mock_session.login.return_value = False
                    mock_session_class.return_value = mock_session
                    
                    main()
                    
                    # Verify login was attempted
                    mock_session.login.assert_called_once()
                    
                    # Verify session was closed even after failure
                    mock_session.close_session.assert_called_once()
                    
                    # Check failure message and exit code
                    captured = capsys.readouterr()
                    assert "✗ LinkedIn authentication failed." in captured.out
                    mock_exit.assert_called_once_with(1)
    
    def test_main_decrypt_cookies(self, capsys):
        """
        Test decrypt-cookies command execution.
        
        This test verifies that the decrypt-cookies command properly
        decrypts and displays cookie data.
        """
        test_args = ['linkedin_auth.py', 'decrypt-cookies']
        cookie_data = {
            'cookies': [{'name': 'test_cookie', 'value': 'test_value'}],
            'timestamp': '2023-01-01T10:00:00',
            'expiry': '2023-01-31T10:00:00'
        }
        
        with patch('sys.argv', test_args):
            with patch('script.linkedin_auth.LinkedInSession') as mock_session_class:
                mock_session = MagicMock()
                mock_session.decrypt_cookies.return_value = cookie_data
                mock_session_class.return_value = mock_session
                
                main()
                
                # Verify decrypt_cookies was called
                mock_session.decrypt_cookies.assert_called_once()
                
                # Check output
                captured = capsys.readouterr()
                assert "=== Decrypted Cookie Data ===" in captured.out
                assert "test_cookie" in captured.out
                assert "test_value" in captured.out
    
    def test_main_decrypt_cookies_missing(self, capsys):
        """
        Test decrypt-cookies when no cookies exist.
        
        This test verifies appropriate messaging when no cookie file
        is found or decryption fails.
        """
        test_args = ['linkedin_auth.py', 'decrypt-cookies']
        
        with patch('sys.argv', test_args):
            with patch('script.linkedin_auth.LinkedInSession') as mock_session_class:
                mock_session = MagicMock()
                mock_session.decrypt_cookies.return_value = None
                mock_session_class.return_value = mock_session
                
                main()
                
                captured = capsys.readouterr()
                assert "No cookie file found or unable to decrypt" in captured.out
    
    def test_cli_login_command(self):
        """
        Test parsing of basic login command.
        
        This test verifies that the docopt argument parsing correctly
        handles the basic login command without additional flags.
        """
        test_args = ['linkedin_auth.py', 'login']
        
        with patch('sys.argv', test_args):
            with patch('script.linkedin_auth.LinkedInSession') as mock_session_class:
                mock_session = MagicMock()
                mock_session.login.return_value = True
                mock_session_class.return_value = mock_session
                
                main()
                
                # Verify correct parameters were passed
                mock_session_class.assert_called_once_with(headless=False)
                mock_session.login.assert_called_once_with(force_fresh=False)
    
    def test_cli_login_force_fresh(self):
        """
        Test parsing of login command with --force-fresh-login flag.
        
        This test verifies that the --force-fresh-login flag is properly
        parsed and passed to the login method.
        """
        test_args = ['linkedin_auth.py', 'login', '--force-fresh-login']
        
        with patch('sys.argv', test_args):
            with patch('script.linkedin_auth.LinkedInSession') as mock_session_class:
                mock_session = MagicMock()
                mock_session.login.return_value = True
                mock_session_class.return_value = mock_session
                
                main()
                
                # Verify force_fresh flag was passed
                mock_session.login.assert_called_once_with(force_fresh=True)
    
    def test_cli_login_headless(self):
        """
        Test parsing of login command with --headless flag.
        
        This test verifies that the --headless flag is properly parsed
        and passed to the LinkedInSession constructor.
        """
        test_args = ['linkedin_auth.py', 'login', '--headless']
        
        with patch('sys.argv', test_args):
            with patch('script.linkedin_auth.LinkedInSession') as mock_session_class:
                mock_session = MagicMock()
                mock_session.login.return_value = True
                mock_session_class.return_value = mock_session
                
                main()
                
                # Verify headless flag was passed
                mock_session_class.assert_called_once_with(headless=True)
    
    def test_cli_login_headless_force_fresh(self):
        """
        Test parsing of login command with combined --headless and --force-fresh-login flags.
        
        This test verifies that multiple flags can be combined and are
        properly parsed and passed to their respective functions.
        """
        test_args = ['linkedin_auth.py', 'login', '--headless', '--force-fresh-login']
        
        with patch('sys.argv', test_args):
            with patch('script.linkedin_auth.LinkedInSession') as mock_session_class:
                mock_session = MagicMock()
                mock_session.login.return_value = True
                mock_session_class.return_value = mock_session
                
                main()
                
                # Verify both flags were passed correctly
                mock_session_class.assert_called_once_with(headless=True)
                mock_session.login.assert_called_once_with(force_fresh=True)
    
    def test_cli_help(self, capsys):
        """
        Test --help flag displays usage information.
        
        This test verifies that the --help flag displays the docstring
        usage information and exits cleanly.
        """
        test_args = ['linkedin_auth.py', '--help']
        
        with patch('sys.argv', test_args):
            with patch('sys.exit') as mock_exit:
                try:
                    main()
                except SystemExit:
                    pass  # docopt calls sys.exit after showing help
                
                captured = capsys.readouterr()
                # Should contain usage information from docstring
                assert "Usage:" in captured.out
                assert "linkedin_auth.py login" in captured.out
                assert "linkedin_auth.py decrypt-cookies" in captured.out
                assert "Options:" in captured.out
    
    def test_cli_version(self, capsys):
        """
        Test --version flag displays version information.
        
        This test verifies that the --version flag displays the
        version string and exits cleanly.
        """
        test_args = ['linkedin_auth.py', '--version']
        
        with patch('sys.argv', test_args):
            with patch('sys.exit') as mock_exit:
                try:
                    main()
                except SystemExit:
                    pass  # docopt calls sys.exit after showing version
                
                captured = capsys.readouterr()
                # Should contain version information
                assert "LinkedIn Auth 1.0" in captured.out
    
    def test_session_cleanup_on_exception(self):
        """
        Test that browser session is cleaned up even when exceptions occur.
        
        This test verifies that the finally block properly closes the
        browser session even if an exception is raised during login.
        """
        test_args = ['linkedin_auth.py', 'login']
        
        with patch('sys.argv', test_args):
            with patch('script.linkedin_auth.LinkedInSession') as mock_session_class:
                mock_session = MagicMock()
                mock_session.login.side_effect = Exception("Test exception")
                mock_session_class.return_value = mock_session
                
                # Should not raise exception due to try/finally
                with pytest.raises(Exception, match="Test exception"):
                    main()
                
                # Session should still be closed
                mock_session.close_session.assert_called_once()
    
    def test_docopt_integration(self):
        """
        Test integration with docopt argument parsing.
        
        This test verifies that docopt correctly parses the command-line
        arguments according to the docstring specification.
        """
        from docopt import docopt
        
        # Test parsing various command combinations
        test_cases = [
            (['login'], {'login': True, '--force-fresh-login': False, '--headless': False}),
            (['login', '--headless'], {'login': True, '--headless': True}),
            (['login', '--force-fresh-login'], {'login': True, '--force-fresh-login': True}),
            (['decrypt-cookies'], {'decrypt-cookies': True, 'login': False})
        ]
        
        for args, expected_flags in test_cases:
            parsed_args = docopt(cli_module.__doc__, argv=args, version="LinkedIn Auth 1.0")
            
            for flag, expected_value in expected_flags.items():
                assert parsed_args[flag] == expected_value, f"Failed for args {args}, flag {flag}"
    
    def test_json_output_formatting(self, capsys):
        """
        Test that JSON output is properly formatted for decrypt-cookies command.
        
        This test verifies that cookie data is displayed in a readable
        JSON format with proper indentation.
        """
        test_args = ['linkedin_auth.py', 'decrypt-cookies']
        cookie_data = {
            'cookies': [
                {'name': 'cookie1', 'value': 'value1'},
                {'name': 'cookie2', 'value': 'value2'}
            ],
            'timestamp': '2023-01-01T10:00:00'
        }
        
        with patch('sys.argv', test_args):
            with patch('script.linkedin_auth.LinkedInSession') as mock_session_class:
                mock_session = MagicMock()
                mock_session.decrypt_cookies.return_value = cookie_data
                mock_session_class.return_value = mock_session
                
                main()
                
                captured = capsys.readouterr()
                
                # Verify JSON is properly formatted (indented)
                assert '"cookies": [' in captured.out
                assert '  {' in captured.out  # Should have indentation
                assert '"name": "cookie1"' in captured.out
                
                # Verify it's valid JSON by parsing it
                json_start = captured.out.find('{')
                json_end = captured.out.rfind('}') + 1
                json_output = captured.out[json_start:json_end]
                
                parsed_data = json.loads(json_output)
                assert parsed_data == cookie_data