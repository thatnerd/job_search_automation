# JSON Schema Migration Test Plan

This document outlines the comprehensive test suite for migrating from structured columns to JSON-based storage with generated columns.

## Test Coverage Overview

### 1. Schema Creation Tests (`test_job_database_json_schema.py`)
- **Fresh database JSON schema creation**
- **Generated column definitions and extraction**
- **Index creation (job_id and location only)**
- **JSON field validation and error handling**
- **Salary parsing with generated INTEGER columns**
- **NULL/missing field handling**

#### Key Test Classes:
- `TestJSONSchemaCreation` - Schema structure validation
- `TestJSONFieldValidation` - JSON data validation
- `TestSalaryParsingGeneratedColumns` - Salary parsing to INTEGER columns

### 2. JobRecord Conversion Tests (`test_job_database_json_schema.py`)
- **JobRecord to JSON dictionary conversion**
- **JSON dictionary to JobRecord creation**
- **Bidirectional conversion (roundtrip)**
- **Default value handling**
- **Missing field graceful handling**

#### Key Test Class:
- `TestJobRecordJSONConversion` - Data model conversions

### 3. Database Operations Tests (`test_job_database_json_operations.py`)
- **Upsert operations with JSON storage**
- **Search functionality with generated columns**
- **Data retrieval from JSON backend**
- **Session mapping with JSON storage**
- **FTS integration with generated columns**

#### Key Test Classes:
- `TestJSONUpsertOperations` - Insert/update operations
- `TestJSONSearchOperations` - Search with generated columns
- `TestJSONRetrievalOperations` - Data retrieval and formatting

### 4. Migration Tests (`test_job_database_json_migration.py`)
- **Fresh database creation with JSON schema**
- **Migration from existing column-based schema**
- **Data preservation during migration**
- **Backup and rollback capabilities**
- **Migration safety checks**

#### Key Test Classes:
- `TestFreshDatabaseCreation` - New database setup
- `TestDatabaseMigrationPreparation` - Migration planning
- `TestDataPreservationDuringMigration` - Data integrity

### 5. Integration Tests (`test_job_database_json_integration.py`)
- **End-to-end scraping workflow**
- **Complete job lifecycle management**
- **Performance testing with JSON backend**
- **Data export from JSON storage**
- **Bulk operations performance**

#### Key Test Classes:
- `TestEndToEndJobScrapeWorkflow` - Complete workflows
- `TestPerformanceWithJSONBackend` - Performance validation

## Implementation Requirements

Based on these tests, the following methods need to be implemented:

### JobRecord Class Additions
```python
def to_json_dict(self) -> Dict[str, Any]:
    """Convert JobRecord to JSON dictionary."""

@classmethod
def from_json_dict(cls, json_data: Dict[str, Any]) -> 'JobRecord':
    """Create JobRecord from JSON dictionary."""
```

### JobDatabase Class Additions
```python
def detect_schema_type(self) -> str:
    """Detect if database uses column-based or JSON schema."""

def create_migration_backup(self) -> bool:
    """Create backup before migration."""

def validate_migration_safety(self) -> Dict[str, Any]:
    """Validate conditions for safe migration."""

def migrate_to_json_schema(self) -> Dict[str, Any]:
    """Migrate existing database to JSON schema."""

def rollback_migration(self) -> Dict[str, Any]:
    """Rollback failed migration."""

def export_jobs_csv(self, filters: Dict = None) -> str:
    """Export jobs to CSV format."""

def export_jobs_json(self, filters: Dict = None) -> str:
    """Export jobs to JSON format."""

def upsert_job(self, job: JobRecord, preserve_existing: bool = False,
               session_id: int = None, position: int = None) -> Tuple[bool, bool]:
    """Updated to support preserve_existing flag for partial updates."""
```

## Database Schema Changes

