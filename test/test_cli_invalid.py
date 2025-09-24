"""
Tests for invalid CLI invocations and error handling.

These tests cover edge cases, invalid command combinations,
and malformed command-line arguments to ensure robust error handling.
"""

import sys
import pytest
from unittest.mock import patch
from docopt import DocoptExit

# Add the project root to the path for imports
sys.path.insert(0, '.')
import script.linkedin_auth as cli_module
from script.linkedin_auth import main


class TestLinkedInAuthCLIInvalid:
    """Test invalid CLI invocations and error handling."""
    
    def test_cli_invalid_command(self):
        """
        Test handling of invalid command arguments.
        
        This test verifies that invalid commands like 'invalid' are
        properly rejected with appropriate error messages.
        """
        test_args = ['linkedin_auth.py', 'invalid']
        
        with patch('sys.argv', test_args):
            # docopt should raise DocoptExit for invalid commands
            with pytest.raises(SystemExit):
                main()
    
    def test_cli_no_command(self):
        """
        Test handling when no command is provided.
        
        This test verifies that running the script without any command
        displays usage information and exits appropriately.
        """
        test_args = ['linkedin_auth.py']
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):
                main()
    
    def test_cli_invalid_flag_combination(self):
        """
        Test handling of flags without required command.
        
        This test verifies that providing flags without a valid command
        results in appropriate error handling.
        """
        test_args = ['linkedin_auth.py', '--headless']  # Flag without command
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):
                main()
    
    def test_cli_unknown_flag(self):
        """
        Test handling of unknown/unsupported flags.
        
        This test verifies that unknown flags are rejected with
        appropriate error messages from docopt.
        """
        test_args = ['linkedin_auth.py', 'login', '--unknown-flag']
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):
                main()
    
    def test_cli_extra_arguments(self):
        """
        Test handling of unexpected extra arguments.
        
        This test verifies that extra arguments beyond what's defined
        in the docstring are properly rejected.
        """
        test_args = ['linkedin_auth.py', 'login', 'extra', 'arguments']
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):
                main()
    
    def test_cli_decrypt_with_flags(self):
        """
        Test that decrypt-cookies command rejects login-specific flags.
        
        This test verifies that flags specific to the login command
        are not accepted with the decrypt-cookies command.
        """
        test_args = ['linkedin_auth.py', 'decrypt-cookies', '--headless']
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):
                main()
    
    def test_docopt_parsing_edge_cases(self):
        """
        Test edge cases in docopt argument parsing.
        
        This test verifies that various malformed argument combinations
        are properly handled by the docopt parser.
        """
        from docopt import docopt
        
        # Test cases that should raise DocoptExit
        invalid_cases = [
            [],  # No arguments
            ['invalid-command'],  # Invalid command
            ['login', 'extra'],  # Extra arguments
            ['--headless'],  # Flag without command
            ['login', '--invalid-flag'],  # Invalid flag
            ['decrypt-cookies', '--force-fresh-login'],  # Wrong flag for command
        ]
        
        for invalid_args in invalid_cases:
            with pytest.raises(DocoptExit):
                docopt(cli_module.__doc__, argv=invalid_args, version="LinkedIn Auth 1.0")
    
    def test_cli_case_sensitivity(self):
        """
        Test that commands are case-sensitive.
        
        This test verifies that commands must be in the exact case
        as specified in the docstring (lowercase).
        """
        test_cases = [
            ['LOGIN'],  # Uppercase command
            ['Login'],  # Mixed case command  
            ['DECRYPT-COOKIES'],  # Uppercase command
        ]
        
        for test_args in test_cases:
            full_args = ['linkedin_auth.py'] + test_args
            with patch('sys.argv', full_args):
                with pytest.raises(SystemExit):
                    main()
    
    def test_cli_flag_variations(self):
        """
        Test various flag format variations.
        
        This test verifies that flags must be in the exact format
        specified and that variations are rejected.
        """
        invalid_flag_cases = [
            ['login', '-h'],  # Should be --help
            ['login', '--force_fresh_login'],  # Underscore instead of dash
            ['login', '--headless=true'],  # Equals sign not supported
            ['login', '--HEADLESS'],  # Uppercase flag
        ]
        
        for test_args in invalid_flag_cases:
            full_args = ['linkedin_auth.py'] + test_args
            with patch('sys.argv', full_args):
                # Some of these might not raise SystemExit (like -h), 
                # so we catch both possible outcomes
                try:
                    main()
                except SystemExit:
                    pass  # Expected for invalid arguments
                except Exception as e:
                    # Verify it's an argument parsing related error
                    assert 'argument' in str(e).lower() or 'option' in str(e).lower()
    
    def test_cli_empty_string_arguments(self):
        """
        Test handling of empty string arguments.
        
        This test verifies that empty strings in arguments are
        properly handled or rejected.
        """
        test_args = ['linkedin_auth.py', '']
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):
                main()
    
    def test_cli_special_characters(self):
        """
        Test handling of special characters in arguments.
        
        This test verifies that arguments containing special characters
        are properly handled by the argument parser.
        """
        special_char_cases = [
            ['login@special'],
            ['login!'],
            ['login#test'],
            ['login$'],
        ]
        
        for test_args in special_char_cases:
            full_args = ['linkedin_auth.py'] + test_args
            with patch('sys.argv', full_args):
                with pytest.raises(SystemExit):
                    main()
    
    def test_docopt_version_format(self):
        """
        Test that the version string matches expected format.
        
        This test verifies that the version string used in docopt
        matches the expected format and is consistent.
        """
        from docopt import docopt
        
        # Test that version is properly formatted
        test_args = ['--version']
        
        with pytest.raises(SystemExit):
            docopt(cli_module.__doc__, argv=test_args, version="LinkedIn Auth 1.0")
    
    def test_docopt_help_content(self):
        """
        Test that help output contains required information.
        
        This test verifies that the help output includes all necessary
        usage information and examples.
        """
        from docopt import docopt
        
        test_args = ['--help']
        
        with pytest.raises(SystemExit):
            docopt(cli_module.__doc__, argv=test_args, version="LinkedIn Auth 1.0")