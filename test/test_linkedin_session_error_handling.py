"""
Tests for LinkedIn session error handling and stack trace management.

These tests focus specifically on proper exception handling without
generating unnecessary stack traces that clutter stderr output.

Following TDD principles, these tests expose current logging issues
and validate that fixes produce clean, professional error messages.
"""

import pytest
import sys
import io
from contextlib import redirect_stderr
from unittest.mock import patch, MagicMock
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException

# Add project root to path
sys.path.insert(0, '.')
from lib.linkedin_session import LinkedInSession


class TestLinkedInErrorHandling:
    """Test LinkedIn session error handling and professional error messaging."""

    @pytest.fixture
    def session(self):
        """Create a LinkedInSession instance for testing."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                return LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUfs=', headless=True)

    def test_authentication_check_clean_error_messages(self, session):
        """
        Test that authentication failures produce clean, professional error messages.

        This test verifies that NoSuchElementException handling in is_authenticated
        produces concise debug messages without stack traces.

        EXPECTED TO FAIL initially - current implementation may log full exception details.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver

        # Mock page without authentication elements
        mock_driver.page_source = "<html><body><div>Login page</div></body></html>"

        # Mock exception with realistic message
        profile_exception = NoSuchElementException(
            "Unable to locate element: {\"method\":\"css selector\",\"selector\":\"[data-control-name='nav.settings_signout']\"}; "
            "For documentation on this error, please visit: "
            "https://selenium-python.readthedocs.io/api.html#module-selenium.common.exceptions"
        )
        mock_driver.find_element.side_effect = profile_exception

        # Capture stderr to analyze error message format
        stderr_capture = io.StringIO()

        with patch.object(session, 'save_page_state'):
            with redirect_stderr(stderr_capture):
                authenticated, user_name = session.is_authenticated()

        # Verify authentication fails as expected
        assert authenticated is False
        assert user_name is None

        # Analyze stderr output
        stderr_output = stderr_capture.getvalue()

        # Should contain a debug message
        assert stderr_output.strip() != "", "Should log debug information"

        # After fix, should be a single clean line
        lines = [line.strip() for line in stderr_output.split('\n') if line.strip()]

        # Should not contain stack trace markers
        stack_trace_indicators = [
            "Traceback (most recent call last):",
            "File \"",
            "line ",
            "selenium.common.exceptions.",
            "For documentation on this error"
        ]

        for line in lines:
            for indicator in stack_trace_indicators:
                assert indicator not in line, f"Stack trace detected in: {line}"

        # Should contain exactly one informative debug line
        debug_lines = [line for line in lines if "Debug:" in line]
        assert len(debug_lines) == 1, f"Expected exactly one debug line, got: {lines}"

        # Debug line should be concise and informative
        debug_line = debug_lines[0]
        assert "Profile element not found" in debug_line
        assert "may be normal" in debug_line
        assert len(debug_line) < 150, f"Debug message too verbose: {debug_line}"

    def test_authentication_exception_message_extraction(self, session):
        """
        Test that relevant exception information is preserved while avoiding stack traces.

        Verifies that important error context is maintained in debug messages
        while eliminating verbose stack trace output.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        mock_driver.page_source = "<html><body>Test page</body></html>"

        test_cases = [
            # Standard NoSuchElementException
            NoSuchElementException("Element not found"),

            # Realistic Selenium exception with URL documentation
            NoSuchElementException(
                "Unable to locate element: {\"method\":\"css selector\",\"selector\":\"[data-control-name='nav.settings_signout']\"}; "
                "For documentation visit: https://selenium-python.readthedocs.io/"
            ),

            # WebDriver communication error
            WebDriverException("chrome not reachable"),

            # Timeout waiting for element
            TimeoutException("Timed out waiting for element to be present")
        ]

        for exception in test_cases:
            mock_driver.find_element.side_effect = exception
            stderr_capture = io.StringIO()

            with patch.object(session, 'save_page_state'):
                with redirect_stderr(stderr_capture):
                    authenticated, user_name = session.is_authenticated()

            # Should handle all exceptions gracefully
            assert authenticated is False
            assert user_name is None

            # Check stderr format
            stderr_output = stderr_capture.getvalue().strip()

            if stderr_output:  # Some exceptions might not log anything
                # Should not contain full exception class names or documentation URLs
                assert "selenium.common.exceptions" not in stderr_output
                assert "https://selenium-python.readthedocs.io" not in stderr_output
                assert "Traceback" not in stderr_output

                # Should contain brief, relevant information
                lines = [line.strip() for line in stderr_output.split('\n') if line.strip()]
                assert all(len(line) < 200 for line in lines), "Error messages should be concise"

    def test_job_scraping_error_message_format(self, session):
        """
        Test that job scraping errors produce clean, actionable messages.

        Verifies that scrape_jobs method handles various exceptions
        with professional error messages rather than raw stack traces.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        mock_driver.page_source = "<html><body>Jobs page</body></html>"

        # Mock various exception scenarios in job scraping
        exception_scenarios = [
            ("Invalid selector", "InvalidSelectorException: Invalid selector syntax"),
            ("Network timeout", "TimeoutException: Page load timeout"),
            ("Element not found", "NoSuchElementException: Show all button not found"),
            ("WebDriver crash", "WebDriverException: Chrome crashed")
        ]

        for scenario_name, exception_message in exception_scenarios:
            # Create appropriate exception type based on message
            if "InvalidSelectorException" in exception_message:
                from selenium.common.exceptions import InvalidSelectorException
                exception = InvalidSelectorException(exception_message)
            elif "TimeoutException" in exception_message:
                exception = TimeoutException(exception_message)
            elif "WebDriverException" in exception_message:
                exception = WebDriverException(exception_message)
            else:
                exception = NoSuchElementException(exception_message)

            # Mock exception during show_all button search
            mock_driver.find_element.side_effect = exception
            mock_driver.find_elements.return_value = []  # No jobs found

            stderr_capture = io.StringIO()

            with patch.object(session, 'save_page_state'):
                with redirect_stderr(stderr_capture):
                    jobs = session.scrape_jobs(show_all=True)

            # Should return empty list gracefully
            assert isinstance(jobs, list)
            assert len(jobs) == 0

            # Check error message quality
            stderr_output = stderr_capture.getvalue()

            if stderr_output.strip():  # May not log for all scenarios
                # Should contain warning about show_all failure
                assert "Warning:" in stderr_output or "Error:" in stderr_output

                # Should not contain raw exception class names or full stack traces
                assert "Exception:" not in stderr_output  # No raw exception class names
                assert "Traceback" not in stderr_output
                assert "File \"" not in stderr_output

    def test_authentication_no_driver_scenario(self, session):
        """
        Test authentication check when no WebDriver is available.

        Verifies clean handling of the edge case where driver is None,
        which should not generate any error messages.
        """
        # Ensure no driver is set
        session.driver = None

        stderr_capture = io.StringIO()

        with redirect_stderr(stderr_capture):
            authenticated, user_name = session.is_authenticated()

        # Should handle gracefully
        assert authenticated is False
        assert user_name is None

        # Should not log anything for this normal case
        stderr_output = stderr_capture.getvalue().strip()
        assert stderr_output == "", "No error messages should be logged when driver is None"

    def test_save_page_state_error_handling(self, session):
        """
        Test that page state saving errors don't propagate unexpectedly.

        Verifies that failures in debug functionality (save_page_state)
        don't interfere with main authentication logic.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        mock_driver.page_source = "<html><body>Test page</body></html>"

        # Mock profile element not found
        mock_driver.find_element.side_effect = NoSuchElementException("Profile element not found")

        stderr_capture = io.StringIO()

        # Mock save_page_state to raise an exception
        with patch.object(session, 'save_page_state', side_effect=Exception("File system error")):
            with redirect_stderr(stderr_capture):
                # This should not crash despite save_page_state failing
                authenticated, user_name = session.is_authenticated()

        # Main authentication logic should still work
        assert authenticated is False
        assert user_name is None

        # May contain error messages, but should not crash
        # The specific handling depends on implementation, but crash should be prevented

    def test_error_message_consistency(self, session):
        """
        Test that error messages follow consistent formatting patterns.

        Verifies that all error messages in the LinkedIn session follow
        a consistent format for professional appearance.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver

        # Test scenarios that should produce consistent error format
        test_scenarios = [
            {
                'name': 'authentication_check',
                'method': lambda: session.is_authenticated(),
                'setup': lambda: setattr(mock_driver, 'page_source', '<html></html>') or
                               setattr(mock_driver, 'find_element', MagicMock(side_effect=NoSuchElementException("Not found")))
            },
            {
                'name': 'job_scraping',
                'method': lambda: session.scrape_jobs(show_all=True),
                'setup': lambda: (
                    setattr(mock_driver, 'page_source', '<html></html>'),
                    setattr(mock_driver, 'find_elements', MagicMock(return_value=[])),
                    setattr(mock_driver, 'find_element', MagicMock(side_effect=NoSuchElementException("Button not found")))
                )
            }
        ]

        error_messages = []

        for scenario in test_scenarios:
            scenario['setup']()

            stderr_capture = io.StringIO()

            with patch.object(session, 'save_page_state'):
                with redirect_stderr(stderr_capture):
                    result = scenario['method']()

            stderr_output = stderr_capture.getvalue().strip()
            if stderr_output:
                error_messages.extend([
                    (scenario['name'], line.strip())
                    for line in stderr_output.split('\n')
                    if line.strip()
                ])

        if error_messages:
            # Check consistency patterns
            for scenario_name, message in error_messages:
                # Should start with consistent prefix
                prefixes = ['Warning:', 'Error:', 'Debug:']
                has_prefix = any(message.startswith(prefix) for prefix in prefixes)
                assert has_prefix, f"Message should have standard prefix: {message}"

                # Should be reasonably concise
                assert len(message) < 300, f"Error message too long: {message}"

                # Should not contain implementation details
                forbidden_terms = ['Traceback', 'File "', 'line ', '.py:', 'Exception:']
                for term in forbidden_terms:
                    assert term not in message, f"Message contains implementation detail '{term}': {message}"


