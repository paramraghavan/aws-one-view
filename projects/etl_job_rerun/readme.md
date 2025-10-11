# Data Ingestion Job Rerun Tool

A Flask-based web application for rerunning failed data ingestion jobs from S3 with configurable cleanup hooks and AWS
profile-based bucket mappings.

## Features

- **AWS Profile Management**: Configure source/destination buckets per AWS profile in `env_config.py`
- **Date Range Filtering**: Specify start/end dates or ingest all data
- **Pickle File Caching**: Cache S3 data for quick re-queries
- **Entity Configuration**: Map source entities to target staging paths
- **Cleanup Hooks**: Execute pre-copy cleanup actions (Snowflake, pass-through, custom scripts)
- **Batch Copy Operations**: Copy multiple files to staging with progress tracking
- **Integrated Workflow**: Query, filter, and copy all in one streamlined interface

## Project Structure

```
job-rerun-tool/
├── app.py                      # Main Flask application
├── cleanup_hooks.py            # Cleanup hook manager
├── env_config.py              # AWS profile to bucket mappings ⭐ NEW
├── entity_config.json         # Entity and cleanup configuration
├── requirements.txt           # Python dependencies
├── start.sh                   # Quick start script
├── README.md                  # Documentation
├── templates/
│   └── index.html            # Web UI
├── pickle_files/             # Auto-created for pickle storage
└── cleanup_scripts/          # Optional custom cleanup scripts
```

## Installation

### 1. Create Project Directory

```bash
mkdir job-rerun-tool
cd job-rerun-tool
mkdir templates
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure AWS Credentials

Ensure your AWS profiles are configured in `~/.aws/credentials`:

```ini
[production]
aws_access_key_id = YOUR_KEY
aws_secret_access_key = YOUR_SECRET
region = us-east-1

[staging]
aws_access_key_id = YOUR_KEY
aws_secret_access_key = YOUR_SECRET
region = us-west-2
```

## Configuration

### AWS Profile to Bucket Mapping (env_config.py) ⭐ IMPORTANT

Edit `env_config.py` to map your AWS profiles to their respective source and destination buckets:

```python
AWS_PROFILE_CONFIG = {
    "production": {
        "source_bucket": "s3://prod-source-bucket",
        "destination_bucket": "s3://prod-destination-bucket",
        "description": "Production environment"
    },
    "staging": {
        "source_bucket": "s3://staging-source-bucket",
        "destination_bucket": "s3://staging-destination-bucket",
        "description": "Staging environment"
    },
    "development": {
        "source_bucket": "s3://dev-source-bucket",
        "destination_bucket": "s3://dev-destination-bucket",
        "description": "Development environment"
    }
}
```

**How it works:**

1. When you select an AWS profile, the tool automatically loads the configured buckets
2. The UI displays the source and destination buckets for verification
3. Profiles without bucket configuration will show a warning
4. This eliminates manual bucket entry and prevents configuration errors

### Entity Mapping (entity_config.json)

Maps source entities to their target staging paths:

```json
{
  "entity_mapping": {
    "FHL": "FHL/stage",
    "FNM": "FNM/stage"
  }
}
```

### Cleanup Hooks (entity_config.json)

Define pre-copy cleanup actions for specific entity/dataset combinations:

```json
{
  "cleanup_hooks": {
    "FHL_Dataset134": {
      "type": "pass_through"
    },
    "FHL_Dataset135": {
      "type": "snowflake_cleanup",
      "strategy": "delete_entity_dataset",
      "tables": [
        "staging.fhl_dataset135_temp",
        "staging.fhl_dataset135_audit"
      ]
    }
  }
}
```

**Cleanup Strategies:**

- `pass_through`: No cleanup needed
- `delete_current_date`: Delete records with today's date
- `truncate`: Truncate entire table
- `delete_entity_dataset`: Delete by entity and dataset
- `custom_query`: Use custom SQL query

### Snowflake Configuration (env_config.py)

If using Snowflake cleanup hooks:

```python
SNOWFLAKE_CONFIG = {
    "user": "your_snowflake_username",
    "password": "your_snowflake_password",
    "account": "your_account.region",
    "warehouse": "your_warehouse_name",
    "database": "your_database_name",
    "schema": "your_schema_name"
}
```

## Usage

### Start the Application

```bash
# Using quick start script
chmod +x start.sh
./start.sh

# Or manually
python3 app.py
```

Access at: `http://localhost:5000`

### Workflow

#### **Tab 1: Configuration**

1. Configure entity mappings (e.g., FHL → FHL/stage)
2. Set up cleanup hooks for specific datasets
3. Save configuration

#### **Tab 2: Parse Source**

