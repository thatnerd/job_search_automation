#!/usr/bin/env python3
"""
LinkedIn Authentication CLI

Usage:
    linkedin_auth.py login [--force-fresh-login] [--headless]
    linkedin_auth.py scrape-jobs [--headless] [--filename=<f>] [--no-database] [--with-descriptions] [--max-descriptions=<n>]
    linkedin_auth.py search-jobs [<query>] [--company=<c>] [--location=<l>] [--work-type=<wt>] [--min-salary=<min>] [--max-salary=<max>] [--limit=<n>]
    linkedin_auth.py db-stats
    linkedin_auth.py decrypt-cookies
    linkedin_auth.py (-h | --help)
    linkedin_auth.py --version

Options:
    -h --help               Show this screen.
    --version               Show version.
    --force-fresh-login     Force a new login even if valid cookies exist.
    --headless              Run browser in headless mode (no visible window).
    --filename=<f>          Custom filename for job data (optional).
    --no-database           Skip database storage, only save to JSON file.
    --with-descriptions     Extract full job descriptions (slower, visits individual job pages).
    --max-descriptions=<n>  Maximum number of job descriptions to extract [default: 5].
    --company=<c>           Filter by company name.
    --location=<l>          Filter by location.
    --work-type=<wt>        Filter by work type (Remote, Hybrid, On-site).
    --min-salary=<min>      Minimum yearly salary (integer).
    --max-salary=<max>      Maximum yearly salary (integer).
    --limit=<n>             Maximum number of results [default: 100].

Examples:
    linkedin_auth.py login
    linkedin_auth.py login --force-fresh-login
    linkedin_auth.py scrape-jobs
    linkedin_auth.py scrape-jobs --headless --filename=my_jobs.json
    linkedin_auth.py scrape-jobs --no-database  # Skip database, JSON only
    linkedin_auth.py scrape-jobs --with-descriptions --max-descriptions=3  # Extract full job descriptions
    linkedin_auth.py search-jobs "software engineer" --company=Google --work-type=Remote
    linkedin_auth.py search-jobs --min-salary=100000 --max-salary=200000
    linkedin_auth.py db-stats
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
    
    elif arguments["scrape-jobs"]:
        headless = arguments.get("--headless")
        filename = arguments.get("--filename")
        use_database = not arguments.get("--no-database")
        with_descriptions = arguments.get("--with-descriptions")
        max_descriptions = int(arguments.get("--max-descriptions", 5))

        # Use the LinkedInSession from our library
        session = LinkedInSession(headless=headless, enable_database=use_database)

        try:
            # First login (will use existing cookies if valid)
            print("Authenticating with LinkedIn...")
            success = session.login(force_fresh=False)

            if not success:
                print("\n✗ LinkedIn authentication failed. Cannot scrape jobs.")
                sys.exit(1)

            if use_database:
                # Scrape jobs and store in database
                print("\n=== Scraping LinkedIn Jobs ===")

                if with_descriptions:
                    # Use the method that extracts full job descriptions
                    jobs, session_id, new_jobs, updated_jobs = session.scrape_jobs_with_descriptions_to_database(
                        show_all=True, max_descriptions=max_descriptions
                    )
                else:
                    # Standard scraping without descriptions
                    jobs, session_id, new_jobs, updated_jobs = session.scrape_jobs_to_database(show_all=True)

                if filename:
                    # Also save to JSON if filename specified
                    saved_file = session.save_jobs_to_file(jobs, filename)
                    print(f"✓ Saved {len(jobs)} jobs to: {saved_file}")

                print(f"✓ Job scraping completed successfully!")
                print(f"Found {len(jobs)} jobs in database (Session ID: {session_id})")

            else:
                # Legacy mode: only save to JSON
                print("\n=== Scraping LinkedIn Jobs ===")
                jobs = session.scrape_jobs(show_all=True)

                if with_descriptions:
                    print("⚠ Description extraction requires database mode. Use without --no-database flag.")

                if jobs:
                    # Save to file
                    saved_file = session.save_jobs_to_file(jobs, filename)
                    print(f"\n✓ Job scraping completed successfully!")
                    print(f"Found {len(jobs)} jobs and saved to: {saved_file}")
                else:
                    print("\n⚠ No jobs found. Check page structure or authentication.")

        except Exception as e:
            print(f"\n✗ Error during job scraping: {e}")
            sys.exit(1)
        finally:
            # Skip input prompt in test environment
            if not os.getenv("TESTING"):
                input("Hit <enter> to close this session.")
            session.close_session()

    elif arguments["search-jobs"]:
        from lib.job_database import JobDatabase

        query = arguments.get("<query>")
        company = arguments.get("--company")
        location = arguments.get("--location")
        work_type = arguments.get("--work-type")
        min_salary = arguments.get("--min-salary")
        max_salary = arguments.get("--max-salary")
        limit = int(arguments.get("--limit", 100))

        # Convert salary strings to integers if provided
        if min_salary:
            try:
                min_salary = int(min_salary)
            except ValueError:
                print("Error: --min-salary must be an integer")
                sys.exit(1)

        if max_salary:
            try:
                max_salary = int(max_salary)
            except ValueError:
                print("Error: --max-salary must be an integer")
                sys.exit(1)

        try:
            database = JobDatabase()
            jobs = database.search_jobs(
                query=query,
                company=company,
                location=location,
                work_type=work_type,
                min_salary=min_salary,
                max_salary=max_salary,
                limit=limit
            )

            print(f"\n=== Found {len(jobs)} matching jobs ===")
            for job in jobs:
                print(f"\nJob ID: {job['job_id']}")
                print(f"Title: {job['title']}")
                print(f"Company: {job['company']}")
                if job['work_type']:
                    print(f"Work Type: {job['work_type']}")
                if job['location']:
                    print(f"Location: {job['location']}")
                if job['salary']:
                    print(f"Salary: {job['salary']}")
                    if job['salary_min_yearly'] and job['salary_max_yearly']:
                        print(f"Parsed Salary: ${job['salary_min_yearly']:,} - ${job['salary_max_yearly']:,}")
                print(f"Status: {job['status']}")
                print(f"First Seen: {job['first_seen']}")
                print(f"URL: {job['url']}")
                print("-" * 50)

        except Exception as e:
            print(f"Error searching jobs: {e}")
            sys.exit(1)

    elif arguments["db-stats"]:
        from lib.job_database import JobDatabase

        try:
            database = JobDatabase()
            stats = database.get_stats()

            print("\n=== Database Statistics ===")
            print(f"Total Jobs: {stats['total_jobs']}")
            print(f"Active Jobs: {stats['active_jobs']}")
            print(f"Jobs Seen (Last 7 days): {stats['jobs_seen_last_7_days']}")
            print(f"Total Scrape Sessions: {stats['total_sessions']}")

            print(f"\nJobs by Status:")
            for status, count in stats['jobs_by_status'].items():
                print(f"  {status}: {count}")

            print(f"\nWork Types:")
            for work_type, count in stats['work_types'].items():
                print(f"  {work_type}: {count}")

            print(f"\nTop Companies:")
            for company, count in stats['top_companies'].items():
                print(f"  {company}: {count}")

        except Exception as e:
            print(f"Error getting database stats: {e}")
            sys.exit(1)

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
