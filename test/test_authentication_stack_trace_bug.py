"""
Specific test for the authentication stack trace bug.

This test targets the exact issue on line 300 of linkedin_session.py:
    print(f"Debug: Profile element not found (may be normal): {e}", file=sys.stderr)

The problem is that printing the full exception 'e' includes stack trace information
that clutters stderr output, even though the exception is being handled gracefully.

This test will FAIL initially and PASS after the fix.
"""

import pytest
import sys
import io
from contextlib import redirect_stderr
from unittest.mock import patch, MagicMock
from selenium.common.exceptions import NoSuchElementException

# Add project root to path
sys.path.insert(0, '.')
from lib.linkedin_session import LinkedInSession


class TestAuthenticationStackTraceBug:
    """Test the specific authentication stack trace logging issue."""

    @pytest.fixture
    def session(self):
        """Create a LinkedInSession instance for testing."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                return LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=', headless=True)

    def test_authentication_exception_logging_format(self, session):
        """
        Test the exact format of exception logging in is_authenticated method.

        This test exposes the bug where the full exception object is logged,
        which includes verbose stack trace information that clutters stderr.

        EXPECTED TO FAIL initially due to line 300:
        print(f"Debug: Profile element not found (may be normal): {e}", file=sys.stderr)
        """
        mock_driver = MagicMock()
        session.driver = mock_driver

        # Mock page without authentication indicators
        mock_driver.page_source = "<html><body>Login page</body></html>"

        # Create a realistic NoSuchElementException with typical Selenium message
        realistic_exception = NoSuchElementException(
            'Message: no such element: Unable to locate element: '
            '{"method":"css selector","selector":"[data-control-name=\'nav.settings_signout\']"}\n'
            '  (Session info: chrome=120.0.6099.109)\n'
            '  (Driver info: chromedriver=120.0.6099.109 '
            '(968205e8ba2ebbcc88f30c8c1d5f74d3a3cfc7e6-refs/branch-heads/6099@{#1333}),platform=Mac OS X 10.15.7 x86_64)'
        )

        mock_driver.find_element.side_effect = realistic_exception

        # Capture stderr to examine what gets logged
        stderr_capture = io.StringIO()

        with patch.object(session, 'save_page_state'):
            with redirect_stderr(stderr_capture):
                authenticated, user_name = session.is_authenticated()

        # Authentication should fail gracefully
        assert authenticated is False
        assert user_name is None

        # Analyze stderr content
        stderr_output = stderr_capture.getvalue()
        assert stderr_output.strip() != "", "Should log debug information"

        # The BUG: Current implementation logs the full exception
        # This will FAIL initially because line 300 prints the full exception object
        lines = stderr_output.strip().split('\n')

        # After the fix, should have exactly one clean debug line
        # WILL FAIL initially - current code includes verbose exception details
        assert len(lines) == 1, f"Expected single debug line, got {len(lines)} lines: {lines}"

        debug_line = lines[0].strip()

        # Should start with expected prefix
        assert debug_line.startswith("Debug: Profile element not found (may be normal)"), \
            f"Unexpected debug line format: {debug_line}"

        # The BUG: Should NOT contain verbose exception details after the colon
        # WILL FAIL initially due to ': {e}' in the print statement
        verbose_indicators = [
            'Message: no such element',
            'Unable to locate element',
            'Session info:',
            'Driver info:',
            'chromedriver=',
            'chrome=',
            '{"method":"css selector"',
            'platform=Mac OS X'
        ]

        for indicator in verbose_indicators:
            assert indicator not in debug_line, \
                f"Debug line contains verbose exception details '{indicator}': {debug_line}"

        # After fix, debug line should be concise (under 100 characters)
        # WILL FAIL initially due to verbose exception being included
        assert len(debug_line) < 100, \
            f"Debug line too verbose ({len(debug_line)} chars): {debug_line}"

    def test_clean_authentication_debug_message_format(self, session):
        """
        Test what the authentication debug message SHOULD look like after the fix.

        This test defines the expected behavior: a clean, informative debug message
        without verbose exception details cluttering the output.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        mock_driver.page_source = "<html><body>Test page</body></html>"

        # Any NoSuchElementException should produce clean debug output
        mock_driver.find_element.side_effect = NoSuchElementException(
            "Extremely verbose selenium exception with session info and driver details"
        )

        stderr_capture = io.StringIO()

        with patch.object(session, 'save_page_state'):
            with redirect_stderr(stderr_capture):
                session.is_authenticated()

        stderr_output = stderr_capture.getvalue().strip()

        # Expected format after fix:
        expected_patterns = [
            "Debug: Profile element not found (may be normal)",
            # Should be brief and informative, not include full exception
        ]

        # Should match one of the expected patterns
        matches_expected = any(pattern in stderr_output for pattern in expected_patterns)
        assert matches_expected, f"Debug message doesn't match expected format: {stderr_output}"

        # Should be a single line
        lines = [line.strip() for line in stderr_output.split('\n') if line.strip()]
        assert len(lines) == 1, f"Should be single debug line: {lines}"

        # Should be reasonably short
        assert len(stderr_output) < 100, f"Debug message too long: {stderr_output}"

    def test_multiple_authentication_attempts_clean_output(self, session):
        """
        Test that multiple authentication attempts don't accumulate verbose output.

        Verifies that the logging issue doesn't compound when authentication
        is checked multiple times in a session.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        mock_driver.page_source = "<html><body>Test page</body></html>"

        # Mock different exception messages for each attempt
        exceptions = [
            NoSuchElementException("First attempt - detailed selenium error with driver info"),
            NoSuchElementException("Second attempt - different detailed error message"),
            NoSuchElementException("Third attempt - yet another verbose selenium exception")
        ]

        all_stderr_output = []

        for i, exception in enumerate(exceptions):
            mock_driver.find_element.side_effect = exception
            stderr_capture = io.StringIO()

            with patch.object(session, 'save_page_state'):
                with redirect_stderr(stderr_capture):
                    session.is_authenticated()

            stderr_output = stderr_capture.getvalue().strip()
            all_stderr_output.append(stderr_output)

        # Each attempt should produce consistent, clean output
        for i, output in enumerate(all_stderr_output):
            # Should have output for each attempt
            assert output.strip() != "", f"Attempt {i+1} should log debug info"

            # Each should be single line after fix
            lines = [line.strip() for line in output.split('\n') if line.strip()]
            # WILL FAIL initially due to verbose exception logging
            assert len(lines) == 1, f"Attempt {i+1} should have single debug line: {lines}"

            # Should be consistently brief
            # WILL FAIL initially due to verbose exception details
            assert len(output) < 150, f"Attempt {i+1} debug message too long: {output}"

    def test_specific_line_300_bug_reproduction(self, session):
        """
        Test that reproduces the exact bug from line 300 of linkedin_session.py.

        Line 300: print(f"Debug: Profile element not found (may be normal): {e}", file=sys.stderr)

        The issue is that {e} includes the full exception object with all its verbose details.
        This test confirms that the current implementation has this issue.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        mock_driver.page_source = "<html><body>Login page</body></html>"

        # Create exception with identifiable content that would appear in {e}
        test_exception = NoSuchElementException("TEST_EXCEPTION_MARKER_12345")
        mock_driver.find_element.side_effect = test_exception

        stderr_capture = io.StringIO()

        with patch.object(session, 'save_page_state'):
            with redirect_stderr(stderr_capture):
                session.is_authenticated()

        stderr_output = stderr_capture.getvalue()

        # Confirm the current bug exists
        # WILL FAIL initially - the exception marker should appear in output due to {e}
        # After fix, this marker should NOT appear (only a clean debug message)
        assert "TEST_EXCEPTION_MARKER_12345" not in stderr_output, \
            f"Exception details leaked into stderr: {stderr_output}"

        # Should contain the expected debug prefix
        assert "Debug: Profile element not found (may be normal)" in stderr_output

        # But NOT the specific exception message after fix
        # WILL FAIL initially because current code includes ': {e}'


