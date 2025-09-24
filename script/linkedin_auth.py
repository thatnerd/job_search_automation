#!/usr/bin/env python3
"""
LinkedIn Authentication CLI

Usage:
    linkedin_auth.py login [--force-fresh-login] [--headless]
    linkedin_auth.py decrypt-cookies
    linkedin_auth.py (-h | --help)
    linkedin_auth.py --version

Options:
    -h --help              Show this screen.
    --version              Show version.
    --force-fresh-login    Force a new login even if valid cookies exist.
    --headless             Run browser in headless mode (no visible window).

Examples:
    linkedin_auth.py login
    linkedin_auth.py login --force-fresh-login
    linkedin_auth.py decrypt-cookies
"""

import json
import os
import sys
from typing import Any, Dict

from docopt import docopt

# Import from our library
sys.path.insert(0, '.')
from lib.linkedin_session import LinkedInSession


def main() -> None:
    """Main entry point for the LinkedIn authentication script."""
    arguments = docopt(__doc__, version="LinkedIn Auth 1.0")
    
    if arguments["login"]:
        headless = arguments.get("--headless")
        force_fresh = arguments.get("--force-fresh-login")
        
        # Use the LinkedInSession from our library
        session = LinkedInSession(headless=headless)
        
        try:
            success = session.login(force_fresh=force_fresh)
            
            if success:
                print("\n✓ LinkedIn authentication completed successfully!")
                print("Session cookies have been saved and can be reused for future requests.")
            else:
                print("\n✗ LinkedIn authentication failed.")
                sys.exit(1)
        finally:
            # Skip input prompt in test environment
            if not os.getenv("TESTING"):
                input("Hit <enter> to close this session.")
            session.close_session()
    
    elif arguments["decrypt-cookies"]:
        session = LinkedInSession()
        cookie_data = session.decrypt_cookies()
        
        if cookie_data:
            print("\n=== Decrypted Cookie Data ===")
            print(json.dumps(cookie_data, indent=2))
        else:
            print("No cookie file found or unable to decrypt")


if __name__ == "__main__":
    main()
