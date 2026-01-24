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
    
    # ================================================================
    # NEW FEATURES - User Analytics, Forecasting, Data Freshness, etc.
    # ================================================================
    
    def get_user_analytics(self, days: int = 30) -> Dict:
        """Get user-level analytics: top users by credits, queries, and failed queries."""
        
        # Top users by estimated credit consumption
        top_users_query = f"""
        SELECT 
            USER_NAME,
            COUNT(*) as QUERY_COUNT,
            SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 as TOTAL_HOURS,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_QUERY_SEC,
            SUM(BYTES_SCANNED) / POWER(1024, 4) as TB_SCANNED,
            COUNT(CASE WHEN EXECUTION_STATUS = 'FAIL' THEN 1 END) as FAILED_QUERIES,
            COUNT(DISTINCT WAREHOUSE_NAME) as WAREHOUSES_USED,
            COUNT(DISTINCT DATABASE_NAME) as DATABASES_ACCESSED
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND USER_NAME IS NOT NULL
        GROUP BY USER_NAME
        ORDER BY TOTAL_HOURS DESC
        LIMIT 25
        """
        
        # User activity over time
        user_activity_query = f"""
        SELECT 
            DATE_TRUNC('day', START_TIME) as DATE,
            COUNT(DISTINCT USER_NAME) as ACTIVE_USERS,
            COUNT(*) as TOTAL_QUERIES
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY DATE_TRUNC('day', START_TIME)
        ORDER BY DATE
        """
        
        # Queries by role
        role_usage_query = f"""
        SELECT 
            ROLE_NAME,
            COUNT(*) as QUERY_COUNT,
            COUNT(DISTINCT USER_NAME) as UNIQUE_USERS,
            SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 as TOTAL_HOURS
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND ROLE_NAME IS NOT NULL
        GROUP BY ROLE_NAME
        ORDER BY QUERY_COUNT DESC
        LIMIT 15
        """
        
        return {
            'top_users': self._serialize_results(self.execute_query(top_users_query)),
            'activity_trend': self._serialize_results(self.execute_query(user_activity_query)),
            'role_usage': self._serialize_results(self.execute_query(role_usage_query))
        }
    
    def get_cost_forecast(self, days: int = 30, forecast_days: int = 30) -> Dict:
        """Forecast future costs based on historical trends."""
        
        # Daily credit usage for trend calculation
        daily_credits_query = f"""
        SELECT 
            DATE_TRUNC('day', START_TIME) as DATE,
            SUM(CREDITS_USED) as DAILY_CREDITS,
            SUM(CREDITS_USED_COMPUTE) as COMPUTE_CREDITS,
            SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_CREDITS
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY DATE_TRUNC('day', START_TIME)
        ORDER BY DATE
        """
        
        # Weekly comparison
        weekly_comparison_query = """
        SELECT 
            'This Week' as PERIOD,
            SUM(CREDITS_USED) as TOTAL_CREDITS,
            AVG(CREDITS_USED) as AVG_HOURLY_CREDITS
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        UNION ALL
        SELECT 
            'Last Week' as PERIOD,
            SUM(CREDITS_USED) as TOTAL_CREDITS,
            AVG(CREDITS_USED) as AVG_HOURLY_CREDITS
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE START_TIME >= DATEADD(day, -14, CURRENT_TIMESTAMP())
        AND START_TIME < DATEADD(day, -7, CURRENT_TIMESTAMP())
        """
        
        daily_data = self.execute_query(daily_credits_query)
        weekly_data = self.execute_query(weekly_comparison_query)
        
        # Calculate forecast
        if daily_data:
            credits_list = [d['DAILY_CREDITS'] for d in daily_data if d['DAILY_CREDITS']]
            if credits_list:
                avg_daily = sum(credits_list) / len(credits_list)
                # Simple trend: compare first half vs second half
                mid = len(credits_list) // 2
                if mid > 0:
                    first_half_avg = sum(credits_list[:mid]) / mid
                    second_half_avg = sum(credits_list[mid:]) / (len(credits_list) - mid)
                    trend_factor = second_half_avg / first_half_avg if first_half_avg > 0 else 1.0
                else:
                    trend_factor = 1.0
                
                forecast = {
                    'avg_daily_credits': avg_daily,
                    'projected_30_day': avg_daily * forecast_days * min(trend_factor, 1.5),  # Cap growth
                    'trend_factor': trend_factor,
                    'trend_direction': 'increasing' if trend_factor > 1.05 else ('decreasing' if trend_factor < 0.95 else 'stable')
                }
            else:
                forecast = {'avg_daily_credits': 0, 'projected_30_day': 0, 'trend_factor': 1.0, 'trend_direction': 'stable'}
        else:
            forecast = {'avg_daily_credits': 0, 'projected_30_day': 0, 'trend_factor': 1.0, 'trend_direction': 'stable'}
        
        return {
            'daily_data': self._serialize_results(daily_data),
            'weekly_comparison': self._serialize_results(weekly_data),
            'forecast': forecast
        }
    
    def get_query_fingerprints(self, days: int = 7, min_count: int = 5) -> List[Dict]:
        """Group similar queries by their pattern (fingerprint) to identify optimization opportunities."""
        
        query = f"""
        SELECT 
            QUERY_PARAMETERIZED_HASH as FINGERPRINT,
            ANY_VALUE(QUERY_TEXT) as SAMPLE_QUERY,
            COUNT(*) as EXECUTION_COUNT,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_DURATION_SEC,
            MAX(TOTAL_ELAPSED_TIME) / 1000 as MAX_DURATION_SEC,
            MIN(TOTAL_ELAPSED_TIME) / 1000 as MIN_DURATION_SEC,
            STDDEV(TOTAL_ELAPSED_TIME) / 1000 as STDDEV_DURATION_SEC,
            SUM(BYTES_SCANNED) / POWER(1024, 3) as TOTAL_GB_SCANNED,
            AVG(BYTES_SCANNED) / POWER(1024, 3) as AVG_GB_SCANNED,
            COUNT(DISTINCT USER_NAME) as UNIQUE_USERS,
            COUNT(DISTINCT WAREHOUSE_NAME) as WAREHOUSES_USED,
            SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 as TOTAL_HOURS
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND QUERY_PARAMETERIZED_HASH IS NOT NULL
        AND QUERY_TYPE IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'MERGE')
        GROUP BY QUERY_PARAMETERIZED_HASH
        HAVING COUNT(*) >= {min_count}
        ORDER BY TOTAL_HOURS DESC
        LIMIT 50
        """
        
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def get_data_freshness(self) -> List[Dict]:
        """Monitor data freshness - when tables were last loaded/modified."""
        
        query = """
        SELECT 
            TABLE_CATALOG as DATABASE_NAME,
            TABLE_SCHEMA as SCHEMA_NAME,
            TABLE_NAME,
            ROW_COUNT,
            BYTES / POWER(1024, 3) as SIZE_GB,
            LAST_ALTERED,
            CREATED,
            DATEDIFF('hour', LAST_ALTERED, CURRENT_TIMESTAMP()) as HOURS_SINCE_UPDATE,
            CASE 
                WHEN DATEDIFF('hour', LAST_ALTERED, CURRENT_TIMESTAMP()) < 24 THEN 'Fresh'
                WHEN DATEDIFF('hour', LAST_ALTERED, CURRENT_TIMESTAMP()) < 168 THEN 'Recent'
                WHEN DATEDIFF('hour', LAST_ALTERED, CURRENT_TIMESTAMP()) < 720 THEN 'Stale'
                ELSE 'Very Stale'
            END as FRESHNESS_STATUS
        FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
        WHERE DELETED IS NULL
        AND TABLE_TYPE = 'BASE TABLE'
        AND TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA')
        AND ROW_COUNT > 0
        ORDER BY BYTES DESC
        LIMIT 100
        """
        
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def get_unused_objects(self, days: int = 30) -> Dict:
        """Identify unused warehouses and tables to optimize costs."""
        
        # Warehouses with no recent queries
        unused_warehouses_query = f"""
        SELECT w.name as WAREHOUSE_NAME, w.size as SIZE
        FROM TABLE(RESULT_SCAN(LAST_QUERY_ID(-1))) w
        WHERE w.name NOT IN (
            SELECT DISTINCT WAREHOUSE_NAME 
            FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
            WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
            AND WAREHOUSE_NAME IS NOT NULL
        )
        """
        
        # Get warehouse list first via SHOW WAREHOUSES
        try:
            warehouses = self.get_warehouse_configurations()
            warehouse_names = set(w['WAREHOUSE_NAME'] for w in warehouses)
            
            # Get recently used warehouses
            used_query = f"""
            SELECT DISTINCT WAREHOUSE_NAME 
            FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
            WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
            AND WAREHOUSE_NAME IS NOT NULL
            """
            used_results = self.execute_query(used_query)
            used_warehouses = set(r['WAREHOUSE_NAME'] for r in used_results)
            
            unused_warehouses = [
                {'WAREHOUSE_NAME': w['WAREHOUSE_NAME'], 'SIZE': w['SIZE']}
                for w in warehouses 
                if w['WAREHOUSE_NAME'] not in used_warehouses
            ]
        except:
            unused_warehouses = []
        
        # Tables not accessed recently
        unused_tables_query = f"""
        SELECT 
            t.TABLE_CATALOG as DATABASE_NAME,
            t.TABLE_SCHEMA as SCHEMA_NAME,
            t.TABLE_NAME,
            t.ROW_COUNT,
            t.BYTES / POWER(1024, 3) as SIZE_GB,
            t.LAST_ALTERED,
            DATEDIFF('day', t.LAST_ALTERED, CURRENT_TIMESTAMP()) as DAYS_SINCE_ALTERED
        FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES t
        WHERE t.DELETED IS NULL
        AND t.TABLE_TYPE = 'BASE TABLE'
        AND t.TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA')
        AND t.LAST_ALTERED < DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND t.BYTES > 1073741824  -- Only tables > 1GB
        ORDER BY t.BYTES DESC
        LIMIT 50
        """
        
        try:
            unused_tables = self.execute_query(unused_tables_query)
        except:
            unused_tables = []
        
        return {
            'unused_warehouses': unused_warehouses,
            'unused_tables': self._serialize_results(unused_tables)
        }
    
    def get_login_history(self, days: int = 7) -> Dict:
        """Monitor user login patterns and security events."""
        
        # Login summary
        login_summary_query = f"""
        SELECT 
            USER_NAME,
            COUNT(*) as LOGIN_COUNT,
            COUNT(DISTINCT CLIENT_IP) as UNIQUE_IPS,
            MAX(EVENT_TIMESTAMP) as LAST_LOGIN,
            COUNT(CASE WHEN IS_SUCCESS = 'NO' THEN 1 END) as FAILED_LOGINS
        FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
        WHERE EVENT_TIMESTAMP >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY USER_NAME
        ORDER BY LOGIN_COUNT DESC
        LIMIT 25
        """
        
        # Failed logins (potential security issues)
        failed_logins_query = f"""
        SELECT 
            EVENT_TIMESTAMP,
            USER_NAME,
            CLIENT_IP,
            REPORTED_CLIENT_TYPE,
            ERROR_CODE,
            ERROR_MESSAGE
        FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
        WHERE EVENT_TIMESTAMP >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND IS_SUCCESS = 'NO'
        ORDER BY EVENT_TIMESTAMP DESC
        LIMIT 50
        """
        
        # Login by hour pattern
        login_pattern_query = f"""
        SELECT 
            EXTRACT(HOUR FROM EVENT_TIMESTAMP) as HOUR_OF_DAY,
            COUNT(*) as LOGIN_COUNT
        FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
        WHERE EVENT_TIMESTAMP >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND IS_SUCCESS = 'YES'
        GROUP BY EXTRACT(HOUR FROM EVENT_TIMESTAMP)
        ORDER BY HOUR_OF_DAY
        """
        
        return {
            'summary': self._serialize_results(self.execute_query(login_summary_query)),
            'failed_logins': self._serialize_results(self.execute_query(failed_logins_query)),
            'hourly_pattern': self._serialize_results(self.execute_query(login_pattern_query))
        }
    
    def get_table_storage_details(self) -> List[Dict]:
        """Get detailed storage breakdown by table."""
        
        query = """
        SELECT 
            TABLE_CATALOG as DATABASE_NAME,
            TABLE_SCHEMA as SCHEMA_NAME,
            TABLE_NAME,
            ROW_COUNT,
            BYTES / POWER(1024, 3) as SIZE_GB,
            ACTIVE_BYTES / POWER(1024, 3) as ACTIVE_GB,
            TIME_TRAVEL_BYTES / POWER(1024, 3) as TIME_TRAVEL_GB,
            FAILSAFE_BYTES / POWER(1024, 3) as FAILSAFE_GB,
            RETAINED_FOR_CLONE_BYTES / POWER(1024, 3) as CLONE_GB,
            CLUSTERING_KEY,
            IS_TRANSIENT,
            CREATED,
            LAST_ALTERED
        FROM SNOWFLAKE.ACCOUNT_USAGE.TABLE_STORAGE_METRICS
        WHERE DELETED IS NULL
        AND TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA')
        ORDER BY BYTES DESC
        LIMIT 100
        """
        
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def get_week_over_week_comparison(self) -> Dict:
        """Compare key metrics between this week and last week."""
        
        # Credit comparison
        credit_comparison_query = """
        SELECT 
            SUM(CASE WHEN START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP()) THEN CREDITS_USED ELSE 0 END) as THIS_WEEK_CREDITS,
            SUM(CASE WHEN START_TIME >= DATEADD(day, -14, CURRENT_TIMESTAMP()) AND START_TIME < DATEADD(day, -7, CURRENT_TIMESTAMP()) THEN CREDITS_USED ELSE 0 END) as LAST_WEEK_CREDITS
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE START_TIME >= DATEADD(day, -14, CURRENT_TIMESTAMP())
        """
        
        # Query performance comparison
        query_comparison = """
        SELECT 
            'This Week' as PERIOD,
            COUNT(*) as QUERY_COUNT,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_DURATION_SEC,
            COUNT(CASE WHEN EXECUTION_STATUS = 'FAIL' THEN 1 END) as FAILED_QUERIES,
            SUM(BYTES_SCANNED) / POWER(1024, 4) as TB_SCANNED
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        UNION ALL
        SELECT 
            'Last Week' as PERIOD,
            COUNT(*) as QUERY_COUNT,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_DURATION_SEC,
            COUNT(CASE WHEN EXECUTION_STATUS = 'FAIL' THEN 1 END) as FAILED_QUERIES,
            SUM(BYTES_SCANNED) / POWER(1024, 4) as TB_SCANNED
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -14, CURRENT_TIMESTAMP())
        AND START_TIME < DATEADD(day, -7, CURRENT_TIMESTAMP())
        """
        
        # User activity comparison
        user_comparison = """
        SELECT 
            COUNT(DISTINCT CASE WHEN START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP()) THEN USER_NAME END) as THIS_WEEK_USERS,
            COUNT(DISTINCT CASE WHEN START_TIME >= DATEADD(day, -14, CURRENT_TIMESTAMP()) AND START_TIME < DATEADD(day, -7, CURRENT_TIMESTAMP()) THEN USER_NAME END) as LAST_WEEK_USERS
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -14, CURRENT_TIMESTAMP())
        """
        
        credit_data = self.execute_query(credit_comparison_query)
        query_data = self.execute_query(query_comparison)
        user_data = self.execute_query(user_comparison)
        
        # Calculate percentage changes
        result = {
            'credits': self._serialize_results(credit_data),
            'queries': self._serialize_results(query_data),
            'users': self._serialize_results(user_data)
        }
        
        if credit_data and credit_data[0]['LAST_WEEK_CREDITS'] and credit_data[0]['LAST_WEEK_CREDITS'] > 0:
            this_week = credit_data[0]['THIS_WEEK_CREDITS'] or 0
            last_week = credit_data[0]['LAST_WEEK_CREDITS']
            result['credit_change_pct'] = ((this_week - last_week) / last_week) * 100
        else:
            result['credit_change_pct'] = 0
        
        return result
    
    def get_query_optimization_opportunities(self) -> List[Dict]:
        """Identify queries that could benefit from optimization."""
        
        # Queries with full table scans (high bytes scanned relative to result)
        full_scan_query = """
        SELECT 
            QUERY_ID,
            QUERY_TEXT,
            USER_NAME,
            WAREHOUSE_NAME,
            DATABASE_NAME,
            TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SEC,
            BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED,
            ROWS_PRODUCED,
            PARTITIONS_SCANNED,
            PARTITIONS_TOTAL,
            ROUND((PARTITIONS_SCANNED / NULLIF(PARTITIONS_TOTAL, 0)) * 100, 1) as PARTITION_SCAN_PCT,
            'Full Table Scan' as ISSUE_TYPE,
            'Consider adding clustering keys or filtering on partitioned columns' as RECOMMENDATION
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        AND PARTITIONS_TOTAL > 100
        AND PARTITIONS_SCANNED >= PARTITIONS_TOTAL * 0.9
        AND TOTAL_ELAPSED_TIME > 30000
        ORDER BY BYTES_SCANNED DESC
        LIMIT 20
        """
        
        # Queries with high spilling
        spill_query = """
        SELECT 
            QUERY_ID,
            QUERY_TEXT,
            USER_NAME,
            WAREHOUSE_NAME,
            DATABASE_NAME,
            TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SEC,
            BYTES_SPILLED_TO_LOCAL_STORAGE / POWER(1024, 3) as LOCAL_SPILL_GB,
            BYTES_SPILLED_TO_REMOTE_STORAGE / POWER(1024, 3) as REMOTE_SPILL_GB,
            'Memory Spilling' as ISSUE_TYPE,
            'Consider using a larger warehouse or optimizing query to reduce memory usage' as RECOMMENDATION
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        AND (BYTES_SPILLED_TO_LOCAL_STORAGE > 5368709120 OR BYTES_SPILLED_TO_REMOTE_STORAGE > 0)
        ORDER BY BYTES_SPILLED_TO_REMOTE_STORAGE DESC, BYTES_SPILLED_TO_LOCAL_STORAGE DESC
        LIMIT 20
        """
        
        # Queries with SELECT *
        select_star_query = """
        SELECT 
            QUERY_ID,
            QUERY_TEXT,
            USER_NAME,
            WAREHOUSE_NAME,
            DATABASE_NAME,
            TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SEC,
            BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED,
            'SELECT * Usage' as ISSUE_TYPE,
            'Consider selecting only required columns to reduce data scanned' as RECOMMENDATION
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        AND QUERY_TYPE = 'SELECT'
        AND QUERY_TEXT ILIKE '%SELECT *%FROM%'
        AND BYTES_SCANNED > 1073741824
        ORDER BY BYTES_SCANNED DESC
        LIMIT 20
        """
        
        full_scans = self.execute_query(full_scan_query)
        spills = self.execute_query(spill_query)
        select_stars = self.execute_query(select_star_query)
        
        all_issues = full_scans + spills + select_stars
        return self._serialize_results(all_issues)
    
    # ================================================================
    # DATABASE-SPECIFIC MONITORING
    # ================================================================
    
    def get_database_list(self) -> List[Dict]:
        """Get list of all databases with basic metrics."""
        query = """
        SELECT 
            DATABASE_NAME,
            DATABASE_OWNER,
            CREATED,
            LAST_ALTERED,
            COMMENT
        FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASES
        WHERE DELETED IS NULL
        ORDER BY DATABASE_NAME
        """
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def get_database_overview(self, database_name: str, days: int = 30) -> Dict:
        """Get comprehensive overview metrics for a specific database."""
        
        # Query metrics for this database
        query_metrics = f"""
        SELECT 
            COUNT(*) as TOTAL_QUERIES,
            COUNT(DISTINCT USER_NAME) as UNIQUE_USERS,
            COUNT(DISTINCT WAREHOUSE_NAME) as WAREHOUSES_USED,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_QUERY_SEC,
            SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 as TOTAL_QUERY_HOURS,
            SUM(BYTES_SCANNED) / POWER(1024, 4) as TB_SCANNED,
            SUM(BYTES_WRITTEN) / POWER(1024, 4) as TB_WRITTEN,
            COUNT(CASE WHEN EXECUTION_STATUS = 'FAIL' THEN 1 END) as FAILED_QUERIES,
            AVG(CASE WHEN QUEUED_OVERLOAD_TIME > 0 THEN QUEUED_OVERLOAD_TIME END) / 1000 as AVG_QUEUE_SEC
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        """
        
        # Storage for this database
        storage_query = f"""
        SELECT 
            COALESCE(SUM(AVERAGE_DATABASE_BYTES), 0) / POWER(1024, 4) as STORAGE_TB,
            COALESCE(SUM(AVERAGE_FAILSAFE_BYTES), 0) / POWER(1024, 3) as FAILSAFE_GB
        FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND USAGE_DATE = (SELECT MAX(USAGE_DATE) FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY)
        """
        
        # Table and schema counts
        object_counts = f"""
        SELECT 
            COUNT(DISTINCT TABLE_SCHEMA) as SCHEMA_COUNT,
            COUNT(*) as TABLE_COUNT,
            SUM(ROW_COUNT) as TOTAL_ROWS
        FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
        WHERE TABLE_CATALOG = '{database_name}'
        AND DELETED IS NULL
        AND TABLE_TYPE = 'BASE TABLE'
        """
        
        query_results = self.execute_query(query_metrics)
        storage_results = self.execute_query(storage_query)
        object_results = self.execute_query(object_counts)
        
        return {
            'query_metrics': self._serialize_results(query_results)[0] if query_results else {},
            'storage': self._serialize_results(storage_results)[0] if storage_results else {},
            'objects': self._serialize_results(object_results)[0] if object_results else {}
        }
    
    def get_database_cost_analysis(self, database_name: str, days: int = 30) -> Dict:
        """Analyze costs associated with queries on a specific database."""
        
        # Estimate credits by warehouse usage for this database
        # Note: Credits are charged at warehouse level, so we estimate based on query time
        cost_by_warehouse = f"""
        SELECT 
            WAREHOUSE_NAME,
            MAX(WAREHOUSE_SIZE) as WAREHOUSE_SIZE,
            COUNT(*) as QUERY_COUNT,
            SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 as TOTAL_HOURS,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_QUERY_SEC,
            SUM(BYTES_SCANNED) / POWER(1024, 4) as TB_SCANNED
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND WAREHOUSE_NAME IS NOT NULL
        GROUP BY WAREHOUSE_NAME
        ORDER BY TOTAL_HOURS DESC
        """
        
        # Daily query volume
        daily_volume = f"""
        SELECT 
            DATE_TRUNC('day', START_TIME) as DATE,
            COUNT(*) as QUERY_COUNT,
            SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 as TOTAL_HOURS,
            SUM(BYTES_SCANNED) / POWER(1024, 3) as GB_SCANNED,
            COUNT(DISTINCT USER_NAME) as UNIQUE_USERS
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY DATE_TRUNC('day', START_TIME)
        ORDER BY DATE
        """
        
        # Cost by user
        cost_by_user = f"""
        SELECT 
            USER_NAME,
            COUNT(*) as QUERY_COUNT,
            SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 as TOTAL_HOURS,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_QUERY_SEC,
            SUM(BYTES_SCANNED) / POWER(1024, 4) as TB_SCANNED
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND USER_NAME IS NOT NULL
        GROUP BY USER_NAME
        ORDER BY TOTAL_HOURS DESC
        LIMIT 20
        """
        
        return {
            'by_warehouse': self._serialize_results(self.execute_query(cost_by_warehouse)),
            'daily_volume': self._serialize_results(self.execute_query(daily_volume)),
            'by_user': self._serialize_results(self.execute_query(cost_by_user))
        }
    
    def get_database_slow_queries(self, database_name: str, days: int = 7, threshold_sec: int = 30) -> List[Dict]:
        """Get slow queries for a specific database."""
        query = f"""
        SELECT 
            QUERY_ID,
            QUERY_TEXT,
            USER_NAME,
            WAREHOUSE_NAME,
            SCHEMA_NAME,
            QUERY_TYPE,
            TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SEC,
            EXECUTION_TIME / 1000 as EXECUTION_SEC,
            COMPILATION_TIME / 1000 as COMPILE_SEC,
            QUEUED_OVERLOAD_TIME / 1000 as QUEUE_SEC,
            BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED,
            ROWS_PRODUCED,
            PARTITIONS_SCANNED,
            PARTITIONS_TOTAL,
            EXECUTION_STATUS,
            START_TIME
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND TOTAL_ELAPSED_TIME >= {threshold_sec * 1000}
        ORDER BY TOTAL_ELAPSED_TIME DESC
        LIMIT 100
        """
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def get_database_bottlenecks(self, database_name: str, days: int = 7) -> Dict:
        """Identify bottlenecks for a specific database."""
        
        # Queries with queue time
        queuing_issues = f"""
        SELECT 
            WAREHOUSE_NAME,
            COUNT(*) as QUEUED_QUERIES,
            AVG(QUEUED_OVERLOAD_TIME) / 1000 as AVG_QUEUE_SEC,
            MAX(QUEUED_OVERLOAD_TIME) / 1000 as MAX_QUEUE_SEC,
            SUM(QUEUED_OVERLOAD_TIME) / 1000 / 60 as TOTAL_QUEUE_MINUTES
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND QUEUED_OVERLOAD_TIME > 0
        GROUP BY WAREHOUSE_NAME
        ORDER BY TOTAL_QUEUE_MINUTES DESC
        """
        
        # Queries with spilling
        spilling_issues = f"""
        SELECT 
            WAREHOUSE_NAME,
            COUNT(*) as SPILLING_QUERIES,
            SUM(BYTES_SPILLED_TO_LOCAL_STORAGE) / POWER(1024, 3) as LOCAL_SPILL_GB,
            SUM(BYTES_SPILLED_TO_REMOTE_STORAGE) / POWER(1024, 3) as REMOTE_SPILL_GB
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND (BYTES_SPILLED_TO_LOCAL_STORAGE > 0 OR BYTES_SPILLED_TO_REMOTE_STORAGE > 0)
        GROUP BY WAREHOUSE_NAME
        ORDER BY REMOTE_SPILL_GB DESC, LOCAL_SPILL_GB DESC
        """
        
        # High compilation time (often indicates complex queries or missing optimizations)
        compilation_issues = f"""
        SELECT 
            QUERY_TYPE,
            COUNT(*) as HIGH_COMPILE_QUERIES,
            AVG(COMPILATION_TIME) / 1000 as AVG_COMPILE_SEC,
            MAX(COMPILATION_TIME) / 1000 as MAX_COMPILE_SEC
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND COMPILATION_TIME > 5000
        GROUP BY QUERY_TYPE
        ORDER BY AVG_COMPILE_SEC DESC
        """
        
        # Failed queries
        failures = f"""
        SELECT 
            ERROR_CODE,
            ERROR_MESSAGE,
            COUNT(*) as FAILURE_COUNT,
            COUNT(DISTINCT USER_NAME) as AFFECTED_USERS
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND EXECUTION_STATUS = 'FAIL'
        GROUP BY ERROR_CODE, ERROR_MESSAGE
        ORDER BY FAILURE_COUNT DESC
        LIMIT 10
        """
        
        # Full table scans
        full_scans = f"""
        SELECT 
            COUNT(*) as FULL_SCAN_COUNT,
            AVG(BYTES_SCANNED) / POWER(1024, 3) as AVG_GB_SCANNED,
            SUM(BYTES_SCANNED) / POWER(1024, 4) as TOTAL_TB_SCANNED
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND PARTITIONS_TOTAL > 100
        AND PARTITIONS_SCANNED >= PARTITIONS_TOTAL * 0.9
        AND TOTAL_ELAPSED_TIME > 10000
        """
        
        return {
            'queuing': self._serialize_results(self.execute_query(queuing_issues)),
            'spilling': self._serialize_results(self.execute_query(spilling_issues)),
            'compilation': self._serialize_results(self.execute_query(compilation_issues)),
            'failures': self._serialize_results(self.execute_query(failures)),
            'full_scans': self._serialize_results(self.execute_query(full_scans))
        }
    
    def get_database_table_analysis(self, database_name: str) -> List[Dict]:
        """Get detailed table analysis for a database."""
        query = f"""
        SELECT 
            TABLE_SCHEMA,
            TABLE_NAME,
            ROW_COUNT,
            BYTES / POWER(1024, 3) as SIZE_GB,
            CLUSTERING_KEY,
            CREATED,
            LAST_ALTERED,
            DATEDIFF('day', LAST_ALTERED, CURRENT_TIMESTAMP()) as DAYS_SINCE_UPDATE,
            CASE 
                WHEN DATEDIFF('hour', LAST_ALTERED, CURRENT_TIMESTAMP()) < 24 THEN 'Fresh'
                WHEN DATEDIFF('hour', LAST_ALTERED, CURRENT_TIMESTAMP()) < 168 THEN 'Recent'
                WHEN DATEDIFF('hour', LAST_ALTERED, CURRENT_TIMESTAMP()) < 720 THEN 'Stale'
                ELSE 'Very Stale'
            END as FRESHNESS
        FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
        WHERE TABLE_CATALOG = '{database_name}'
        AND DELETED IS NULL
        AND TABLE_TYPE = 'BASE TABLE'
        AND TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA')
        ORDER BY BYTES DESC NULLS LAST
        LIMIT 100
        """
        results = self.execute_query(query)
        return self._serialize_results(results)
    
    def get_database_query_patterns(self, database_name: str, days: int = 7) -> Dict:
        """Analyze query patterns for a specific database."""
        
        # By hour
        hourly = f"""
        SELECT 
            EXTRACT(HOUR FROM START_TIME) as HOUR_OF_DAY,
            COUNT(*) as QUERY_COUNT,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_DURATION_SEC
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY EXTRACT(HOUR FROM START_TIME)
        ORDER BY HOUR_OF_DAY
        """
        
        # By query type
        by_type = f"""
        SELECT 
            QUERY_TYPE,
            COUNT(*) as QUERY_COUNT,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_DURATION_SEC,
            SUM(BYTES_SCANNED) / POWER(1024, 4) as TB_SCANNED
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY QUERY_TYPE
        ORDER BY QUERY_COUNT DESC
        """
        
        # By schema
        by_schema = f"""
        SELECT 
            SCHEMA_NAME,
            COUNT(*) as QUERY_COUNT,
            COUNT(DISTINCT USER_NAME) as UNIQUE_USERS,
            AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_DURATION_SEC,
            SUM(BYTES_SCANNED) / POWER(1024, 3) as GB_SCANNED
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND SCHEMA_NAME IS NOT NULL
        GROUP BY SCHEMA_NAME
        ORDER BY QUERY_COUNT DESC
        """
        
        return {
            'hourly': self._serialize_results(self.execute_query(hourly)),
            'by_type': self._serialize_results(self.execute_query(by_type)),
            'by_schema': self._serialize_results(self.execute_query(by_schema))
        }
    
    def get_database_optimization_opportunities(self, database_name: str, days: int = 7) -> List[Dict]:
        """Get optimization opportunities specific to a database."""
        
        # Expensive queries
        expensive = f"""
        SELECT 
            QUERY_ID,
            QUERY_TEXT,
            USER_NAME,
            WAREHOUSE_NAME,
            SCHEMA_NAME,
            TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SEC,
            BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED,
            PARTITIONS_SCANNED,
            PARTITIONS_TOTAL,
            BYTES_SPILLED_TO_LOCAL_STORAGE / POWER(1024, 3) as LOCAL_SPILL_GB,
            BYTES_SPILLED_TO_REMOTE_STORAGE / POWER(1024, 3) as REMOTE_SPILL_GB,
            CASE 
                WHEN PARTITIONS_TOTAL > 100 AND PARTITIONS_SCANNED >= PARTITIONS_TOTAL * 0.9 THEN 'Full Table Scan'
                WHEN BYTES_SPILLED_TO_REMOTE_STORAGE > 0 THEN 'Remote Spilling'
                WHEN BYTES_SPILLED_TO_LOCAL_STORAGE > 5368709120 THEN 'Heavy Local Spilling'
                WHEN QUERY_TEXT ILIKE '%SELECT *%FROM%' AND BYTES_SCANNED > 1073741824 THEN 'SELECT * on Large Table'
                WHEN COMPILATION_TIME > 10000 THEN 'High Compilation Time'
                ELSE 'High Resource Usage'
            END as ISSUE_TYPE,
            START_TIME
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE DATABASE_NAME = '{database_name}'
        AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND (
            (PARTITIONS_TOTAL > 100 AND PARTITIONS_SCANNED >= PARTITIONS_TOTAL * 0.9 AND TOTAL_ELAPSED_TIME > 30000)
            OR BYTES_SPILLED_TO_REMOTE_STORAGE > 0
            OR BYTES_SPILLED_TO_LOCAL_STORAGE > 5368709120
            OR (QUERY_TEXT ILIKE '%SELECT *%FROM%' AND BYTES_SCANNED > 1073741824)
            OR COMPILATION_TIME > 10000
        )
        ORDER BY TOTAL_ELAPSED_TIME DESC
        LIMIT 50
        """
        
        results = self.execute_query(expensive)
        
        # Add recommendations
        for r in results:
            issue = r.get('ISSUE_TYPE', '')
            if issue == 'Full Table Scan':
                r['RECOMMENDATION'] = 'Add clustering keys or filters on partition columns'
            elif issue == 'Remote Spilling':
                r['RECOMMENDATION'] = 'Use larger warehouse or optimize query to reduce memory'
            elif issue == 'Heavy Local Spilling':
                r['RECOMMENDATION'] = 'Consider warehouse size upgrade or query optimization'
            elif issue == 'SELECT * on Large Table':
                r['RECOMMENDATION'] = 'Select only required columns to reduce data scanned'
            elif issue == 'High Compilation Time':
                r['RECOMMENDATION'] = 'Simplify query or break into smaller parts'
            else:
                r['RECOMMENDATION'] = 'Review query for optimization opportunities'
        
        return self._serialize_results(results)
    
    def get_database_recommendations(self, database_name: str, days: int = 30) -> List[Dict]:
        """Generate recommendations specific to a database."""
        recommendations = []
        
        # Get metrics for analysis
        try:
            overview = self.get_database_overview(database_name, days)
            bottlenecks = self.get_database_bottlenecks(database_name, min(days, 7))
            
            query_metrics = overview.get('query_metrics', {})
            
            # Check for high failure rate
            total_queries = query_metrics.get('TOTAL_QUERIES', 0)
            failed_queries = query_metrics.get('FAILED_QUERIES', 0)
            if total_queries > 0 and failed_queries / total_queries > 0.05:
                recommendations.append({
                    'severity': 'High',
                    'category': 'Reliability',
                    'title': 'High Query Failure Rate',
                    'description': f'{failed_queries} failed queries ({(failed_queries/total_queries*100):.1f}% failure rate). Review error patterns and fix root causes.',
                    'metric': f'{failed_queries} failures'
                })
            
            # Check for queue time issues
            avg_queue = query_metrics.get('AVG_QUEUE_SEC')
            if avg_queue and avg_queue > 5:
                recommendations.append({
                    'severity': 'High',
                    'category': 'Performance',
                    'title': 'Significant Queue Times',
                    'description': f'Average queue time of {avg_queue:.1f}s indicates warehouse contention. Consider scaling warehouses or spreading workloads.',
                    'metric': f'{avg_queue:.1f}s avg queue'
                })
            
            # Check for spilling issues
            spilling = bottlenecks.get('spilling', [])
            total_remote_spill = sum(s.get('REMOTE_SPILL_GB', 0) or 0 for s in spilling)
            if total_remote_spill > 10:
                recommendations.append({
                    'severity': 'High',
                    'category': 'Cost',
                    'title': 'Heavy Remote Spilling',
                    'description': f'{total_remote_spill:.1f} GB spilled to remote storage. This is expensive and slow. Increase warehouse size or optimize queries.',
                    'metric': f'{total_remote_spill:.1f} GB remote spill'
                })
            
            # Check full table scan issues
            full_scans = bottlenecks.get('full_scans', [])
            if full_scans and full_scans[0].get('FULL_SCAN_COUNT', 0) > 100:
                count = full_scans[0]['FULL_SCAN_COUNT']
                recommendations.append({
                    'severity': 'Medium',
                    'category': 'Performance',
                    'title': 'Frequent Full Table Scans',
                    'description': f'{count} queries performed full table scans. Add clustering keys or improve WHERE clause filters.',
                    'metric': f'{count} full scans'
                })
            
            # Check for heavy TB scanned
            tb_scanned = query_metrics.get('TB_SCANNED', 0)
            if tb_scanned and tb_scanned > 10:
                recommendations.append({
                    'severity': 'Medium',
                    'category': 'Cost',
                    'title': 'High Data Scanning Volume',
                    'description': f'{tb_scanned:.1f} TB scanned in {days} days. Review queries for partition pruning and column selection.',
                    'metric': f'{tb_scanned:.1f} TB scanned'
                })
            
            # Check compilation issues
            compilation = bottlenecks.get('compilation', [])
            high_compile_count = sum(c.get('HIGH_COMPILE_QUERIES', 0) or 0 for c in compilation)
            if high_compile_count > 50:
                recommendations.append({
                    'severity': 'Low',
                    'category': 'Performance',
                    'title': 'Complex Query Compilation',
                    'description': f'{high_compile_count} queries had high compilation time (>5s). Consider simplifying complex queries.',
                    'metric': f'{high_compile_count} slow compiles'
                })
            
        except Exception as e:
            recommendations.append({
                'severity': 'Low',
                'category': 'System',
                'title': 'Analysis Error',
                'description': f'Could not complete full analysis: {str(e)}',
                'metric': 'N/A'
            })
        
        return recommendations
    
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