1. **Select AWS Profile** - Automatically loads configured buckets
2. **Set Date Range** (optional):
    - Leave both empty: Process all datasets
    - Start only: Process from start date onwards
    - Both: Process date range
3. **Choose parsing method**:
    - Parse new data from S3 (creates new pickle file)
    - Load existing pickle file (faster, no S3 scan)
4. Click "Parse Source Bucket"

#### **Tab 3: Query, Filter & Copy** (All-in-one interface)

**Step 1: Select AWS Profile**

- Choose profile (shows configured buckets)
- Verify source and destination buckets

**Step 2: Select and Filter Data**

- Choose pickle file
- Apply filters:
    - Entity name (e.g., FHL)
    - Dataset (e.g., Dataset134)
    - Date range
- Click "Apply Filters"

**Step 3: Review and Select Files**

- Review filtered results
- Select individual files or use "Select All"
- Selection count displays automatically

**Step 4: Confirm and Copy** (Appears when files are selected)

- Review confirmation details:
    - Number of files
    - Source bucket
    - Destination bucket
    - Cleanup hooks that will execute
- Click "✓ Confirm and Copy to Staging"
- Monitor progress and results

## S3 Path Structure

### Source Bucket Format

```
s3://source_bucket/
  └── entity_name/
      └── Dataset###/
          └── year=YYYY/
              └── month=MM/
                  └── day=DD/
                      └── ENTITY_LDST_YYYYMMDD_HHMMSS_r######.DAT
```

### Destination Bucket Format

```
s3://destination_bucket/
  └── stage/
      └── entity_name/
          └── filename.dat
```

## Pickle File Naming

Format: `datasets_{aws_profile}_{timestamp}.pkl`

Example: `datasets_production_20250110_143052.pkl`

## Key Improvements ⭐

### 1. Profile-Based Configuration

- AWS profiles automatically map to buckets via `env_config.py`
- No manual bucket entry required
- Visual indicators show configuration status
- Prevents bucket mismatches

### 2. Streamlined Workflow

- All query, filter, and copy operations in one tab
- Progressive disclosure (confirmation appears when ready)
- Clear step-by-step process
- Real-time selection feedback

### 3. Confirmation Before Copy

- Review exactly what will be copied
- See source and destination buckets
- Understand cleanup actions
- Cancel anytime before execution

## API Endpoints

- `GET /api/profiles` - List AWS profiles with bucket configurations
- `GET /api/profile_config/<profile>` - Get specific profile configuration
- `GET /api/pickle_files` - List existing pickle files
- `GET /api/config` - Get entity and cleanup configuration
- `POST /api/config` - Save configuration
- `POST /api/parse_source` - Parse source bucket (uses profile buckets)
- `POST /api/load_pickle` - Load existing pickle file
- `POST /api/query_pickle` - Query pickle file with filters
- `POST /api/copy_to_staging` - Copy files to staging (uses profile buckets)

## Troubleshooting

### AWS Profile Not Showing Buckets

- Edit `env_config.py` and add your profile with bucket mappings
- Restart the application
- Profile should show "✓ Configured" status

### "Profile Not Configured" Warning

- The AWS profile exists in `~/.aws/credentials` but not in `env_config.py`
- Add the profile to `AWS_PROFILE_CONFIG` in `env_config.py`

### S3 Access Denied

- Verify IAM permissions: `s3:ListBucket`, `s3:GetObject`, `s3:PutObject`
- Check AWS credentials are not expired
- Ensure buckets exist and profile has access

### Snowflake Connection Issues

- Verify `SNOWFLAKE_CONFIG` in `env_config.py`
- Test connection: `pip install snowflake-connector-python`
- Check network access to Snowflake

## Security Notes

- Store AWS credentials in `~/.aws/credentials`, not in code
- Use IAM roles with minimal required permissions
- Keep `env_config.py` secure (contains bucket names)
- Change `FLASK_CONFIG['SECRET_KEY']` for production
- Consider using environment variables for Snowflake credentials

## Production Deployment

1. Edit `env_config.py`:
    - Set `FLASK_CONFIG['DEBUG'] = False`
    - Change `SECRET_KEY`
2. Use production WSGI server (gunicorn, uwsgi)
3. Set up HTTPS with reverse proxy (nginx)
4. Configure logging and monitoring
5. Set up automated pickle file cleanup

## File Management

### Pickle Files

- Stored in `pickle_files/` directory
- Named: `datasets_{profile}_{timestamp}.pkl`
- Can be reused for multiple copy operations
- Recommend cleanup after 30 days

### Configuration Files

- `env_config.py` - Profile/bucket mappings, Snowflake, Flask config
- `entity_config.json` - Entity mappings and cleanup hooks