class TestAuthenticationDebugMessageFix:
    """Test the correct implementation after fixing the authentication debug message."""

    @pytest.fixture
    def session(self):
        """Create a LinkedInSession instance for testing."""
        with patch('lib.linkedin_session.load_dotenv'):
            with patch('lib.linkedin_session.Path.mkdir'):
                return LinkedInSession(encryption_key='rqKVCgpWxjqjdOddPVxft-kLK6oOkecU029UGm_kUFs=', headless=True)

    def test_proposed_fix_behavior(self, session):
        """
        Test the expected behavior after fixing line 300.

        The fix should change:
        FROM: print(f"Debug: Profile element not found (may be normal): {e}", file=sys.stderr)
        TO:   print("Debug: Profile element not found (may be normal)", file=sys.stderr)

        This removes the verbose exception details while preserving the informative debug message.
        """
        mock_driver = MagicMock()
        session.driver = mock_driver
        mock_driver.page_source = "<html><body>Test</body></html>"

        # Any exception should produce the same clean debug output after fix
        mock_driver.find_element.side_effect = NoSuchElementException(
            "Very long verbose selenium exception with tons of details that shouldn't appear in output"
        )

        stderr_capture = io.StringIO()

        with patch.object(session, 'save_page_state'):
            with redirect_stderr(stderr_capture):
                session.is_authenticated()

        stderr_output = stderr_capture.getvalue().strip()

        # After fix: Should be exactly this clean message
        expected_message = "Debug: Profile element not found (may be normal)"
        assert stderr_output == expected_message, \
            f"Expected clean debug message, got: {stderr_output}"