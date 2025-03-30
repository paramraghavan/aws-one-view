"""
Mock Snowflake connector for testing purposes.
This module provides a drop-in replacement for the snowflake.connector module
that can be used for testing without an actual Snowflake connection.
"""

import datetime
import random
import re
from typing import List, Dict, Any, Tuple, Optional, Union

# Sample data structures
SAMPLE_DATABASES = ["DB1", "DB2", "DB3"]
SAMPLE_SCHEMAS = {
    "DB1": ["SCHEMA1", "SCHEMA2", "SCHEMA3"],
    "DB2": ["SCHEMA1", "SCHEMA4"],
    "DB3": ["SCHEMA5", "SCHEMA6"]
}

SAMPLE_TABLES = {
    "DB1.SCHEMA1": ["CUSTOMER", "ORDER", "PRODUCT"],
    "DB1.SCHEMA2": ["EMPLOYEE", "DEPARTMENT", "SALARY"],
    "DB1.SCHEMA3": ["LOG", "ERROR", "AUDIT"],
    "DB2.SCHEMA1": ["FINANCE", "REVENUE", "EXPENSE"],
    "DB2.SCHEMA4": ["MARKETING", "CAMPAIGN", "LEAD"],
    "DB3.SCHEMA5": ["INVENTORY", "WAREHOUSE", "SUPPLIER"],
    "DB3.SCHEMA6": ["SHIPPING", "DELIVERY", "TRACKING"]
}

# Sample query history data
QUERY_TYPES = ["INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"]
USERS = ["ADMIN", "ANALYST", "DEVELOPER", "DATAENGINEER", "TESTER"]
STATUSES = ["SUCCESS", "ERROR", "RUNNING", "QUEUED"]