### New Table Structure
```sql
CREATE TABLE jobs (
    -- Primary JSON storage
    json_data TEXT NOT NULL,

    -- Generated columns from JSON
    job_id TEXT GENERATED ALWAYS AS (json_data->>'$.job_id') STORED,
    title TEXT GENERATED ALWAYS AS (json_data->>'$.title') STORED,
    company TEXT GENERATED ALWAYS AS (json_data->>'$.company') STORED,
    work_type TEXT GENERATED ALWAYS AS (json_data->>'$.work_type') STORED,
    location TEXT GENERATED ALWAYS AS (json_data->>'$.location') STORED,
    salary TEXT GENERATED ALWAYS AS (json_data->>'$.salary') STORED,
    benefits TEXT GENERATED ALWAYS AS (json_data->>'$.benefits') STORED,
    url TEXT GENERATED ALWAYS AS (json_data->>'$.url') STORED,
    description TEXT GENERATED ALWAYS AS (json_data->>'$.description') STORED,
    status TEXT GENERATED ALWAYS AS (json_data->>'$.status') STORED,
    source TEXT GENERATED ALWAYS AS (json_data->>'$.source') STORED,

    -- Generated salary parsing columns
    salary_min_yearly INTEGER GENERATED ALWAYS AS (
        CAST(REPLACE(REPLACE(SUBSTR(salary, INSTR(salary, '$') + 1,
             CASE WHEN INSTR(salary, ' - ') > 0
                  THEN INSTR(salary, ' - ') - INSTR(salary, '$') - 1
                  ELSE INSTR(salary, 'K/yr') - INSTR(salary, '$') - 1 END), 'K', '000'), ',', '') AS INTEGER)
        WHERE salary GLOB '$*K/yr*'
    ) STORED,

    salary_max_yearly INTEGER GENERATED ALWAYS AS (
        CASE WHEN INSTR(salary, ' - ') > 0 THEN
            CAST(REPLACE(REPLACE(SUBSTR(salary, INSTR(salary, ' - ') + 3,
                 INSTR(salary, 'K/yr', INSTR(salary, ' - ')) - INSTR(salary, ' - ') - 3), 'K', '000'), ',', '') AS INTEGER)
        ELSE
            CAST(REPLACE(REPLACE(SUBSTR(salary, INSTR(salary, '$') + 1,
                 INSTR(salary, 'K/yr') - INSTR(salary, '$') - 1), 'K', '000'), ',', '') AS INTEGER)
        END
        WHERE salary GLOB '$*K/yr*'
    ) STORED,

    -- Timestamp columns (not generated)
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (job_id)
);
```

### Indexes (Simplified)
```sql
CREATE INDEX idx_jobs_job_id ON jobs (job_id);
CREATE INDEX idx_jobs_location ON jobs (location);
```

## Running the Tests

```bash
# Run all JSON schema tests
pytest test/test_job_database_json_schema.py -v

# Run database operations tests
pytest test/test_job_database_json_operations.py -v

# Run migration tests
pytest test/test_job_database_json_migration.py -v

# Run integration tests
pytest test/test_job_database_json_integration.py -v

# Run all JSON-related tests
pytest test/test_job_database_json*.py -v --cov=lib --cov=script
```

## Test Data Examples

### Sample JSON Structure
```json
{
  "job_id": "123456",
  "title": "Senior Python Developer",
  "company": "TechCorp Inc",
  "work_type": "Remote",
  "location": "San Francisco, CA",
  "salary": "$120K/yr - $150K/yr",
  "benefits": "Health, Dental, Vision, 401k",
  "url": "https://example.com/job/123456",
  "description": "Build amazing Python applications...",
  "status": "active",
  "source": "linkedin"
}
```

### Expected Generated Column Values
- `salary_min_yearly`: 120000
- `salary_max_yearly`: 150000
- All other fields extracted directly from JSON

## Benefits of This Approach

1. **Flexible Schema**: Easy to add new fields without migration
2. **Maintained Performance**: Generated columns provide indexing
3. **Simplified Indexing**: Only essential indexes (job_id, location)
4. **Data Integrity**: JSON validation ensures consistent structure
5. **Easy Export**: JSON data readily available for export
6. **Future-Proof**: Schema can evolve without breaking changes

These tests provide comprehensive validation of the JSON-based schema transition while ensuring the external API remains consistent and performant.