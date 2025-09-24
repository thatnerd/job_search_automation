"""
Unit tests for LinkedInSession authentication detection methods.

These tests cover the is_authenticated method and related functionality
for detecting whether a user is logged into LinkedIn.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, '.')
from lib.linkedin_session import LinkedInSession
from selenium.common.exceptions import NoSuchElementException


class TestLinkedInSessionAuth:
    """Test LinkedInSession authentication detection methods."""
    
    @pytest.fixture
    def session(self):
        """Create a LinkedInSession instance for testing."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                return LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=')
    
    def test_is_authenticated_with_nav_elements(self, session, capsys):
        """
        Test authentication detection via navigation elements.
        
        This test verifies that the presence of LinkedIn navigation elements
        (nav_homepage, nav_mynetwork, etc.) correctly indicates an authenticated state.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        
        # Mock page source with navigation elements
        page_source_with_nav = """
        <html>
            <body>
                <nav data-control-name="nav_homepage">Home</nav>
                <nav data-control-name="nav_jobs">Jobs</nav>
                <div>Other content</div>
            </body>
        </html>
        """
        mock_driver.page_source = page_source_with_nav
        
        with patch.object(session, 'save_page_state', return_value='/path/to/saved.html'):
            authenticated, user_name = session.is_authenticated()
            
            assert authenticated is True
            assert user_name == "User"  # Default when no specific name found
            
            # Verify page state was saved for debugging
            session.save_page_state.assert_called_once_with("auth_check")
    
    def test_is_authenticated_with_user_name(self, session):
        """
        Test authentication detection via user name in page content.

        This test verifies that finding the user's name from LINKEDIN_NAME
        environment variable in the page source correctly identifies the authenticated user.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        
        # Mock page source with user name
        page_source_with_name = """
        <html>
            <body>
                <div data-control-name="nav_homepage">Home</div>
                <div class="profile">Test User</div>
            </body>
        </html>
        """
        mock_driver.page_source = page_source_with_name
        
        # Mock environment variable for user name detection
        with patch.dict(os.environ, {'LINKEDIN_NAME': 'Test User'}):
            with patch.object(session, 'save_page_state'):
                authenticated, user_name = session.is_authenticated()

                assert authenticated is True
                assert user_name == "Test User"
    
    def test_is_authenticated_with_occupation(self, session):
        """
        Test authentication detection via occupation from environment variable.

        This test verifies that finding the user's occupation from LINKEDIN_ROLE
        environment variable indicates an authenticated state even without the exact name.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        
        # Mock page source with occupation
        page_source_with_occupation = """
        <html>
            <body>
                <div data-control-name="nav_jobs">Jobs</div>
                <div class="profile">Technical Test Role at AWS</div>
            </body>
        </html>
        """
        mock_driver.page_source = page_source_with_occupation
        
        # Mock environment variable for role detection
        with patch.dict(os.environ, {'LINKEDIN_ROLE': 'Test Role'}):
            with patch.object(session, 'save_page_state'):
                authenticated, user_name = session.is_authenticated()

                assert authenticated is True
                assert user_name == "User (occupation found)"
    
    def test_is_authenticated_with_profile_element(self, session):
        """
        Test authentication detection via profile/settings menu element.
        
        This test verifies that finding the settings/signout element
        correctly indicates authentication, taking precedence over other indicators.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        
        # Mock page source with navigation but no specific user info
        mock_driver.page_source = """
        <html>
            <body>
                <div data-control-name="nav_homepage">Home</div>
            </body>
        </html>
        """
        
        # Mock successful element finding
        mock_element = MagicMock()
        mock_driver.find_element.return_value = mock_element
        
        with patch.object(session, 'save_page_state'):
            authenticated, user_name = session.is_authenticated()
            
            assert authenticated is True
            assert user_name == "User"
            
            # Verify the correct CSS selector was used
            from selenium.webdriver.common.by import By
            mock_driver.find_element.assert_called_once_with(
                By.CSS_SELECTOR, "[data-control-name='nav.settings_signout']"
            )
    
    def test_is_authenticated_not_logged_in(self, session, capsys):
        """
        Test authentication detection when user is not logged in.
        
        This test verifies that pages without authentication indicators
        correctly return False for authentication status.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        
        # Mock page source without any authentication indicators
        mock_driver.page_source = """
        <html>
            <body>
                <div class="login-form">Please sign in</div>
                <input type="email" placeholder="Email">
                <input type="password" placeholder="Password">
            </body>
        </html>
        """
        
        # Mock element not found (no profile menu)
        mock_driver.find_element.side_effect = NoSuchElementException("Element not found")
        
        with patch.object(session, 'save_page_state'):
            authenticated, user_name = session.is_authenticated()
            
            assert authenticated is False
            assert user_name is None
            
            # Check that debug message was logged
            captured = capsys.readouterr()
            assert "Debug: Profile element not found" in captured.err
    
    def test_is_authenticated_no_driver(self, session):
        """
        Test authentication detection when no browser session is active.
        
        This test verifies that authentication check returns False
        when no WebDriver instance is available.
        """
        session.driver = None
        
        authenticated, user_name = session.is_authenticated()
        
        assert authenticated is False
        assert user_name is None
    
    def test_is_authenticated_precedence_order(self, session):
        """
        Test the precedence order of authentication detection methods.
        
        This test verifies that profile element detection takes precedence
        over name/occupation detection, and that the most specific user
        identification is returned.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        
        # Mock page with both name and occupation
        mock_driver.page_source = """
        <html>
            <body>
                <div data-control-name="nav_homepage">Home</div>
                <div>Test User - Test Role</div>
            </body>
        </html>
        """
        
        # Mock profile element found
        mock_element = MagicMock()
        mock_driver.find_element.return_value = mock_element
        
        # Mock environment variable
        with patch.dict(os.environ, {'LINKEDIN_NAME': 'Test User'}):
            with patch.object(session, 'save_page_state'):
                authenticated, user_name = session.is_authenticated()

                assert authenticated is True
                # Should return Test User (more specific than occupation)
                assert user_name == "Test User"
    
    def test_is_authenticated_nav_elements_detection(self, session):
        """
        Test detection of various LinkedIn navigation elements.
        
        This test verifies that different combinations of navigation
        elements are properly detected as authentication indicators.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        
        # Test each navigation element individually
        nav_elements = ["nav_homepage", "nav_mynetwork", "nav_jobs", "nav_messaging"]
        
        for nav_element in nav_elements:
            mock_driver.page_source = f"""
            <html>
                <body>
                    <div data-control-name="{nav_element}">Navigation</div>
                </body>
            </html>
            """
            
            # Mock no profile element found
            mock_driver.find_element.side_effect = NoSuchElementException("Not found")
            
            with patch.object(session, 'save_page_state'):
                authenticated, user_name = session.is_authenticated()
                
                assert authenticated is True, f"Failed to detect authentication with {nav_element}"
                assert user_name == "User"
    
    def test_is_authenticated_partial_indicators(self, session):
        """
        Test authentication detection with partial indicators.
        
        This test verifies behavior when some but not all expected
        elements are present in the page.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        
        # Page with occupation but no navigation elements
        mock_driver.page_source = """
        <html>
            <body>
                <div class="profile">Test Role position</div>
                <div class="content">No navigation here</div>
            </body>
        </html>
        """
        
        # Mock no profile element
        mock_driver.find_element.side_effect = NoSuchElementException("Not found")
        
        # Mock environment variable for role detection
        with patch.dict(os.environ, {'LINKEDIN_ROLE': 'Test Role'}):
            with patch.object(session, 'save_page_state'):
                authenticated, user_name = session.is_authenticated()

                # Should still be authenticated based on occupation
                assert authenticated is True
                assert user_name == "User (occupation found)"
    
    def test_is_authenticated_saves_debug_state(self, session):
        """
        Test that authentication check always saves page state for debugging.
        
        This test verifies that page state is saved regardless of authentication
        result to aid in troubleshooting authentication issues.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        mock_driver.page_source = "<html><body>Test page</body></html>"
        
        with patch.object(session, 'save_page_state', return_value='/path/to/debug.html') as mock_save:
            # Mock no elements found
            mock_driver.find_element.side_effect = NoSuchElementException("Not found")
            
            session.is_authenticated()
            
            # Verify page state was saved with correct prefix
            mock_save.assert_called_once_with("auth_check")
    
    def test_is_authenticated_user_name_priority(self, session):
        """
        Test user name detection priority (exact name over occupation).
        
        This test verifies that when both exact name and occupation are
        present, the exact name takes precedence in the returned user_name.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        
        # Page with both name and occupation
        mock_driver.page_source = """
        <html>
            <body>
                <div data-control-name="nav_homepage">Home</div>
                <div>Test User</div>
                <div>Test Role at AWS</div>
            </body>
        </html>
        """
        
        # Mock no profile element
        mock_driver.find_element.side_effect = NoSuchElementException("Not found")
        
        # Mock environment variable
        with patch.dict(os.environ, {'LINKEDIN_NAME': 'Test User'}):
            with patch.object(session, 'save_page_state'):
                authenticated, user_name = session.is_authenticated()

                assert authenticated is True
                # Should prefer exact name over occupation
                assert user_name == "Test User"