class MockCursor:
    """Mock implementation of Snowflake cursor."""

    def __init__(self, connection):
        self.connection = connection
        self.query_results = []
        self.description = []
        self.rowcount = 0
        self.current_database = None
        self.current_schema = None
        self._query_id = 0

    def execute(self, query: str) -> "MockCursor":
        """Execute a query on the mock connection."""
        # Log the query for debugging
        print(f"Mock executing: {query}")

        # Increment query ID
        self._query_id += 1

        # Process different query types
        query = query.strip().upper()

        # USE DATABASE
        if query.startswith("USE DATABASE"):
            db_name = re.search(r"USE DATABASE\s+(\w+)", query)
            if db_name and db_name.group(1) in SAMPLE_DATABASES:
                self.current_database = db_name.group(1)
                self.query_results = []
                self.description = []
                self.rowcount = 0
                return self

        # USE SCHEMA
        elif query.startswith("USE SCHEMA"):
            schema_name = re.search(r"USE SCHEMA\s+(\w+)", query)
            if schema_name and self.current_database:
                if schema_name.group(1) in SAMPLE_SCHEMAS.get(self.current_database, []):
                    self.current_schema = schema_name.group(1)
                    self.query_results = []
                    self.description = []
                    self.rowcount = 0
                    return self

        # SHOW TABLES
        elif query.startswith("SHOW TABLES"):
            match = re.search(r"SHOW TABLES IN\s+(\w+)\.(\w+)", query)
            if match:
                db_name = match.group(1)
                schema_name = match.group(2)
                key = f"{db_name}.{schema_name}"

                if key in SAMPLE_TABLES:
                    # Create result structure similar to Snowflake's SHOW TABLES
                    self.query_results = []
                    for table_name in SAMPLE_TABLES[key]:
                        # Snowflake SHOW TABLES returns data in a specific format
                        # We'll simplify by just including the main fields needed
                        self.query_results.append((
                            self._query_id,  # created_on (using query_id as a stand-in)
                            table_name,  # name
                            "TABLE",  # kind
                            db_name,  # database_name
                            schema_name,  # schema_name
                            0,  # rows
                            0  # bytes
                        ))

                    self.description = [
                        ("created_on", None, None, None, None, None, None),
                        ("name", None, None, None, None, None, None),
                        ("kind", None, None, None, None, None, None),
                        ("database_name", None, None, None, None, None, None),
                        ("schema_name", None, None, None, None, None, None),
                        ("rows", None, None, None, None, None, None),
                        ("bytes", None, None, None, None, None, None)
                    ]
                    self.rowcount = len(self.query_results)
                    return self

        # Query history queries
        elif "SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY" in query:
            match_db_schema = re.search(r"DATABASE_NAME\s*=\s*'(\w+)'\s+AND\s+SCHEMA_NAME\s*=\s*'(\w+)'", query)
            match_table = re.search(r"QUERY_TEXT\s+ILIKE\s+'%(\w+)%'", query)

            if match_db_schema:
                db_name = match_db_schema.group(1)
                schema_name = match_db_schema.group(2)
                table_filter = match_table.group(1) if match_table else None

                # Generate mock query history data
                self._generate_query_history(db_name, schema_name, table_filter)
                return self

        # Default case - empty result
        self.query_results = []
        self.description = []
        self.rowcount = 0
        return self

    def fetchall(self) -> List[Tuple]:
        """Fetch all results from the last query."""
        return self.query_results

    def fetchone(self) -> Optional[Tuple]:
        """Fetch one result from the last query."""
        if self.query_results:
            return self.query_results[0]
        return None

    def close(self) -> None:
        """Close the cursor."""
        self.query_results = []
        self.description = []

    def _generate_query_history(self, db_name: str, schema_name: str, table_filter: Optional[str] = None) -> None:
        """Generate mock query history data."""
        # Check if the requested DB and schema are in our sample data
        if db_name not in SAMPLE_DATABASES or schema_name not in SAMPLE_SCHEMAS.get(db_name, []):
            self.query_results = []
            self.description = []
            self.rowcount = 0
            return

        # Get tables for this schema
        key = f"{db_name}.{schema_name}"
        tables = SAMPLE_TABLES.get(key, [])

        if table_filter:
            tables = [t for t in tables if table_filter.upper() in t]

        if not tables:
            self.query_results = []
            self.description = []
            self.rowcount = 0
            return

        # Generate between 0-20 random operations
        num_operations = random.randint(0, 20)

        # Description for the query
        self.description = [
            ("QUERY_TEXT", None, None, None, None, None, None),
            ("DATABASE_NAME", None, None, None, None, None, None),
            ("SCHEMA_NAME", None, None, None, None, None, None),
            ("USER_NAME", None, None, None, None, None, None),
            ("QUERY_TYPE", None, None, None, None, None, None),
            ("EXECUTION_STATUS", None, None, None, None, None, None),
            ("START_TIME", None, None, None, None, None, None),
            ("END_TIME", None, None, None, None, None, None),
            ("ROWS_PRODUCED", None, None, None, None, None, None),
            ("ERROR_MESSAGE", None, None, None, None, None, None)
        ]

        operations = []
        # Generate data for the last 24 hours
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(hours=24)

        for _ in range(num_operations):
            table = random.choice(tables)
            query_type = random.choice(QUERY_TYPES)
            user = random.choice(USERS)
            status = random.choice(STATUSES)

            # Generate random timestamps in the past 24 hours
            op_time = start_time + datetime.timedelta(
                seconds=random.randint(0, int((end_time - start_time).total_seconds()))
            )

            # End time is a bit after start time
            end_op_time = op_time + datetime.timedelta(seconds=random.randint(1, 60))

            # Generate a mock query text based on the operation type
            query_text = self._generate_query_text(query_type, db_name, schema_name, table)

            # Generate row count - more for INSERTs, fewer for others
            rows_produced = random.randint(0, 1000) if query_type == "INSERT" else random.randint(0, 100)

            # Error message only for ERROR status
            error_message = self._generate_error_message() if status == "ERROR" else None

            # Create the operation record
            operations.append((
                query_text,
                db_name,
                schema_name,
                user,
                query_type,
                status,
                op_time,
                end_op_time,
                rows_produced,
                error_message
            ))

        self.query_results = operations
        self.rowcount = len(operations)

    def _generate_query_text(self, query_type: str, db_name: str, schema_name: str, table: str) -> str:
        """Generate a mock SQL query text."""
        table_path = f"{db_name}.{schema_name}.{table}"

        if query_type == "INSERT":
            return f"INSERT INTO {table_path} (col1, col2) VALUES ('value1', 'value2')"

        elif query_type == "UPDATE":
            return f"UPDATE {table_path} SET col1 = 'new_value' WHERE col2 = 'condition'"

        elif query_type == "DELETE":
            return f"DELETE FROM {table_path} WHERE col1 = 'condition'"

        elif query_type == "CREATE":
            return f"CREATE TABLE {table_path} (col1 VARCHAR, col2 INTEGER)"

        elif query_type == "DROP":
            return f"DROP TABLE {table_path}"

        elif query_type == "ALTER":
            return f"ALTER TABLE {table_path} ADD COLUMN col3 FLOAT"

        return f"SELECT * FROM {table_path}"

    def _generate_error_message(self) -> str:
        """Generate a realistic error message."""
        error_messages = [
            "Syntax error: Unexpected symbol ')'",
            "Object does not exist or operation cannot be performed",
            "Insufficient privileges to perform this operation",
            "Column not found",
            "Duplicate key value violates unique constraint",
            "Operation timed out",
            "Resource limit exceeded",
            "Division by zero",
            "Invalid date format",
            "Transaction aborted due to conflict"
        ]
        return random.choice(error_messages)


class MockConnection:
    """Mock implementation of Snowflake connection."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.is_closed = False
        self._cursors = []

    def cursor(self) -> MockCursor:
        """Create a new cursor for the connection."""
        cursor = MockCursor(self)
        self._cursors.append(cursor)
        return cursor

    def close(self) -> None:
        """Close the connection."""
        for cursor in self._cursors:
            cursor.close()
        self._cursors = []
        self.is_closed = True

    def commit(self) -> None:
        """Commit the transaction (no-op for the mock)."""
        pass

    def rollback(self) -> None:
        """Rollback the transaction (no-op for the mock)."""
        pass


def connect(**kwargs) -> MockConnection:
    """Create a mock connection to Snowflake."""
    print(f"Creating mock Snowflake connection with: {kwargs}")
    return MockConnection(**kwargs)
