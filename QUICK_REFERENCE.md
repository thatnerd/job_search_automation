# LinkedIn Job Automation - Quick Reference

## 🚀 Essential Commands

### First Time Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials
cp .env.example .env
# Edit .env with LinkedIn username/password and encryption key

# 3. Initial authentication
python script/linkedin_auth.py login
```

### Daily Usage
```bash
# Scrape jobs with descriptions (recommended)
python script/linkedin_auth.py scrape-jobs --headless --with-descriptions --max-descriptions=5

# View database stats
python script/linkedin_auth.py db-stats

# Search recent jobs
python script/linkedin_auth.py search-jobs "software engineer" --company=Google --limit=10
```

## 📊 Command Quick Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `login` | Authenticate with LinkedIn | `login --force-fresh-login --headless` |
| `scrape-jobs` | Extract job data | `scrape-jobs --headless --with-descriptions` |
| `search-jobs` | Query stored jobs | `search-jobs "python" --min-salary=100000` |
| `db-stats` | Database overview | `db-stats` |
| `decrypt-cookies` | View session info | `decrypt-cookies` |

## 🔍 Search Filters

| Filter | Usage | Example |
|--------|-------|---------|
| Query text | Position argument | `"software engineer"` |
| `--company` | Company name | `--company="Google|Microsoft"` |
| `--location` | Job location | `--location="San Francisco"` |
| `--work-type` | Remote/Hybrid/On-site | `--work-type=Remote` |
| `--min-salary` | Minimum salary | `--min-salary=120000` |
| `--max-salary` | Maximum salary | `--max-salary=180000` |
| `--limit` | Max results | `--limit=50` |

## 🎯 Common Workflows

### Weekly Job Discovery
```bash
# 1. Scrape latest jobs
python script/linkedin_auth.py scrape-jobs --headless --with-descriptions

# 2. View what's new
python script/linkedin_auth.py db-stats

# 3. Search for relevant positions
python script/linkedin_auth.py search-jobs "your keywords" --work-type=Remote --min-salary=100000
```

### Target Company Research
```bash
# Search specific companies
python script/linkedin_auth.py search-jobs --company="Target Company" --limit=20

# Salary research for company
python script/linkedin_auth.py search-jobs --company="Target Company" --min-salary=1 --limit=100
```

### Market Analysis
```bash
# High-paying remote positions
python script/linkedin_auth.py search-jobs --work-type=Remote --min-salary=150000

# Popular companies by job count
python script/linkedin_auth.py db-stats  # See "Top Companies" section

# Recent market activity
python script/linkedin_auth.py search-jobs --limit=100  # Recent jobs
```

## 📁 File Locations

| Path | Contents |
|------|----------|
| `data/database/jobs.db` | Main SQLite database |
| `data/cookies/` | Encrypted session cookies |
| `data/html/` | Debug HTML captures |
| `data/screenshots/` | Debug screenshots |
| `.env` | Configuration and credentials |

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|---------|
| Authentication failed | `rm data/cookies/*.enc && python script/linkedin_auth.py login` |
| Browser crashes | Add `--headless` flag |
| No jobs found | Check LinkedIn manually, may need fresh login |
| Database errors | `sqlite3 data/database/jobs.db "PRAGMA integrity_check;"` |
| Slow scraping | Reduce `--max-descriptions` value |

## ⚡ Performance Tips

- **Use `--headless`** for faster, background scraping
- **Limit descriptions** with `--max-descriptions=3` for speed
- **Scrape incrementally** - database handles duplicates
- **Run during off-peak hours** (early morning/late evening)
- **Clear debug files** periodically: `rm -rf data/html/* data/screenshots/*`

## 🔒 Security Reminders

- Keep `.env` file secure and never commit to version control
- Cookies are encrypted but contain session data
- Use unique, strong LinkedIn password
- Enable 2FA on LinkedIn account
- Respect LinkedIn's rate limits and terms of service

## 📊 Database Schema Quick Reference

### Job Record Structure (JSON)
```json
{
  "job_id": "123456789",
  "title": "Software Engineer",
  "company": "Tech Corp",
  "work_type": "Remote",
  "location": "San Francisco, CA",
  "salary": "$120K/yr - $150K/yr",
  "benefits": "Health, Dental",
  "url": "https://linkedin.com/jobs/view/123456789",
  "description": "Full job description..."
}
```

### Job Status Values
- `active` - Currently available on LinkedIn
- `removed` - No longer found in search results
- `applied` - Manually marked as applied
- `interviewed` - Manually marked as interviewed

### Key Database Tables
- `jobs` - Main job data (JSON + generated columns)
- `scrape_sessions` - Audit trail of scraping runs
- `job_session_mapping` - Links jobs to discovery sessions
- `jobs_fts` - Full-text search index (auto-managed)

---

💡 **Pro Tip**: Run `python script/linkedin_auth.py --help` or any subcommand with `--help` for detailed usage information.