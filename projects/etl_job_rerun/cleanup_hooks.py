"""
Cleanup Hooks Module
Provides cleanup implementations for different data sources before copying to staging.
"""

import os
from typing import Tuple, Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CleanupHookManager:
    """Manages cleanup operations for different entity/dataset combinations"""

    def __init__(self, snowflake_config: Dict[str, Any] = None):
        """
        Initialize cleanup hook manager

        Args:
            snowflake_config: Configuration for Snowflake connection
                {
                    'user': 'username',
                    'password': 'password',
                    'account': 'account_name',
                    'warehouse': 'warehouse_name',
                    'database': 'database_name',
                    'schema': 'schema_name'
                }
        """
        self.snowflake_config = snowflake_config or {}
        self.snowflake_conn = None

    def execute_cleanup(self, entity_name: str, dataset: str,
                        cleanup_config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Execute cleanup hook for specific entity/dataset

        Args:
            entity_name: Entity name (e.g., 'FHL')
            dataset: Dataset name (e.g., 'Dataset135')
            cleanup_config: Cleanup configuration from entity_config.json

        Returns:
            Tuple of (success: bool, message: str)
        """
        cleanup_key = f"{entity_name}_{dataset}"

        # No cleanup configured - pass through
        if cleanup_key not in cleanup_config:
            logger.info(f"No cleanup configured for {cleanup_key} - passing through")
            return True, "Pass-through (no cleanup required)"

        cleanup_action = cleanup_config[cleanup_key]
        cleanup_type = cleanup_action.get('type', 'pass_through')

        logger.info(f"Executing {cleanup_type} cleanup for {cleanup_key}")

        # Route to appropriate cleanup handler
        if cleanup_type == 'pass_through':
            return self._pass_through_cleanup()

        elif cleanup_type == 'snowflake_cleanup':
            return self._snowflake_cleanup(cleanup_action, entity_name, dataset)

        elif cleanup_type == 'custom_script':
            return self._custom_script_cleanup(cleanup_action, entity_name, dataset)

        else:
            logger.warning(f"Unknown cleanup type: {cleanup_type}")
            return True, f"Unknown cleanup type: {cleanup_type} (defaulting to pass-through)"

    def _pass_through_cleanup(self) -> Tuple[bool, str]:
        """No cleanup needed - pass through"""
        return True, "Pass-through"

    def _snowflake_cleanup(self, cleanup_action: Dict[str, Any],
                           entity_name: str, dataset: str) -> Tuple[bool, str]:
        """
        Execute Snowflake table cleanup

        Args:
            cleanup_action: Cleanup configuration with 'tables' list
            entity_name: Entity name
            dataset: Dataset name

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            import snowflake.connector
        except ImportError:
            logger.error("snowflake-connector-python not installed")
            return False, "Snowflake connector not installed. Run: pip install snowflake-connector-python"

        tables = cleanup_action.get('tables', [])
        if not tables:
            return True, "No tables specified for cleanup"

        try:
            # Create connection if not exists
            if not self.snowflake_conn:
                self.snowflake_conn = snowflake.connector.connect(
                    user=self.snowflake_config.get('user'),
                    password=self.snowflake_config.get('password'),
                    account=self.snowflake_config.get('account'),
                    warehouse=self.snowflake_config.get('warehouse'),
                    database=self.snowflake_config.get('database'),
                    schema=self.snowflake_config.get('schema')
                )

            cursor = self.snowflake_conn.cursor()
            cleaned_tables = []

            for table in tables:
                logger.info(f"Cleaning Snowflake table: {table}")

                # Determine cleanup strategy based on configuration
                cleanup_strategy = cleanup_action.get('strategy', 'delete_current_date')

                if cleanup_strategy == 'delete_current_date':
                    query = f"DELETE FROM {table} WHERE load_date = CURRENT_DATE()"
                elif cleanup_strategy == 'truncate':
                    query = f"TRUNCATE TABLE {table}"
                elif cleanup_strategy == 'delete_entity_dataset':
                    query = f"""
                        DELETE FROM {table} 
                        WHERE entity_name = '{entity_name}' 
                        AND dataset_name = '{dataset}'
                    """
                elif cleanup_strategy == 'custom_query':
                    query = cleanup_action.get('custom_query', '').format(
                        table=table,
                        entity_name=entity_name,
                        dataset=dataset
                    )
                else:
                    logger.warning(f"Unknown cleanup strategy: {cleanup_strategy}")
                    continue

                cursor.execute(query)
                rows_affected = cursor.rowcount
                logger.info(f"Cleaned {rows_affected} rows from {table}")
                cleaned_tables.append(f"{table} ({rows_affected} rows)")

            cursor.close()

            return True, f"Successfully cleaned tables: {', '.join(cleaned_tables)}"

        except Exception as e:
            logger.error(f"Snowflake cleanup failed: {str(e)}")
            return False, f"Snowflake cleanup failed: {str(e)}"

    def _custom_script_cleanup(self, cleanup_action: Dict[str, Any],
                               entity_name: str, dataset: str) -> Tuple[bool, str]:
        """
        Execute custom cleanup script

        Args:
            cleanup_action: Configuration with 'script_path' key
            entity_name: Entity name
            dataset: Dataset name

        Returns:
            Tuple of (success: bool, message: str)
        """
        script_path = cleanup_action.get('script_path')

        if not script_path or not os.path.exists(script_path):
            return False, f"Custom script not found: {script_path}"

        try:
            import subprocess

            # Execute script with entity and dataset as arguments
            result = subprocess.run(
                ['python', script_path, entity_name, dataset],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                return True, f"Custom script executed successfully: {result.stdout}"
            else:
                return False, f"Custom script failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Custom script execution timed out (5 minutes)"
        except Exception as e:
            return False, f"Custom script execution failed: {str(e)}"

    def close(self):
        """Close any open connections"""
        if self.snowflake_conn:
            try:
                self.snowflake_conn.close()
                logger.info("Snowflake connection closed")
            except Exception as e:
                logger.error(f"Error closing Snowflake connection: {e}")


# Example usage functions
def get_cleanup_manager_from_env() -> CleanupHookManager:
    """
    Create cleanup manager using environment variables for Snowflake config

    Environment variables:
        SNOWFLAKE_USER
        SNOWFLAKE_PASSWORD
        SNOWFLAKE_ACCOUNT
        SNOWFLAKE_WAREHOUSE
        SNOWFLAKE_DATABASE
        SNOWFLAKE_SCHEMA
    """
    snowflake_config = {
        'user': os.getenv('SNOWFLAKE_USER'),
        'password': os.getenv('SNOWFLAKE_PASSWORD'),
        'account': os.getenv('SNOWFLAKE_ACCOUNT'),
        'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE'),
        'database': os.getenv('SNOWFLAKE_DATABASE'),
        'schema': os.getenv('SNOWFLAKE_SCHEMA')
    }

    return CleanupHookManager(snowflake_config)


def example_cleanup_config() -> Dict[str, Any]:
    """
    Example cleanup configuration structure

    Returns:
        Dictionary with example cleanup configurations
    """
    return {
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
        },
        "FNM_Dataset200": {
            "type": "snowflake_cleanup",
            "strategy": "truncate",
            "tables": [
                "staging.fnm_dataset200_staging"
            ]
        },
        "XYZ_Dataset999": {
            "type": "snowflake_cleanup",
            "strategy": "custom_query",
            "custom_query": "DELETE FROM {table} WHERE entity = '{entity_name}' AND dataset = '{dataset}' AND status = 'FAILED'",
            "tables": [
                "staging.xyz_processing_log"
            ]
        },
        "ABC_Dataset100": {
            "type": "custom_script",
            "script_path": "./cleanup_scripts/abc_cleanup.py"
        }
    }


if __name__ == '__main__':
    # Example usage
    cleanup_manager = CleanupHookManager()

    # Example cleanup configurations
    config = example_cleanup_config()

    # Execute cleanup for different entities
    success, message = cleanup_manager.execute_cleanup('FHL', 'Dataset134', config)
    print(f"FHL_Dataset134: {success} - {message}")

    success, message = cleanup_manager.execute_cleanup('FHL', 'Dataset135', config)
    print(f"FHL_Dataset135: {success} - {message}")

    cleanup_manager.close()