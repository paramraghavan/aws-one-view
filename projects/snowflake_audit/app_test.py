"""
Test script for Snowflake Operations Monitor with mock connector.
This script demonstrates how to use the mock_snowflake connector for testing the application.
"""

import os
import sys
import unittest
from unittest.mock import patch
import json
import tempfile
from datetime import datetime

# Add mock_snowflake to the path
sys.path.insert(0, os.path.abspath('.'))

# Import mock_snowflake
import mock_snowflake


# Create a temporary config file for testing
def create_test_config():
    """Create a temporary config file for testing."""
    config = {
        "snowflake": {
            "account": "test_account",
            "user": "test_user",
            "password": "test_password",
            "warehouse": "test_warehouse",
            "role": "test_role"
        },
        "databases": [
            {
                "name": "DB1",
                "schemas": ["SCHEMA1", "SCHEMA2", "SCHEMA3"]
            },
            {
                "name": "DB2",
                "schemas": ["SCHEMA1", "SCHEMA4"]
            },
            {
                "name": "DB3",
                "schemas": ["SCHEMA5", "SCHEMA6"]
            }
        ],
        "default_interval": 24,
        "log_file": "test_snowflake_operations.log"
    }

    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w') as f:
        json.dump(config, f)

    return path


class TestSnowflakeMonitor(unittest.TestCase):
    """Test cases for Snowflake Operations Monitor."""

    @classmethod
    def setUpClass(cls):
        """Setup for all test cases."""
        # Create a test config file
        cls.config_path = create_test_config()

        # Create a mock patch for the snowflake.connector
        cls.snowflake_patch = patch('snowflake.connector', mock_snowflake)

    @classmethod
    def tearDownClass(cls):
        """Cleanup after all test cases."""
        # Remove the test config file
        if os.path.exists(cls.config_path):
            os.remove(cls.config_path)

    def setUp(self):
        """Setup before each test case."""
        # Start the snowflake.connector patch
        self.mock_snowflake = self.snowflake_patch.start()

        # Import the application modules after patching
        from config import Config
        from app import get_snowflake_connection, get_schemas_and_tables, check_table_operations

        # Store references to the imported modules
        self.Config = Config
        self.get_snowflake_connection = get_snowflake_connection
        self.get_schemas_and_tables = get_schemas_and_tables
        self.check_table_operations = check_table_operations

        # Initialize config with the test config file
        self.config = self.Config(self.config_path)

    def tearDown(self):
        """Cleanup after each test case."""
        # Stop the snowflake.connector patch
        self.snowflake_patch.stop()

    def test_connection(self):
        """Test connecting to the mock Snowflake."""
        conn = self.get_snowflake_connection()
        self.assertIsNotNone(conn)
        self.assertIsInstance(conn, mock_snowflake.MockConnection)
        conn.close()

    def test_get_schemas_and_tables(self):
        """Test retrieving schemas and tables."""
        db_schema_map = self.get_schemas_and_tables()

        # Verify the structure
        self.assertIsInstance(db_schema_map, dict)

        # Check if the databases are present
        for db in ["DB1", "DB2", "DB3"]:
            self.assertIn(db, db_schema_map)

            # Check if the schemas for this database are present
            for schema in mock_snowflake.SAMPLE_SCHEMAS[db]:
                self.assertIn(schema, db_schema_map[db])

                # Check if tables exist for this schema
                tables = db_schema_map[db][schema]
                self.assertIsInstance(tables, list)

                # Verify tables match our sample data
                expected_tables = mock_snowflake.SAMPLE_TABLES.get(f"{db}.{schema}", [])
                self.assertEqual(sorted(tables), sorted(expected_tables))

    def test_check_table_operations(self):
        """Test checking table operations."""
        # Test for a specific database and schema
        results = self.check_table_operations("DB1", "SCHEMA1", hours=24)

        # Verify the structure of results
        self.assertIsInstance(results, dict)
        self.assertIn("database", results)
        self.assertIn("schema", results)
        self.assertIn("operations", results)
        self.assertIn("operations_count", results)

        # Verify the results match our input
        self.assertEqual(results["database"], "DB1")
        self.assertEqual(results["schema"], "SCHEMA1")

        # Verify operations
        operations = results["operations"]
        self.assertIsInstance(operations, list)
        self.assertEqual(len(operations), results["operations_count"])

        # Check a specific table
        table_results = self.check_table_operations("DB1", "SCHEMA1", "CUSTOMER", hours=24)
        self.assertEqual(table_results["database"], "DB1")
        self.assertEqual(table_results["schema"], "SCHEMA1")
        self.assertEqual(table_results["table"], "CUSTOMER")

    def test_invalid_database(self):
        """Test with an invalid database."""
        results = self.check_table_operations("INVALID_DB", "SCHEMA1", hours=24)

        # Should still return a dict, but with no operations
        self.assertIsInstance(results, dict)
        self.assertEqual(results["database"], "INVALID_DB")
        self.assertEqual(results["operations_count"], 0)

    def test_config_loading(self):
        """Test loading configuration."""
        # Verify snowflake config
        snowflake_config = self.config.get_snowflake_config()
        self.assertEqual(snowflake_config["account"], "test_account")
        self.assertEqual(snowflake_config["user"], "test_user")

        # Verify databases config
        databases = self.config.get_databases()
        self.assertEqual(len(databases), 3)
        self.assertEqual(databases[0]["name"], "DB1")

        # Verify default interval
        interval = self.config.get_default_interval()
        self.assertEqual(interval, 24)

    def test_date_range(self):
        """Test date range calculation."""
        # Test default date range (24 hours)
        start_date, end_date = self.config.get_date_range()
        self.assertIsInstance(start_date, datetime)
        self.assertIsInstance(end_date, datetime)

        # Verify start date is beginning of day
        self.assertEqual(start_date.hour, 0)
        self.assertEqual(start_date.minute, 0)
        self.assertEqual(start_date.second, 0)

        # Test custom interval
        custom_start, custom_end = self.config.get_date_range(hours=12)
        self.assertEqual((custom_end - custom_start).total_seconds(), 12 * 3600)


if __name__ == '__main__':
    unittest.main()