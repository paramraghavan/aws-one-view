#!/usr/bin/env python3
"""
AWS Monitor - Configuration Validator
Validates YAML configuration files before deployment
"""

import sys
import yaml
import os
from pathlib import Path


class ConfigValidator:
    """Validates AWS Monitor configuration files"""
    
    REQUIRED_FIELDS = ['job_name', 'aws_profile', 'regions', 'resource_types']
    VALID_RESOURCE_TYPES = ['ec2', 'rds', 's3', 'lambda', 'ebs', 'eks', 'emr']
    VALID_OUTPUT_FORMATS = ['detailed', 'summary', 'json']
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_file(self, config_file):
        """Validate a single configuration file"""
        print(f"\nValidating: {config_file}")
        print("=" * 60)
        
        self.errors = []
        self.warnings = []
        
        # Check file exists
        if not os.path.exists(config_file):
            self.errors.append(f"File not found: {config_file}")
            self._print_results()
            return False
        
        # Load YAML
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML: {e}")
            self._print_results()
            return False
        except Exception as e:
            self.errors.append(f"Failed to read file: {e}")
            self._print_results()
            return False
        
        if not config:
            self.errors.append("Empty configuration file")
            self._print_results()
            return False
        
        # Validate required fields
        self._validate_required_fields(config)
        
        # Validate field values
        self._validate_job_name(config)
        self._validate_regions(config)
        self._validate_resource_types(config)
        self._validate_filters(config)
        self._validate_checks(config)
        self._validate_notifications(config)
        self._validate_output(config)
        
        # Print results
        self._print_results()
        
        return len(self.errors) == 0
    
    def _validate_required_fields(self, config):
        """Check all required fields are present"""
        for field in self.REQUIRED_FIELDS:
            if field not in config:
                self.errors.append(f"Missing required field: {field}")
    
    def _validate_job_name(self, config):
        """Validate job_name field"""
        if 'job_name' not in config:
            return
        
        job_name = config['job_name']
        
        if not isinstance(job_name, str):
            self.errors.append("job_name must be a string")
        elif not job_name:
            self.errors.append("job_name cannot be empty")
        elif len(job_name) > 100:
            self.warnings.append("job_name is very long (>100 chars)")
        elif ' ' in job_name:
            self.warnings.append("job_name contains spaces (use hyphens or underscores)")
    
    def _validate_regions(self, config):
        """Validate regions field"""
        if 'regions' not in config:
            return
        
        regions = config['regions']
        
        if not isinstance(regions, list):
            self.errors.append("regions must be a list")
        elif not regions:
            self.errors.append("regions list cannot be empty")
        else:
            for region in regions:
                if not isinstance(region, str):
                    self.errors.append(f"Invalid region: {region} (must be string)")
                elif not region.startswith(('us-', 'eu-', 'ap-', 'ca-', 'sa-', 'af-', 'me-')):
                    self.warnings.append(f"Unusual region format: {region}")
    
    def _validate_resource_types(self, config):
        """Validate resource_types field"""
        if 'resource_types' not in config:
            return
        
        resource_types = config['resource_types']
        
        if not isinstance(resource_types, list):
            self.errors.append("resource_types must be a list")
        elif not resource_types:
            self.errors.append("resource_types list cannot be empty")
        else:
            for rtype in resource_types:
                if rtype not in self.VALID_RESOURCE_TYPES:
                    self.errors.append(f"Invalid resource type: {rtype}")
                    self.errors.append(f"  Valid types: {', '.join(self.VALID_RESOURCE_TYPES)}")
    
    def _validate_filters(self, config):
        """Validate filters section"""
        if 'filters' not in config:
            return
        
        filters = config['filters']
        
        if not isinstance(filters, dict):
            self.errors.append("filters must be a dictionary")
            return
        
        # Validate tags
        if 'tags' in filters:
            if not isinstance(filters['tags'], dict):
                self.errors.append("filters.tags must be a dictionary")
        
        # Validate names
        if 'names' in filters:
            if not isinstance(filters['names'], list):
                self.errors.append("filters.names must be a list")
        
        # Validate ids
        if 'ids' in filters:
            if not isinstance(filters['ids'], list):
                self.errors.append("filters.ids must be a list")
    
    def _validate_checks(self, config):
        """Validate checks section"""
        if 'checks' not in config:
            return
        
        checks = config['checks']
        
        if not isinstance(checks, dict):
            self.errors.append("checks must be a dictionary")
            return
        
        # Validate performance check
        if 'performance' in checks:
            perf = checks['performance']
            if not isinstance(perf, dict):
                self.errors.append("checks.performance must be a dictionary")
            elif 'enabled' in perf and not isinstance(perf['enabled'], bool):
                self.errors.append("checks.performance.enabled must be boolean")
            elif 'period' in perf:
                if not isinstance(perf['period'], int):
                    self.errors.append("checks.performance.period must be integer")
                elif perf['period'] < 60:
                    self.warnings.append("checks.performance.period is very short (<60s)")
        
        # Validate cost check
        if 'cost' in checks:
            cost = checks['cost']
            if not isinstance(cost, dict):
                self.errors.append("checks.cost must be a dictionary")
            elif 'days' in cost:
                if not isinstance(cost['days'], int):
                    self.errors.append("checks.cost.days must be integer")
                elif cost['days'] > 365:
                    self.warnings.append("checks.cost.days is very large (>365)")
        
        # Validate alerts check
        if 'alerts' in checks:
            alerts = checks['alerts']
            if not isinstance(alerts, dict):
                self.errors.append("checks.alerts must be a dictionary")
            elif 'thresholds' in alerts:
                thresholds = alerts['thresholds']
                if not isinstance(thresholds, dict):
                    self.errors.append("checks.alerts.thresholds must be a dictionary")
                else:
                    for key, value in thresholds.items():
                        if not isinstance(value, (int, float)):
                            self.errors.append(f"checks.alerts.thresholds.{key} must be a number")
                        elif value < 0 or value > 100:
                            self.warnings.append(f"checks.alerts.thresholds.{key} is outside 0-100 range")
    
    def _validate_notifications(self, config):
        """Validate notifications section"""
        if 'notifications' not in config:
            return
        
        notif = config['notifications']
        
        if not isinstance(notif, dict):
            self.errors.append("notifications must be a dictionary")
            return
        
        # Validate email
        if 'email' in notif:
            email = notif['email']
            if not isinstance(email, dict):
                self.errors.append("notifications.email must be a dictionary")
            elif 'enabled' in email and email['enabled'] and 'to' not in email:
                self.warnings.append("notifications.email is enabled but 'to' address is missing")
        
        # Validate slack
        if 'slack' in notif:
            slack = notif['slack']
            if not isinstance(slack, dict):
                self.errors.append("notifications.slack must be a dictionary")
            elif 'enabled' in slack and slack['enabled'] and 'webhook_url' not in slack:
                self.warnings.append("notifications.slack is enabled but 'webhook_url' is missing")
        
        # Validate SNS
        if 'sns' in notif:
            sns = notif['sns']
            if not isinstance(sns, dict):
                self.errors.append("notifications.sns must be a dictionary")
            elif 'enabled' in sns and sns['enabled'] and 'topic_arn' not in sns:
                self.warnings.append("notifications.sns is enabled but 'topic_arn' is missing")
    
    def _validate_output(self, config):
        """Validate output section"""
        if 'output' not in config:
            return
        
        output = config['output']
        
        if not isinstance(output, dict):
            self.errors.append("output must be a dictionary")
            return
        
        # Validate format
        if 'format' in output:
            fmt = output['format']
            if fmt not in self.VALID_OUTPUT_FORMATS:
                self.errors.append(f"Invalid output.format: {fmt}")
                self.errors.append(f"  Valid formats: {', '.join(self.VALID_OUTPUT_FORMATS)}")
        
        # Validate log_file
        if 'log_file' in output:
            log_file = output['log_file']
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                self.warnings.append(f"Log directory does not exist: {log_dir}")
        
        # Validate json_file
        if 'json_file' in output:
            json_file = output['json_file']
            json_dir = os.path.dirname(json_file)
            if json_dir and not os.path.exists(json_dir):
                self.warnings.append(f"Output directory does not exist: {json_dir}")
    
    def _print_results(self):
        """Print validation results"""
        print()
        
        if self.errors:
            print(f"❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   - {error}")
            print()
        
        if self.warnings:
            print(f"⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   - {warning}")
            print()
        
        if not self.errors and not self.warnings:
            print("✅ Configuration is valid - no issues found")
            print()
        elif not self.errors:
            print("✅ Configuration is valid (with warnings)")
            print()
        else:
            print("❌ Configuration has errors - please fix before using")
            print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate-config.py <config.yaml> [config2.yaml ...]")
        print()
        print("Examples:")
        print("  python validate-config.py configs/production.yaml")
        print("  python validate-config.py configs/*.yaml")
        sys.exit(1)
    
    validator = ConfigValidator()
    all_valid = True
    
    for config_file in sys.argv[1:]:
        valid = validator.validate_file(config_file)
        if not valid:
            all_valid = False
    
    print("=" * 60)
    if all_valid:
        print("✅ All configurations are valid!")
        sys.exit(0)
    else:
        print("❌ Some configurations have errors")
        sys.exit(1)


if __name__ == '__main__':
    main()
