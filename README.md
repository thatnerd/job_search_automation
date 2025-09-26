# LinkedIn Job Search Automation

A Python-based automation tool for scraping, storing, and analyzing job postings from LinkedIn. The application provides secure session management, comprehensive job data extraction, and powerful search capabilities through a SQLite database with JSON-based storage.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Chrome browser (for web automation)
- LinkedIn account credentials

### Installation

1. **Clone and setup environment:**
   ```bash
   git clone <repository-url>
   cd job_search_automation

   # Using direnv (recommended)
   direnv allow

   # Or manual setup
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your LinkedIn credentials and encryption key
   ```

3. **Generate encryption key:**
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

4. **First run - authenticate with LinkedIn:**
   ```bash
   python script/linkedin_auth.py login
   ```

## 📋 Core Commands

### Authentication
```bash
# Standard login (reuses existing session if valid)
python script/linkedin_auth.py login

# Force fresh login (ignores cached session)
python script/linkedin_auth.py login --force-fresh-login --headless

# View stored session cookies
python script/linkedin_auth.py decrypt-cookies
```

### Job Scraping
```bash
# Basic job scraping with database storage
python script/linkedin_auth.py scrape-jobs

# Headless scraping with job descriptions
python script/linkedin_auth.py scrape-jobs --headless --with-descriptions --max-descriptions=10

# Save to custom file without database
python script/linkedin_auth.py scrape-jobs --filename=my_jobs.json --no-database

# Complete example with all options
python script/linkedin_auth.py scrape-jobs --headless --filename=jobs.json --with-descriptions --max-descriptions=5
```

### Database Operations
```bash
# View database statistics
python script/linkedin_auth.py db-stats

# Search jobs by criteria
python script/linkedin_auth.py search-jobs "software engineer" --company=Google --work-type=Remote
python script/linkedin_auth.py search-jobs --min-salary=100000 --max-salary=200000 --location="San Francisco"
python script/linkedin_auth.py search-jobs --company=Microsoft --limit=10
```

## 🎯 Features

### 🔐 Secure Authentication
- **Encrypted session storage** using Fernet encryption
- **30-day cookie persistence** with automatic expiry
- **2FA support** with interactive prompts
- **Device recognition** through "Remember this browser" functionality
- **macOS integration** with automatic terminal focus management

### 📊 Comprehensive Data Extraction
- **Basic job information**: Title, company, location, work type, salary
- **Full job descriptions** with configurable extraction limits
- **Benefits and additional details** when available
- **LinkedIn job URLs** for direct access
- **JSON-based storage** preserving complete extracted data

### 🗄️ Advanced Database Features
- **SQLite database** with automatic schema management
- **JSON-first storage** with generated columns for performance
- **Full-text search** across job titles, companies, and descriptions
- **Salary parsing** with automatic min/max extraction
- **Job lifecycle tracking** (active, removed, applied, interviewed)
- **Session audit trail** with scraping statistics

### 🔍 Powerful Search Capabilities
- **Multi-criteria filtering** by company, location, work type, salary
- **Flexible text search** across all job fields
- **Date-based queries** (jobs seen in last N days)
- **Status-based filtering** (active, removed, etc.)
- **Results limiting** and pagination support

## 📁 Project Structure

```
job_search_automation/
├── script/                    # Executable CLI scripts
│   └── linkedin_auth.py      # Main application entry point
├── lib/                      # Core library modules
│   ├── linkedin_session.py  # LinkedIn automation & scraping
│   └── job_database.py      # Database operations & search
├── test/                     # Comprehensive test suite
├── data/                     # Data storage (auto-created)
│   ├── cookies/             # Encrypted session cookies
│   ├── database/            # SQLite database files
│   ├── test_data/           # Test fixtures
│   ├── html/               # Debug HTML captures
│   └── screenshots/         # Debug screenshots
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
└── CLAUDE.md               # Development guidelines
```

## 💾 Database Schema

### JSON-First Storage
The application uses a hybrid approach with JSON as the primary storage format and generated columns for performance:

```sql
-- Primary storage
json_data TEXT NOT NULL  -- Complete job data as JSON

-- Generated columns (automatically computed)
job_id TEXT GENERATED ALWAYS AS (json_data->>'$.job_id') STORED UNIQUE
title TEXT GENERATED ALWAYS AS (json_data->>'$.title') STORED
company TEXT GENERATED ALWAYS AS (json_data->>'$.company') STORED
location TEXT GENERATED ALWAYS AS (json_data->>'$.location') STORED
salary TEXT GENERATED ALWAYS AS (json_data->>'$.salary') STORED

-- Automatic salary parsing
salary_min_yearly INTEGER GENERATED ALWAYS AS (...) STORED
salary_max_yearly INTEGER GENERATED ALWAYS AS (...) STORED
```

### JSON Data Format
```json
{
  "job_id": "4158216146",
  "title": "Software Engineer",
  "company": "Tech Corp",
  "work_type": "Remote",
  "location": "San Francisco, CA",
  "salary": "$120K/yr - $150K/yr",
  "benefits": "Health, Dental, Vision",
  "url": "https://linkedin.com/jobs/view/4158216146/...",
  "description": "Full job description text..."
}
```

### Audit Trail
- **Scraping sessions** with timestamps and statistics
- **Job-session mappings** tracking discovery sessions
- **Change detection** with automatic data comparison
- **Full-text search** integration with automatic updates

## 🔍 Search Examples

