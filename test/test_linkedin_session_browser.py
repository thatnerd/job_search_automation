"""
Unit tests for LinkedInSession browser management methods.

These tests cover browser session management including starting sessions,
closing sessions, context manager functionality, and Chrome configuration.
"""

import pytest
from unittest.mock import patch, MagicMock, call

import sys
sys.path.insert(0, '.')
from lib.linkedin_session import LinkedInSession


class TestLinkedInSessionBrowser:
    """Test LinkedInSession browser management methods."""
    
    @pytest.fixture
    def session(self):
        """Create a LinkedInSession instance for testing."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                return LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=')
    
    def test_start_session_normal_mode(self, session):
        """
        Test Chrome driver setup in normal (non-headless) mode.
        
        This test verifies that Chrome is configured correctly for normal mode
        with appropriate options including off-screen positioning to avoid
        focus stealing.
        """
        mock_service = MagicMock()
        mock_driver = MagicMock()
        
        with patch('lib.linkedin_session.ChromeDriverManager') as mock_manager:
            with patch('lib.linkedin_session.Service', return_value=mock_service):
                with patch('lib.linkedin_session.Options') as mock_options:
                    with patch('lib.linkedin_session.webdriver.Chrome', return_value=mock_driver):
                        mock_manager.return_value.install.return_value = '/path/to/chromedriver'
                        
                        # Test normal mode (headless=False)
                        session.headless = False
                        result = session.start_session()
                        
                        # Verify Chrome options were configured correctly
                        options_instance = mock_options.return_value
                        options_instance.add_argument.assert_any_call(
                            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        )
                        options_instance.add_argument.assert_any_call("--disable-blink-features=AutomationControlled")
                        options_instance.add_argument.assert_any_call("--window-position=-2000,-2000")  # Off-screen start
                        options_instance.add_argument.assert_any_call("--no-sandbox")
                        
                        # Verify WebDriver was created
                        assert result == mock_driver
                        assert session.driver == mock_driver
                        
                        # Verify anti-automation script was executed
                        mock_driver.execute_script.assert_called_once()
                        
                        # Verify window was moved to visible position
                        mock_driver.set_window_position.assert_called_once_with(100, 100)
    
    def test_start_session_headless_mode(self, session):
        """
        Test Chrome driver setup in headless mode.
        
        This test verifies that Chrome is configured correctly for headless mode
        with appropriate options and that window positioning is not attempted.
        """
        mock_driver = MagicMock()
        
        with patch('lib.linkedin_session.ChromeDriverManager') as mock_manager:
            with patch('lib.linkedin_session.Service'):
                with patch('lib.linkedin_session.Options') as mock_options:
                    with patch('lib.linkedin_session.webdriver.Chrome', return_value=mock_driver):
                        mock_manager.return_value.install.return_value = '/path/to/chromedriver'
                        
                        # Test headless mode
                        session.headless = True
                        result = session.start_session()
                        
                        # Verify headless options were set
                        options_instance = mock_options.return_value
                        options_instance.add_argument.assert_any_call("--headless=new")
                        options_instance.add_argument.assert_any_call("--window-size=1920,1080")
                        
                        # Verify window positioning was NOT called in headless mode
                        mock_driver.set_window_position.assert_not_called()
                        
                        assert result == mock_driver
    
    def test_start_session_already_started(self, session):
        """
        Test calling start_session() when a session is already active.
        
        This test verifies that if a browser session is already running,
        calling start_session() again returns the existing driver without
        creating a new one.
        """
        existing_driver = MagicMock()
        session.driver = existing_driver
        
        # Should return existing driver without creating new one
        result = session.start_session()
        
        assert result == existing_driver
        assert session.driver == existing_driver
    
    def test_close_session(self, session):
        """
        Test browser session cleanup.
        
        This test verifies that close_session() properly quits the browser
        and resets the driver reference to None.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        
        session.close_session()
        
        # Verify driver was quit and reset
        mock_driver.quit.assert_called_once()
        assert session.driver is None
    
    def test_close_session_no_driver(self, session):
        """
        Test close_session() when no driver is active.
        
        This test verifies that close_session() handles the case where
        no browser session is currently active without raising errors.
        """
        # Ensure no driver is set
        session.driver = None
        
        # Should not raise an error
        session.close_session()
        
        assert session.driver is None
    
    def test_context_manager(self, session):
        """
        Test __enter__ and __exit__ methods for context manager usage.
        
        This test verifies that LinkedInSession can be used as a context manager
        and that browser sessions are properly started and cleaned up.
        """
        mock_driver = MagicMock()
        
        with patch.object(session, 'start_session', return_value=mock_driver) as mock_start:
            with patch.object(session, 'close_session') as mock_close:
                
                # Test context manager entry
                result = session.__enter__()
                assert result == session
                mock_start.assert_called_once()
                
                # Test context manager exit
                session.__exit__(None, None, None)
                mock_close.assert_called_once()
    
    def test_context_manager_with_exception(self, session):
        """
        Test context manager cleanup when an exception occurs.
        
        This test verifies that the browser session is properly closed
        even when an exception occurs within the context manager block.
        """
        with patch.object(session, 'start_session'):
            with patch.object(session, 'close_session') as mock_close:
                
                # Simulate exception in context manager
                session.__exit__(Exception, Exception("test error"), None)
                
                # Should still call close_session
                mock_close.assert_called_once()
    
    def test_chrome_options_configuration(self, session):
        """
        Test that Chrome options are configured with security and stability settings.
        
        This test verifies that all the necessary Chrome options are set for
        avoiding detection, stability, and proper operation.
        """
        with patch('lib.linkedin_session.ChromeDriverManager') as mock_manager:
            with patch('lib.linkedin_session.Service'):
                with patch('lib.linkedin_session.Options') as mock_options:
                    with patch('lib.linkedin_session.webdriver.Chrome'):
                        mock_manager.return_value.install.return_value = '/path/to/chromedriver'
                        
                        session.start_session()
                        
                        options_instance = mock_options.return_value
                        
                        # Verify anti-detection options
                        options_instance.add_experimental_option.assert_any_call(
                            "excludeSwitches", ["enable-automation"]
                        )
                        options_instance.add_experimental_option.assert_any_call(
                            'useAutomationExtension', False
                        )
                        
                        # Verify stability options
                        options_instance.add_argument.assert_any_call("--no-sandbox")
                        options_instance.add_argument.assert_any_call("--disable-dev-shm-usage")
                        options_instance.add_argument.assert_any_call("--disable-gpu")
    
    def test_webdriver_manager_integration(self, session):
        """
        Test integration with webdriver-manager for ChromeDriver.
        
        This test verifies that ChromeDriverManager is used to automatically
        manage the ChromeDriver installation and that the Service is configured
        with the correct driver path.
        """
        mock_driver_path = '/path/to/auto/chromedriver'
        mock_service = MagicMock()
        
        with patch('lib.linkedin_session.ChromeDriverManager') as mock_manager:
            with patch('lib.linkedin_session.Service', return_value=mock_service) as mock_service_class:
                with patch('lib.linkedin_session.webdriver.Chrome'):
                    mock_manager.return_value.install.return_value = mock_driver_path
                    
                    session.start_session()
                    
                    # Verify ChromeDriverManager was used
                    mock_manager.assert_called_once()
                    mock_manager.return_value.install.assert_called_once()
                    
                    # Verify Service was created with correct path
                    mock_service_class.assert_called_once_with(mock_driver_path)