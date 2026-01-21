"""
Configuration settings for AWS Resource Monitor.
All settings can be overridden using environment variables.
"""

import os


class Config:
    """Application configuration with sensible defaults."""
    
    # Flask Settings
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    
    # AWS Settings
    DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    AWS_SES_REGION = os.getenv('AWS_SES_REGION', 'us-east-1')
    
    # CloudWatch Metrics Settings
    METRICS_PERIOD_SECONDS = 3600  # 1 hour
    DEFAULT_METRIC_HOURS = 24
    
    # Cost Analysis Settings
    DEFAULT_COST_DAYS = 30
    
    # Bottleneck Detection Thresholds
    CPU_HIGH_THRESHOLD = 80.0      # Alert when CPU > 80%
    CPU_CRITICAL_THRESHOLD = 90.0  # Critical when CPU > 90%
    CPU_LOW_THRESHOLD = 10.0       # Underutilized when CPU < 10%
    
    # Performance Settings
    MAX_CONCURRENT_REGIONS = 10
    REQUEST_TIMEOUT_SECONDS = 30
    
    # Background Monitoring Settings
    MONITORING_ENABLED = os.getenv('MONITORING_ENABLED', 'False').lower() == 'true'
    MONITORING_INTERVAL_MINUTES = int(os.getenv('MONITORING_INTERVAL_MINUTES', '15'))  # Check every 15 minutes
    
    # Alert Settings
    ALERTS_ENABLED = os.getenv('ALERTS_ENABLED', 'False').lower() == 'true'
    ALERT_METHOD = os.getenv('ALERT_METHOD', 'smtp')  # 'smtp' or 'ses'
    ALERT_RECIPIENTS = os.getenv('ALERT_RECIPIENTS', '').split(',')  # Comma-separated emails
    
    # SMTP Settings (for email alerts)
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_FROM_EMAIL = os.getenv('SMTP_FROM_EMAIL', '')


# Environment-specific configurations
class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    # In production, SECRET_KEY must be set via environment variable
    if not os.getenv('SECRET_KEY'):
        raise ValueError("SECRET_KEY environment variable must be set in production")


# Select configuration based on environment
ENV = os.getenv('FLASK_ENV', 'development')
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}
Config = config_map.get(ENV, DevelopmentConfig)
