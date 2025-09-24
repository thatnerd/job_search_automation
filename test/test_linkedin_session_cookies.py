"""
Unit tests for LinkedInSession cookie management methods.

These tests cover cookie storage, retrieval, encryption, decryption,
and loading cookies into browser sessions.
"""

import json
import os
import tempfile
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import sys
sys.path.insert(0, '.')
from lib.linkedin_session import LinkedInSession


class TestLinkedInSessionCookies:
    """Test LinkedInSession cookie management methods."""
    
    @pytest.fixture
    def session(self):
        """Create a LinkedInSession instance for testing."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                return LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=')
    
    def test_get_stored_cookies_valid(self, session):
        """
        Test loading valid, non-expired cookies from storage.
        
        This test verifies that valid cookies are properly decrypted and returned
        when they exist and haven't expired.
        """
        # Create mock valid cookie data
        valid_cookies = [
            {'name': 'test_cookie', 'value': 'test_value', 'domain': 'linkedin.com'}
        ]
        cookie_data = {
            'cookies': valid_cookies,
            'timestamp': datetime.now().isoformat(),
            'expiry': (datetime.now() + timedelta(days=5)).isoformat()  # Valid for 5 more days
        }
        encrypted_data = b'encrypted_cookie_data'
        
        # Mock file operations
        mock_cookie_file = MagicMock()
        mock_cookie_file.exists.return_value = True
        mock_cookie_file.read_bytes.return_value = encrypted_data

        with patch.object(session, 'cookie_file', mock_cookie_file):
            with patch.object(session.fernet, 'decrypt', return_value=json.dumps(cookie_data).encode()):

                result = session.get_stored_cookies()

                assert result == valid_cookies
                session.fernet.decrypt.assert_called_once_with(encrypted_data)
    
    def test_get_stored_cookies_expired(self, session):
        """
        Test handling of expired cookies.
        
        This test verifies that expired cookies are detected and None is returned
        instead of the expired cookie data.
        """
        # Create expired cookie data
        cookie_data = {
            'cookies': [{'name': 'test_cookie', 'value': 'test_value'}],
            'timestamp': datetime.now().isoformat(),
            'expiry': (datetime.now() - timedelta(days=1)).isoformat()  # Expired 1 day ago
        }
        
        mock_cookie_file = MagicMock()
        mock_cookie_file.exists.return_value = True
        mock_cookie_file.read_bytes.return_value = b'encrypted_data'

        with patch.object(session, 'cookie_file', mock_cookie_file):
            with patch.object(session.fernet, 'decrypt', return_value=json.dumps(cookie_data).encode()):

                result = session.get_stored_cookies()

                assert result is None
    
    def test_get_stored_cookies_missing_file(self, session):
        """
        Test when cookie file doesn't exist.
        
        This test verifies that None is returned when no cookie file exists.
        """
        mock_cookie_file = MagicMock()
        mock_cookie_file.exists.return_value = False

        with patch.object(session, 'cookie_file', mock_cookie_file):
            result = session.get_stored_cookies()
            assert result is None
    
    def test_get_stored_cookies_corrupted_data(self, session, capsys):
        """
        Test handling corrupted cookie data.
        
        This test verifies that corrupted JSON data is handled gracefully
        and appropriate warnings are logged to stderr.
        """
        mock_cookie_file = MagicMock()
        mock_cookie_file.exists.return_value = True
        mock_cookie_file.read_bytes.return_value = b'encrypted_data'

        with patch.object(session, 'cookie_file', mock_cookie_file):
            with patch.object(session.fernet, 'decrypt', return_value=b'invalid_json_data'):

                result = session.get_stored_cookies()

                assert result is None
                # Check that warning was logged to stderr
                captured = capsys.readouterr()
                assert "Warning: Cookie data format issue" in captured.err
    
    def test_get_stored_cookies_permission_error(self, session, capsys):
        """
        Test permission denied scenarios when accessing cookie file.
        
        This test verifies that permission errors are handled gracefully
        with appropriate error logging.
        """
        mock_cookie_file = MagicMock()
        mock_cookie_file.exists.return_value = True
        mock_cookie_file.read_bytes.side_effect = PermissionError("Access denied")

        with patch.object(session, 'cookie_file', mock_cookie_file):

            result = session.get_stored_cookies()

            assert result is None
            captured = capsys.readouterr()
            assert "Warning: Could not access cookie file" in captured.err
    
    def test_save_cookies(self, session):
        """
        Test cookie encryption and saving to file.
        
        This test verifies that cookies are properly retrieved from the browser,
        encrypted, and saved to the cookie file with appropriate metadata.
        """
        mock_driver = MagicMock()
        test_cookies = [
            {'name': 'cookie1', 'value': 'value1'},
            {'name': 'cookie2', 'value': 'value2'}
        ]
        mock_driver.get_cookies.return_value = test_cookies
        session.driver = mock_driver
        
        encrypted_data = b'encrypted_cookie_data'
        
        mock_cookie_file = MagicMock()

        mock_cookies_dir = MagicMock()

        with patch.object(session, 'cookie_file', mock_cookie_file):
            with patch.object(session, 'cookies_dir', mock_cookies_dir):
                with patch.object(session.fernet, 'encrypt', return_value=encrypted_data) as mock_encrypt:
                    
                    session.save_cookies()
                    
                    # Verify cookies were retrieved from driver
                    mock_driver.get_cookies.assert_called_once()
                    
                    # Verify directory creation
                    mock_cookies_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
                    
                    # Verify encryption was called with proper data structure
                    mock_encrypt.assert_called_once()
                    encrypt_call_args = json.loads(mock_encrypt.call_args[0][0])
                    assert encrypt_call_args['cookies'] == test_cookies
                    assert 'timestamp' in encrypt_call_args
                    assert 'expiry' in encrypt_call_args
                    
                    # Verify encrypted data was written to file
                    mock_cookie_file.write_bytes.assert_called_once_with(encrypted_data)
    
    def test_save_cookies_no_driver(self, session):
        """
        Test error when attempting to save cookies with no active driver.
        
        This test verifies that a RuntimeError is raised when trying to save
        cookies without an active browser session.
        """
        session.driver = None
        
        with pytest.raises(RuntimeError, match="No active session to save cookies from"):
            session.save_cookies()
    
    def test_decrypt_cookies_valid(self, session):
        """
        Test successful cookie decryption for inspection.
        
        This test verifies that the decrypt_cookies method properly decrypts
        and returns the full cookie data structure for user inspection.
        """
        cookie_data = {
            'cookies': [{'name': 'test_cookie', 'value': 'test_value'}],
            'timestamp': '2023-01-01T10:00:00',
            'expiry': '2023-01-31T10:00:00'
        }
        encrypted_data = b'encrypted_data'
        
        mock_cookie_file = MagicMock()
        mock_cookie_file.exists.return_value = True
        mock_cookie_file.read_bytes.return_value = encrypted_data

        with patch.object(session, 'cookie_file', mock_cookie_file):
            with patch.object(session.fernet, 'decrypt', return_value=json.dumps(cookie_data).encode()):

                result = session.decrypt_cookies()

                assert result == cookie_data
    
    def test_decrypt_cookies_corrupted(self, session, capsys):
        """
        Test handling corrupted encrypted cookie data.
        
        This test verifies that corrupted data is handled gracefully during
        decryption with appropriate error messages.
        """
        mock_cookie_file = MagicMock()
        mock_cookie_file.exists.return_value = True
        mock_cookie_file.read_bytes.return_value = b'encrypted_data'

        with patch.object(session, 'cookie_file', mock_cookie_file):
            with patch.object(session.fernet, 'decrypt', return_value=b'corrupted_json'):

                result = session.decrypt_cookies()

                assert result is None
                captured = capsys.readouterr()
                assert "Error: Cookie data is corrupted" in captured.err
    
    def test_decrypt_cookies_missing(self, session):
        """
        Test decrypt_cookies when no cookie file exists.
        
        This test verifies that None is returned when attempting to decrypt
        cookies that don't exist.
        """
        mock_cookie_file = MagicMock()
        mock_cookie_file.exists.return_value = False

        with patch.object(session, 'cookie_file', mock_cookie_file):
            result = session.decrypt_cookies()
            assert result is None
    
    def test_load_cookies_to_session_success(self, session, capsys):
        """
        Test successful cookie loading into browser session.
        
        This test verifies that stored cookies are properly loaded into the
        browser session and the page is refreshed to apply them.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        
        test_cookies = [
            {'name': 'cookie1', 'value': 'value1', 'domain': 'linkedin.com'},
            {'name': 'cookie2', 'value': 'value2', 'expiry': 1234567890}  # Will be converted to 'expires'
        ]
        
        with patch.object(session, 'get_stored_cookies', return_value=test_cookies):
            result = session.load_cookies_to_session()
            
            assert result is True
            
            # Verify browser navigation to LinkedIn
            mock_driver.get.assert_called_once_with("https://www.linkedin.com")
            
            # Verify cookies were added (expiry should be converted to expires)
            expected_calls = [
                (({'name': 'cookie1', 'value': 'value1', 'domain': 'linkedin.com'},),),
                (({'name': 'cookie2', 'value': 'value2', 'expires': 1234567890},),)
            ]
            assert mock_driver.add_cookie.call_count == 2
            
            # Verify page was refreshed
            mock_driver.refresh.assert_called_once()
            
            # Check success message
            captured = capsys.readouterr()
            assert "Attempting to use existing cookies" in captured.out
    
    def test_load_cookies_to_session_no_cookies(self, session):
        """
        Test loading cookies when no stored cookies are available.
        
        This test verifies that False is returned when no cookies are available
        to load into the browser session.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        
        with patch.object(session, 'get_stored_cookies', return_value=None):
            result = session.load_cookies_to_session()
            
            assert result is False
            # Should not attempt to navigate or add cookies
            mock_driver.get.assert_not_called()
            mock_driver.add_cookie.assert_not_called()
    
    def test_load_cookies_to_session_invalid_cookies(self, session, capsys):
        """
        Test handling invalid cookie formats during loading.
        
        This test verifies that invalid cookies are skipped with warnings
        and the loading process continues for valid cookies.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        
        # Mock add_cookie to fail for first cookie, succeed for second
        from selenium.common.exceptions import WebDriverException
        mock_driver.add_cookie.side_effect = [
            WebDriverException("Invalid cookie format"),  # First cookie fails
            None  # Second cookie succeeds
        ]
        
        test_cookies = [
            {'name': 'invalid_cookie', 'value': 'bad_format'},
            {'name': 'valid_cookie', 'value': 'good_format'}
        ]
        
        with patch.object(session, 'get_stored_cookies', return_value=test_cookies):
            result = session.load_cookies_to_session()
            
            assert result is True  # Should still return True even with some failures
            assert mock_driver.add_cookie.call_count == 2
            
            # Check that warning was logged for failed cookie
            captured = capsys.readouterr()
            assert "Warning: Could not add cookie 'invalid_cookie'" in captured.err
    
    def test_load_cookies_to_session_no_driver(self, session):
        """
        Test error when loading cookies with no active driver.
        
        This test verifies that a RuntimeError is raised when trying to load
        cookies without an active browser session.
        """
        session.driver = None
        
        with pytest.raises(RuntimeError, match="No active session to load cookies into"):
            session.load_cookies_to_session()
    
    def test_cookie_expiry_calculation(self, session):
        """
        Test that cookie expiry is set correctly (30 days from now).
        
        This test verifies that when saving cookies, the expiry date is
        calculated correctly as 30 days from the current time.
        """
        mock_driver = MagicMock()
        mock_driver.get_cookies.return_value = []
        session.driver = mock_driver
        
        mock_cookie_file = MagicMock()

        mock_cookies_dir = MagicMock()

        with patch.object(session, 'cookie_file', mock_cookie_file):
            with patch.object(session, 'cookies_dir', mock_cookies_dir):
                with patch.object(session.fernet, 'encrypt', return_value=b'encrypted') as mock_encrypt:
                    
                    before_save = datetime.now()
                    session.save_cookies()
                    after_save = datetime.now()
                    
                    # Extract the data that was encrypted
                    encrypted_data = json.loads(mock_encrypt.call_args[0][0])
                    expiry = datetime.fromisoformat(encrypted_data['expiry'])
                    
                    # Verify expiry is approximately 30 days from now
                    expected_expiry_min = before_save + timedelta(days=29, hours=23)
                    expected_expiry_max = after_save + timedelta(days=30, hours=1)
                    
                    assert expected_expiry_min <= expiry <= expected_expiry_max