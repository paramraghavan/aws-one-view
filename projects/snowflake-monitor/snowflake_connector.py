"""
Snowflake Connector Module
Contains all the queries and logic for monitoring Snowflake resources.
"""

import snowflake.connector
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Dict, List, Any, Optional


class SnowflakeMonitor:
    """Monitor class for Snowflake resource tracking."""
    
    def __init__(self, config: Dict[str, str]):
        self.config = config
        
    @contextmanager
    def get_connection(self):
        """Context manager for Snowflake connections."""
        conn = snowflake.connector.connect(
            account=self.config['account'],
            user=self.config['user'],
            password=self.config['password'],
            warehouse=self.config['warehouse'],
            database=self.config['database'],
            schema=self.config['schema'],
            role=self.config['role']
        )
        try:
            yield conn
        finally:
            conn.close()
            
    def execute_query(self, query: str) -> List[Dict]:
        """Execute a query and return results as list of dicts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
    
    def get_overview_metrics(self) -> Dict:
        """Get high-level overview metrics."""
        
        # Total credits used in last 30 days
        credits_query = """
        SELECT 
            COALESCE(SUM(CREDITS_USED), 0) as TOTAL_CREDITS,
            COUNT(DISTINCT WAREHOUSE_NAME) as ACTIVE_WAREHOUSES
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE START_TIME >= DATEADD(day, -30, CURRENT_TIMESTAMP())
        """
        
        # Total storage
        storage_query = """
        SELECT 
            COALESCE(SUM(AVERAGE_DATABASE_BYTES + AVERAGE_FAILSAFE_BYTES), 0) / POWER(1024, 4) as TOTAL_STORAGE_TB
        FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
        WHERE USAGE_DATE = (SELECT MAX(USAGE_DATE) FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY)
        """
        
        # Query count last 24 hours
        query_count = """
        SELECT 
            COUNT(*) as QUERY_COUNT,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_QUERY_TIME_SEC
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(hour, -24, CURRENT_TIMESTAMP())
        """
        
        # Failed queries
        failed_query = """
        SELECT COUNT(*) as FAILED_QUERIES
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(hour, -24, CURRENT_TIMESTAMP())
        AND EXECUTION_STATUS = 'FAIL'
        """
        
        credits_result = self.execute_query(credits_query)
        storage_result = self.execute_query(storage_query)
        query_result = self.execute_query(query_count)
        failed_result = self.execute_query(failed_query)
        
        return {
            'total_credits_30d': float(credits_result[0]['TOTAL_CREDITS'] or 0),
            'active_warehouses': int(credits_result[0]['ACTIVE_WAREHOUSES'] or 0),
            'total_storage_tb': float(storage_result[0]['TOTAL_STORAGE_TB'] or 0),
            'queries_24h': int(query_result[0]['QUERY_COUNT'] or 0),
            'avg_query_time_sec': float(query_result[0]['AVG_QUERY_TIME_SEC'] or 0),
            'failed_queries_24h': int(failed_result[0]['FAILED_QUERIES'] or 0)
        }
    
    def get_warehouse_costs(self, days: int = 30) -> List[Dict]:
        """Get warehouse cost breakdown."""
        query = f"""
        SELECT 
            WAREHOUSE_NAME,
            SUM(CREDITS_USED) as TOTAL_CREDITS,
            SUM(CREDITS_USED_COMPUTE) as COMPUTE_CREDITS,
            SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_SERVICES_CREDITS,
            COUNT(DISTINCT DATE_TRUNC('day', START_TIME)) as ACTIVE_DAYS,
            AVG(CREDITS_USED) as AVG_HOURLY_CREDITS
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY WAREHOUSE_NAME
        ORDER BY TOTAL_CREDITS DESC
        """
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def get_warehouse_usage(self, days: int = 7) -> List[Dict]:
        """Get warehouse usage statistics."""
        query = f"""
        SELECT 
            WAREHOUSE_NAME,
            DATE_TRUNC('hour', START_TIME) as HOUR,
            SUM(CREDITS_USED) as CREDITS_USED
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY WAREHOUSE_NAME, DATE_TRUNC('hour', START_TIME)
        ORDER BY HOUR DESC, WAREHOUSE_NAME
        """
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def get_long_running_queries(self, threshold_seconds: int = 60, limit: int = 50) -> List[Dict]:
        """Get queries that exceeded the time threshold."""
        query = f"""
        SELECT 
            QUERY_ID,
            QUERY_TEXT,
            USER_NAME,
            WAREHOUSE_NAME,
            DATABASE_NAME,
            SCHEMA_NAME,
            EXECUTION_STATUS,
            START_TIME,
            END_TIME,
            TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SECONDS,
            BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED,
            ROWS_PRODUCED,
            COMPILATION_TIME / 1000 as COMPILATION_SECONDS,
            EXECUTION_TIME / 1000 as EXECUTION_SECONDS,
            QUEUED_PROVISIONING_TIME / 1000 as QUEUED_PROVISIONING_SECONDS,
            QUEUED_OVERLOAD_TIME / 1000 as QUEUED_OVERLOAD_SECONDS
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        AND TOTAL_ELAPSED_TIME > {threshold_seconds * 1000}
        ORDER BY TOTAL_ELAPSED_TIME DESC
        LIMIT {limit}
        """
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def get_expensive_queries(self, days: int = 7, limit: int = 50) -> List[Dict]:
        """Get most expensive queries by estimated credits."""
        query = f"""
        SELECT 
            qh.QUERY_ID,
            qh.QUERY_TEXT,
            qh.USER_NAME,
            qh.WAREHOUSE_NAME,
            qh.DATABASE_NAME,
            qh.START_TIME,
            qh.TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SECONDS,
            qh.BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED,
            qh.BYTES_WRITTEN / POWER(1024, 3) as GB_WRITTEN,
            qh.ROWS_PRODUCED,
            qh.CREDITS_USED_CLOUD_SERVICES
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY qh
        WHERE qh.START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND qh.EXECUTION_STATUS = 'SUCCESS'
        ORDER BY qh.TOTAL_ELAPSED_TIME DESC
        LIMIT {limit}
        """
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def get_storage_usage(self) -> List[Dict]:
        """Get storage usage by database."""
        query = """
        SELECT 
            DATABASE_NAME,
            AVERAGE_DATABASE_BYTES / POWER(1024, 3) as DATABASE_GB,
            AVERAGE_FAILSAFE_BYTES / POWER(1024, 3) as FAILSAFE_GB,
            (AVERAGE_DATABASE_BYTES + AVERAGE_FAILSAFE_BYTES) / POWER(1024, 3) as TOTAL_GB
        FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
        WHERE USAGE_DATE = (SELECT MAX(USAGE_DATE) FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY)
        ORDER BY TOTAL_GB DESC
        """
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def get_cluster_load(self, days: int = 7) -> List[Dict]:
        """Get cluster load and concurrency metrics."""
        query = f"""
        SELECT 
            WAREHOUSE_NAME,
            DATE_TRUNC('hour', START_TIME) as HOUR,
            AVG(AVG_RUNNING) as AVG_CONCURRENT_QUERIES,
            MAX(AVG_RUNNING) as MAX_CONCURRENT_QUERIES,
            AVG(AVG_QUEUED_LOAD) as AVG_QUEUED,
            MAX(AVG_QUEUED_LOAD) as MAX_QUEUED,
            AVG(AVG_QUEUED_PROVISIONING) as AVG_QUEUED_PROVISIONING,
            AVG(AVG_BLOCKED) as AVG_BLOCKED
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY WAREHOUSE_NAME, DATE_TRUNC('hour', START_TIME)
        ORDER BY HOUR DESC
        """
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def get_warehouse_configurations(self) -> List[Dict]:
        """Get warehouse configurations including auto-suspend settings."""
        # Use SHOW WAREHOUSES command (WAREHOUSES view doesn't exist in ACCOUNT_USAGE)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SHOW WAREHOUSES")
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                # Map to expected column names
                results.append({
                    'WAREHOUSE_NAME': row_dict.get('name'),
                    'STATE': row_dict.get('state'),
                    'TYPE': row_dict.get('type'),
                    'SIZE': row_dict.get('size'),
                    'MIN_CLUSTER_COUNT': row_dict.get('min_cluster_count'),
                    'MAX_CLUSTER_COUNT': row_dict.get('max_cluster_count'),
                    'SCALING_POLICY': row_dict.get('scaling_policy'),
                    'AUTO_SUSPEND': row_dict.get('auto_suspend'),
                    'AUTO_RESUME': row_dict.get('auto_resume'),
                    'RESOURCE_MONITOR': row_dict.get('resource_monitor'),
                    'CREATED_ON': row_dict.get('created_on'),
                    'OWNER': row_dict.get('owner')
                })
            return self._serialize_results(results)
    
    def analyze_query_patterns(self, days: int = 7) -> Dict:
        """Analyze query patterns for potential bottlenecks."""
        
        # Query by hour of day
        hourly_pattern = f"""
        SELECT 
            EXTRACT(HOUR FROM START_TIME) as HOUR_OF_DAY,
            COUNT(*) as QUERY_COUNT,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_ELAPSED_SEC,
            SUM(BYTES_SCANNED) / POWER(1024, 4) as TOTAL_TB_SCANNED
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY EXTRACT(HOUR FROM START_TIME)
        ORDER BY HOUR_OF_DAY
        """
        
        # Query by type
        type_pattern = f"""
        SELECT 
            QUERY_TYPE,
            COUNT(*) as QUERY_COUNT,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_ELAPSED_SEC,
            SUM(TOTAL_ELAPSED_TIME) / 1000 as TOTAL_ELAPSED_SEC
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY QUERY_TYPE
        ORDER BY QUERY_COUNT DESC
        """
        
        # Query by user
        user_pattern = f"""
        SELECT 
            USER_NAME,
            COUNT(*) as QUERY_COUNT,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_ELAPSED_SEC,
            SUM(BYTES_SCANNED) / POWER(1024, 3) as TOTAL_GB_SCANNED
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY USER_NAME
        ORDER BY QUERY_COUNT DESC
        LIMIT 20
        """
        
        return {
            'hourly': self._serialize_results(self.execute_query(hourly_pattern)),
            'by_type': self._serialize_results(self.execute_query(type_pattern)),
            'by_user': self._serialize_results(self.execute_query(user_pattern))
        }
    
    def get_cost_trends(self, days: int = 30) -> List[Dict]:
        """Get daily cost trends."""
        query = f"""
        SELECT 
            DATE_TRUNC('day', START_TIME) as DATE,
            SUM(CREDITS_USED) as TOTAL_CREDITS,
            SUM(CREDITS_USED_COMPUTE) as COMPUTE_CREDITS,
            SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_SERVICES_CREDITS
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY DATE_TRUNC('day', START_TIME)
        ORDER BY DATE
        """
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def analyze_bottlenecks(self) -> Dict:
        """Comprehensive bottleneck analysis."""
        
        # Queuing analysis
        queuing_query = """
        SELECT 
            WAREHOUSE_NAME,
            SUM(CASE WHEN QUEUED_OVERLOAD_TIME > 0 THEN 1 ELSE 0 END) as QUEUED_QUERIES,
            AVG(QUEUED_OVERLOAD_TIME) / 1000 as AVG_QUEUE_TIME_SEC,
            MAX(QUEUED_OVERLOAD_TIME) / 1000 as MAX_QUEUE_TIME_SEC,
            COUNT(*) as TOTAL_QUERIES
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        GROUP BY WAREHOUSE_NAME
        HAVING QUEUED_QUERIES > 0
        ORDER BY QUEUED_QUERIES DESC
        """
        
        # Spilling analysis (queries that spill to disk)
        spilling_query = """
        SELECT 
            WAREHOUSE_NAME,
            COUNT(*) as SPILLING_QUERIES,
            SUM(BYTES_SPILLED_TO_LOCAL_STORAGE) / POWER(1024, 3) as GB_SPILLED_LOCAL,
            SUM(BYTES_SPILLED_TO_REMOTE_STORAGE) / POWER(1024, 3) as GB_SPILLED_REMOTE
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        AND (BYTES_SPILLED_TO_LOCAL_STORAGE > 0 OR BYTES_SPILLED_TO_REMOTE_STORAGE > 0)
        GROUP BY WAREHOUSE_NAME
        ORDER BY SPILLING_QUERIES DESC
        """
        
        # Compilation time analysis
        compilation_query = """
        SELECT 
            WAREHOUSE_NAME,
            COUNT(*) as HIGH_COMPILE_QUERIES,
            AVG(COMPILATION_TIME) / 1000 as AVG_COMPILE_SEC,
            MAX(COMPILATION_TIME) / 1000 as MAX_COMPILE_SEC
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        AND COMPILATION_TIME > 5000
        GROUP BY WAREHOUSE_NAME
        ORDER BY HIGH_COMPILE_QUERIES DESC
        """
        
        # Failed queries analysis
        failure_query = """
        SELECT 
            ERROR_CODE,
            ERROR_MESSAGE,
            COUNT(*) as FAILURE_COUNT
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        AND EXECUTION_STATUS = 'FAIL'
        GROUP BY ERROR_CODE, ERROR_MESSAGE
        ORDER BY FAILURE_COUNT DESC
        LIMIT 10
        """
        
        return {
            'queuing': self._serialize_results(self.execute_query(queuing_query)),
            'spilling': self._serialize_results(self.execute_query(spilling_query)),
            'compilation': self._serialize_results(self.execute_query(compilation_query)),
            'failures': self._serialize_results(self.execute_query(failure_query))
        }
    
    def get_database_costs(self, days: int = 30) -> List[Dict]:
        """Get cost breakdown by database."""
        query = f"""
        SELECT 
            DATABASE_NAME,
            COUNT(*) as QUERY_COUNT,
            SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 as TOTAL_HOURS,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_ELAPSED_SEC,
            SUM(BYTES_SCANNED) / POWER(1024, 4) as TB_SCANNED,
            SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_SERVICES_CREDITS
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND DATABASE_NAME IS NOT NULL
        GROUP BY DATABASE_NAME
        ORDER BY TOTAL_HOURS DESC
        """
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def get_recommendations(self) -> List[Dict]:
        """Generate optimization recommendations based on analysis."""
        recommendations = []
        
        # Get warehouse configurations using SHOW WAREHOUSES
        try:
            warehouse_configs = self.get_warehouse_configurations()
            
            # Check for warehouses that could benefit from auto-suspend
            for wh in warehouse_configs:
                auto_suspend = wh.get('AUTO_SUSPEND')
                if auto_suspend is None or (isinstance(auto_suspend, (int, float)) and auto_suspend > 300):
                    recommendations.append({
                        'category': 'Cost Optimization',
                        'severity': 'Medium',
                        'title': f'Consider reducing auto-suspend for {wh["WAREHOUSE_NAME"]}',
                        'description': f'Warehouse {wh["WAREHOUSE_NAME"]} has auto-suspend of {auto_suspend} seconds. Consider reducing to 60-120 seconds to save costs during idle periods.',
                        'warehouse': wh['WAREHOUSE_NAME']
                    })
        except Exception:
            pass
        
        # Check for oversized warehouses using WAREHOUSE_LOAD_HISTORY
        try:
            oversize_query = """
            SELECT 
                WAREHOUSE_NAME,
                AVG(AVG_RUNNING) as AVG_CONCURRENT
            FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
            WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
            GROUP BY WAREHOUSE_NAME
            HAVING AVG_CONCURRENT < 0.2
            """
            oversize_results = self.execute_query(oversize_query)
            for r in oversize_results:
                if r.get('AVG_CONCURRENT') is not None:
                    recommendations.append({
                        'category': 'Right-sizing',
                        'severity': 'High',
                        'title': f'Warehouse {r["WAREHOUSE_NAME"]} may be oversized',
                        'description': f'Warehouse {r["WAREHOUSE_NAME"]} has low average concurrency ({r["AVG_CONCURRENT"]:.2f}). Consider downsizing.',
                        'warehouse': r['WAREHOUSE_NAME']
                    })
        except Exception:
            pass
        
        # Check for high queue times
        queue_query = """
        SELECT 
            WAREHOUSE_NAME,
            AVG(QUEUED_OVERLOAD_TIME) / 1000 as AVG_QUEUE_SEC,
            COUNT(*) as AFFECTED_QUERIES
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        AND QUEUED_OVERLOAD_TIME > 10000
        GROUP BY WAREHOUSE_NAME
        HAVING AFFECTED_QUERIES > 10
        ORDER BY AVG_QUEUE_SEC DESC
        """
        try:
            queue_results = self.execute_query(queue_query)
            for r in queue_results:
                recommendations.append({
                    'category': 'Performance',
                    'severity': 'High',
                    'title': f'High queue times on {r["WAREHOUSE_NAME"]}',
                    'description': f'{r["AFFECTED_QUERIES"]} queries experienced avg queue time of {r["AVG_QUEUE_SEC"]:.1f}s. Consider increasing cluster count or warehouse size.',
                    'warehouse': r['WAREHOUSE_NAME']
                })
        except Exception:
            pass
        
        # Check for spilling
        spill_query = """
        SELECT 
            WAREHOUSE_NAME,
            COUNT(*) as SPILLING_QUERIES
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        AND (BYTES_SPILLED_TO_LOCAL_STORAGE > 1073741824 OR BYTES_SPILLED_TO_REMOTE_STORAGE > 0)
        GROUP BY WAREHOUSE_NAME
        HAVING SPILLING_QUERIES > 5
        """
        try:
            spill_results = self.execute_query(spill_query)
            for r in spill_results:
                recommendations.append({
                    'category': 'Performance',
                    'severity': 'Medium',
                    'title': f'Query spilling detected on {r["WAREHOUSE_NAME"]}',
                    'description': f'{r["SPILLING_QUERIES"]} queries spilled to disk. Consider increasing warehouse size for memory-intensive queries.',
                    'warehouse': r['WAREHOUSE_NAME']
                })
        except Exception:
            pass
        
        return recommendations
    
    def get_queued_queries(self, days: int = 7) -> List[Dict]:
        """Get information about queries that were queued."""
        query = f"""
        SELECT 
            QUERY_ID,
            QUERY_TEXT,
            USER_NAME,
            WAREHOUSE_NAME,
            START_TIME,
            TOTAL_ELAPSED_TIME / 1000 as TOTAL_SEC,
            QUEUED_OVERLOAD_TIME / 1000 as QUEUE_SEC,
            QUEUED_PROVISIONING_TIME / 1000 as PROVISIONING_SEC,
            EXECUTION_TIME / 1000 as EXECUTION_SEC
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND (QUEUED_OVERLOAD_TIME > 1000 OR QUEUED_PROVISIONING_TIME > 1000)
        ORDER BY QUEUED_OVERLOAD_TIME + QUEUED_PROVISIONING_TIME DESC
        LIMIT 100
        """
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def get_hourly_credit_usage(self, days: int = 7) -> List[Dict]:
        """Get hourly credit usage pattern."""
        query = f"""
        SELECT 
            EXTRACT(HOUR FROM START_TIME) as HOUR_OF_DAY,
            EXTRACT(DAYOFWEEK FROM START_TIME) as DAY_OF_WEEK,
            AVG(CREDITS_USED) as AVG_CREDITS,
            SUM(CREDITS_USED) as TOTAL_CREDITS
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY EXTRACT(HOUR FROM START_TIME), EXTRACT(DAYOFWEEK FROM START_TIME)
        ORDER BY DAY_OF_WEEK, HOUR_OF_DAY
        """
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def _serialize_results(self, results: List[Dict]) -> List[Dict]:
        """Serialize results to JSON-compatible format."""
        serialized = []
        for row in results:
            new_row = {}
            for key, value in row.items():
                if isinstance(value, datetime):
                    new_row[key] = value.isoformat()
                elif value is None:
                    new_row[key] = None
                elif isinstance(value, (int, float)):
                    new_row[key] = value
                else:
                    new_row[key] = str(value)
            serialized.append(new_row)
        return serialized
