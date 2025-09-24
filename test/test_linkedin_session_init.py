"""
Unit tests for LinkedInSession class initialization and setup methods.

These tests cover the constructor, directory creation, encryption key handling,
and basic configuration of the LinkedInSession class.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, '.')
from lib.linkedin_session import LinkedInSession


class TestLinkedInSessionInit:
    """Test LinkedInSession class initialization and setup."""
    
    def test_init_with_encryption_key(self, tmp_path):
        """
        Test LinkedInSession initialization with a provided encryption key.
        
        This test verifies that when an encryption key is explicitly provided,
        it is used directly without checking environment variables.
        """
        test_key = "rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs="
        
        with patch('lib.linkedin_session.Path.mkdir') as mock_mkdir:
            with patch('lib.linkedin_session.load_dotenv'):
                session = LinkedInSession(encryption_key=test_key, headless=True)
                
                assert session.encryption_key == test_key
                assert session.headless is True
                # Should create data directories
                assert mock_mkdir.call_count >= 3  # cookies, screenshots, html dirs
    
    @patch.dict(os.environ, {'COOKIE_ENCRYPTION_KEY': 'rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs='})
    def test_init_without_encryption_key(self):
        """
        Test LinkedInSession initialization loading key from environment.
        
        This test verifies that when no encryption key is provided, the class
        loads the key from the COOKIE_ENCRYPTION_KEY environment variable.
        """
        with patch('lib.linkedin_session.Path.mkdir') as mock_mkdir:
            with patch('lib.linkedin_session.load_dotenv'):
                session = LinkedInSession(headless=False)
                
                assert session.encryption_key == 'rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs='
                assert session.headless is False
                assert mock_mkdir.call_count >= 3
    
    @patch.dict(os.environ, {}, clear=True)  # Clear environment variables
    def test_init_generates_key_when_missing(self, capsys):
        """
        Test key generation when COOKIE_ENCRYPTION_KEY is not in environment.
        
        This test verifies that when no encryption key is found in the environment,
        a new key is generated and the user is prompted to add it to their .env file.
        """
        with patch('lib.linkedin_session.Fernet.generate_key') as mock_generate:
            mock_generate.return_value.decode.return_value = 'rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs='
            
            with patch('lib.linkedin_session.Path.mkdir'):
                with patch('lib.linkedin_session.load_dotenv'):
                    session = LinkedInSession()
                    
                    assert session.encryption_key == 'rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs='
                    
                    # Check that warning messages were printed
                    captured = capsys.readouterr()
                    assert "Warning: COOKIE_ENCRYPTION_KEY not set" in captured.out
                    assert "COOKIE_ENCRYPTION_KEY=rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=" in captured.out
    
    def test_init_creates_directories(self):
        """
        Test that LinkedInSession initialization creates required directories.
        
        This test verifies that the data, cookies, screenshots, and html
        directories are created during initialization.
        """
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir') as mock_mkdir:
                session = LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=')
                
                # Verify mkdir was called for each directory
                expected_calls = [
                    # Each directory should be created with parents=True, exist_ok=True
                    ((session.cookies_dir,), {'parents': True, 'exist_ok': True}),
                    ((session.screenshots_dir,), {'parents': True, 'exist_ok': True}),
                    ((session.html_dir,), {'parents': True, 'exist_ok': True})
                ]
                
                # Check that mkdir was called at least once for each directory type
                assert mock_mkdir.call_count >= 3
                
                # Verify that the directories are set up correctly
                assert session.data_dir == Path("data")
                assert session.cookies_dir == Path("data/cookies")
                assert session.screenshots_dir == Path("data/screenshots")
                assert session.html_dir == Path("data/html")
    
    def test_init_headless_flag(self):
        """
        Test that the headless flag is properly configured.
        
        This test verifies that the headless parameter is correctly stored
        and that it defaults to False when not specified.
        """
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                # Test with headless=True
                session_headless = LinkedInSession(
                    encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=',
                    headless=True
                )
                assert session_headless.headless is True
                
                # Test with headless=False
                session_normal = LinkedInSession(
                    encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=',
                    headless=False
                )
                assert session_normal.headless is False
                
                # Test default (should be False)
                session_default = LinkedInSession(
                    encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs='
                )
                assert session_default.headless is False
    
    def test_init_sets_up_fernet(self):
        """
        Test that Fernet encryption is properly initialized.
        
        This test verifies that the Fernet instance is created with the
        provided encryption key for cookie encryption/decryption.
        """
        test_key = 'rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs='
        
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                with patch('lib.linkedin_session.Fernet') as mock_fernet:
                    session = LinkedInSession(encryption_key=test_key)
                    
                    # Verify Fernet was initialized with the encoded key
                    mock_fernet.assert_called_once_with(test_key.encode())
                    assert session.fernet == mock_fernet.return_value
    
    def test_init_sets_driver_to_none(self):
        """
        Test that the WebDriver is initially set to None.
        
        This test verifies that no browser session is started during
        initialization - it should only be created when explicitly requested.
        """
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                session = LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=')

                assert session.driver is None
    
    def test_init_sets_up_paths(self):
        """
        Test that all file paths are properly configured.
        
        This test verifies that the cookie file path and directory paths
        are set up correctly relative to the data directory.
        """
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                session = LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=')

                # Test that paths are configured correctly
                assert session.cookie_file == session.cookies_dir / "linkedin_session.json.enc"
                assert str(session.cookie_file).endswith("data/cookies/linkedin_session.json.enc")
                
                # Test that all directory paths are Path objects
                assert isinstance(session.data_dir, Path)
                assert isinstance(session.cookies_dir, Path)
                assert isinstance(session.screenshots_dir, Path)
                assert isinstance(session.html_dir, Path)