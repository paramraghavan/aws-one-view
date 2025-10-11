"""
Environment Configuration
Maps AWS profiles to source and destination buckets
"""

# AWS Profile to Bucket Mappings
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
    },
    "default": {
        "source_bucket": "s3://default-source-bucket",
        "destination_bucket": "s3://default-destination-bucket",
        "description": "Default profile"
    }
}

# Snowflake Configuration (Optional - only needed if using Snowflake cleanup hooks)
SNOWFLAKE_CONFIG = {
    "user": "your_snowflake_username",
    "password": "your_snowflake_password",
    "account": "your_account.region",
    "warehouse": "your_warehouse_name",
    "database": "your_database_name",
    "schema": "your_schema_name"
}

# Flask Configuration
FLASK_CONFIG = {
    "SECRET_KEY": "your-secret-key-change-in-production",
    "DEBUG": True,
    "HOST": "0.0.0.0",
    "PORT": 7506
}

# Application Settings
APP_SETTINGS = {
    "pickle_dir": "pickle_files",
    "config_file": "entity_config.json",
    "max_pickle_age_days": 30,  # Auto-cleanup old pickle files
    "default_records_per_page": 100
}


def get_bucket_config(profile_name):
    """
    Get source and destination bucket configuration for a given AWS profile

    Args:
        profile_name: AWS profile name

    Returns:
        Dictionary with source_bucket, destination_bucket, and description
        Returns default config if profile not found
    """
    return AWS_PROFILE_CONFIG.get(profile_name, AWS_PROFILE_CONFIG.get("default", {
        "source_bucket": "",
        "destination_bucket": "",
        "description": "No configuration found"
    }))


def get_all_profiles():
    """
    Get all configured AWS profiles

    Returns:
        List of profile configurations with name, description, and buckets
    """
    profiles = []
    for profile_name, config in AWS_PROFILE_CONFIG.items():
        profiles.append({
            "name": profile_name,
            "description": config.get("description", ""),
            "source_bucket": config.get("source_bucket", ""),
            "destination_bucket": config.get("destination_bucket", "")
        })
    return profiles


def validate_profile_config(profile_name):
    """
    Validate that a profile has complete configuration

    Args:
        profile_name: AWS profile name

    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    if profile_name not in AWS_PROFILE_CONFIG:
        return False, f"Profile '{profile_name}' not found in configuration"

    config = AWS_PROFILE_CONFIG[profile_name]

    if not config.get("source_bucket"):
        return False, f"Source bucket not configured for profile '{profile_name}'"

    if not config.get("destination_bucket"):
        return False, f"Destination bucket not configured for profile '{profile_name}'"

    return True, "Configuration valid"