### Basic Searches
```bash
# Find all remote software engineering jobs
python script/linkedin_auth.py search-jobs "software engineer" --work-type=Remote

# Jobs at specific companies
python script/linkedin_auth.py search-jobs --company="Google|Microsoft|Apple"

# High-paying jobs in tech hubs
python script/linkedin_auth.py search-jobs --min-salary=150000 --location="San Francisco|New York|Seattle"
```

### Advanced Filtering
```bash
# Recently discovered jobs (last 7 days) at startups
python script/linkedin_auth.py search-jobs startup --limit=20

# Full-text search in job descriptions
python script/linkedin_auth.py search-jobs "machine learning" --limit=50

# Salary range filtering
python script/linkedin_auth.py search-jobs --min-salary=100000 --max-salary=180000 --work-type=Hybrid
```

## 🛠️ Configuration Options

### Environment Variables (.env)
```bash
# LinkedIn credentials
LINKEDIN_USERNAME=your.email@domain.com
LINKEDIN_PASSWORD=your_secure_password

# Encryption key (generate with command above)
ENCRYPTION_KEY=your_fernet_encryption_key

# Optional: Browser settings
CHROME_BINARY_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
```

### Command Line Options

#### Scraping Options
- `--headless`: Run browser without visible window
- `--filename=<file>`: Custom output filename
- `--no-database`: Skip database storage, save to JSON only
- `--with-descriptions`: Extract full job descriptions (slower)
- `--max-descriptions=<n>`: Limit description extraction (default: 5)

#### Search Options
- `--company=<name>`: Filter by company name
- `--location=<location>`: Filter by job location
- `--work-type=<type>`: Filter by work type (Remote, Hybrid, On-site)
- `--min-salary=<amount>`: Minimum yearly salary filter
- `--max-salary=<amount>`: Maximum yearly salary filter
- `--limit=<n>`: Maximum number of results (default: 100)

## 📈 Database Statistics

The `db-stats` command provides comprehensive insights:

```bash
python script/linkedin_auth.py db-stats
```

**Sample Output:**
```
=== Database Statistics ===
Total Jobs: 1,247
Active Jobs: 892
Jobs Seen (Last 7 days): 156
Total Scrape Sessions: 23

Jobs by Status:
  active: 892
  removed: 298
  applied: 45
  interviewed: 12

Work Types:
  Remote: 445
  Hybrid: 321
  On-site: 126
  Unknown: 355

Top Companies:
  Google: 34
  Microsoft: 28
  Apple: 22
  Amazon: 19
  Meta: 15
```

## 🔄 Job Lifecycle Management

### Status Tracking
- **`active`**: Currently available on LinkedIn
- **`removed`**: No longer found in search results
- **`applied`**: Manually marked as applied
- **`interviewed`**: Manually marked as interviewed

### Automatic Updates
When re-running scrapes, existing jobs are:
1. **Data comparison**: JSON data checked for changes
2. **Timestamp updates**: `last_seen` always updated
3. **Change detection**: Modified jobs marked as updated
4. **Removal detection**: Missing jobs marked as removed

## 🚨 Error Handling & Debugging

### Debug Information
The application automatically captures debug information:
- **Screenshots** saved to `data/screenshots/` on errors
- **HTML snapshots** saved to `data/html/` for analysis
- **Automatic cleanup** of old debug files (10+ files)

### Common Issues

#### Authentication Problems
```bash
# Clear cached cookies and re-authenticate
rm data/cookies/linkedin_session.json.enc
python script/linkedin_auth.py login --force-fresh-login
```

#### Browser Issues
```bash
# Test headless mode
python script/linkedin_auth.py login --headless

# Check Chrome installation
which google-chrome-stable
```

#### Database Issues
```bash
# Check database integrity
sqlite3 data/database/jobs.db "PRAGMA integrity_check;"

# View recent errors
tail -f ~/.local/share/claude_code/logs/error.log
```

## 🧪 Testing & Development

### Running Tests
```bash
# Run all tests
pytest test/

# Run with coverage
pytest test/ --cov=lib --cov=script

# Run specific test categories
pytest test/test_linkedin_session_*.py -v
```

### Development Commands
```bash
# Code formatting
black script/ lib/ test/

# Linting
ruff check script/ lib/ test/

# Type checking
mypy script/ lib/ test/
```

## 🔒 Security & Privacy

### Data Protection
- **Encrypted cookie storage** using industry-standard Fernet encryption
- **No plaintext credentials** stored on disk
- **Local data processing** - no external API calls
- **Secure session management** with automatic expiry

### Rate Limiting
- **Respectful scraping** with built-in delays
- **Configurable limits** for description extraction
- **Session-based throttling** to avoid detection

### Privacy Compliance
- **Personal use only** - respect LinkedIn's terms of service
- **No data sharing** - all data remains local
- **User consent** - explicit authentication required

## 📞 Support & Troubleshooting

### Getting Help
1. Check the **error logs** in debug output
2. Review **captured screenshots** and HTML files
3. Run with `--headless=false` to see browser interaction
4. Use `decrypt-cookies` to verify session status

### Performance Optimization
- Use `--headless` for faster scraping
- Limit `--max-descriptions` to reduce processing time
- Run during off-peak hours for better success rates
- Clear old debug files periodically

### Best Practices
- **Authenticate once** and reuse sessions (30-day expiry)
- **Scrape incrementally** - the database handles duplicates
- **Monitor database stats** to track progress
- **Backup database** before major changes

---

## 📄 License & Disclaimer

This tool is for educational and personal use only. Users are responsible for complying with LinkedIn's Terms of Service and applicable laws. The authors assume no liability for misuse of this software.

**Remember**: Always respect rate limits and use this tool responsibly.