class TestLinkedInExceptionPropagation:
    """Test that appropriate exceptions are propagated while others are handled."""

    @pytest.fixture
    def session(self):
        """Create a LinkedInSession instance for testing."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                return LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=', headless=True)

    def test_critical_exceptions_propagate(self, session):
        """
        Test that critical system exceptions are propagated, not silently handled.

        Verifies that serious errors (like system failures) are not caught
        and hidden by overly broad exception handling.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver

        # Test that critical exceptions are NOT caught
        critical_exceptions = [
            MemoryError("Out of memory"),
            KeyboardInterrupt("User interrupted"),
            SystemExit("System exit requested"),
        ]

        for critical_exception in critical_exceptions:
            mock_driver.page_source = "<html></html>"
            mock_driver.find_element.side_effect = critical_exception

            with patch.object(session, 'save_page_state'):
                # Critical exceptions should propagate, not be caught
                with pytest.raises(type(critical_exception)):
                    session.is_authenticated()

    def test_operational_exceptions_handled(self, session):
        """
        Test that expected operational exceptions are handled gracefully.

        Verifies that normal WebDriver exceptions are caught and handled
        without crashing or producing stack traces.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver

        # These exceptions should be handled gracefully
        operational_exceptions = [
            NoSuchElementException("Element not found"),
            TimeoutException("Timeout waiting for element"),
            WebDriverException("WebDriver error"),
        ]

        for operational_exception in operational_exceptions:
            mock_driver.page_source = "<html></html>"
            mock_driver.find_element.side_effect = operational_exception

            with patch.object(session, 'save_page_state'):
                # Should not raise exception
                authenticated, user_name = session.is_authenticated()

                assert authenticated is False
                assert user_name is None