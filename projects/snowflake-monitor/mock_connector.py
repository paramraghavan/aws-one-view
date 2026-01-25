"""
Mock Snowflake Connector for Demo Mode
Provides sample data for testing the dashboard without a Snowflake connection.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List


class MockSnowflakeMonitor:
    """Mock monitor class that returns sample data for demonstration."""
    
    def __init__(self, config: Dict[str, str] = None):
        self.config = config or {}
    
    def get_overview_metrics(self) -> Dict:
        """Get high-level overview metrics."""
        return {
            'total_credits_30d': random.uniform(1500, 3500),
            'active_warehouses': random.randint(5, 12),
            'total_storage_tb': random.uniform(2.5, 15.0),
            'queries_24h': random.randint(15000, 45000),
            'avg_query_time_sec': random.uniform(1.5, 8.5),
            'failed_queries_24h': random.randint(10, 150)
        }
    
    def get_warehouse_costs(self, days: int = 30) -> List[Dict]:
        """Get warehouse cost breakdown."""
        warehouses = ['ANALYTICS_WH', 'ETL_WH', 'REPORTING_WH', 'DEV_WH', 'DATA_SCIENCE_WH', 'TRANSFORM_WH']
        return [
            {
                'WAREHOUSE_NAME': wh,
                'TOTAL_CREDITS': random.uniform(100, 800) * (days / 30),
                'COMPUTE_CREDITS': random.uniform(80, 700) * (days / 30),
                'CLOUD_SERVICES_CREDITS': random.uniform(5, 50) * (days / 30),
                'ACTIVE_DAYS': min(days, random.randint(15, days)),
                'AVG_HOURLY_CREDITS': random.uniform(0.5, 3.5)
            }
            for wh in warehouses
        ]
    
    def get_warehouse_usage(self, days: int = 7) -> List[Dict]:
        """Get warehouse usage statistics."""
        warehouses = ['ANALYTICS_WH', 'ETL_WH', 'REPORTING_WH']
        results = []
        base_time = datetime.now()
        
        for wh in warehouses:
            for i in range(days * 24):
                results.append({
                    'WAREHOUSE_NAME': wh,
                    'HOUR': (base_time - timedelta(hours=i)).isoformat(),
                    'CREDITS_USED': random.uniform(0.1, 2.5)
                })
        
        return results
    
    def get_long_running_queries(self, threshold_seconds: int = 60, limit: int = 50) -> List[Dict]:
        """Get long-running queries."""
        users = ['ANALYTICS_USER', 'ETL_SERVICE', 'REPORT_USER', 'DATA_SCIENTIST', 'ADMIN']
        warehouses = ['ANALYTICS_WH', 'ETL_WH', 'REPORTING_WH']
        databases = ['ANALYTICS_DB', 'RAW_DATA', 'WAREHOUSE_DB', 'REPORTING_DB']
        statuses = ['SUCCESS', 'SUCCESS', 'SUCCESS', 'FAIL']
        
        return [
            {
                'QUERY_ID': f'01b{i:05d}-0000-{random.randint(1000,9999)}-0000-{random.randint(10000,99999)}',
                'QUERY_TEXT': f'SELECT * FROM {random.choice(["fact_sales", "dim_customer", "fact_orders", "stg_events"])} WHERE date_col > DATEADD(day, -{random.randint(1,30)}, CURRENT_DATE()) {"GROUP BY category" if random.random() > 0.5 else ""}',
                'USER_NAME': random.choice(users),
                'WAREHOUSE_NAME': random.choice(warehouses),
                'DATABASE_NAME': random.choice(databases),
                'SCHEMA_NAME': 'PUBLIC',
                'EXECUTION_STATUS': random.choice(statuses),
                'START_TIME': (datetime.now() - timedelta(hours=random.randint(1, 168))).isoformat(),
                'END_TIME': (datetime.now() - timedelta(hours=random.randint(0, 167))).isoformat(),
                'ELAPSED_SECONDS': random.uniform(threshold_seconds, threshold_seconds * 10),
                'GB_SCANNED': random.uniform(0.5, 50),
                'ROWS_PRODUCED': random.randint(1000, 10000000),
                'COMPILATION_SECONDS': random.uniform(0.1, 5),
                'EXECUTION_SECONDS': random.uniform(threshold_seconds - 10, threshold_seconds * 8),
                'QUEUED_PROVISIONING_SECONDS': random.uniform(0, 10),
                'QUEUED_OVERLOAD_SECONDS': random.uniform(0, 30)
            }
            for i in range(min(limit, 50))
        ]
    
    def get_expensive_queries(self, days: int = 7, limit: int = 50) -> List[Dict]:
        """Get most expensive queries by estimated credits."""
        users = ['ETL_SERVICE', 'ANALYTICS_USER', 'DATA_SCIENTIST', 'REPORT_USER']
        warehouses = ['ANALYTICS_WH', 'ETL_WH', 'DATA_SCIENCE_WH']
        databases = ['ANALYTICS_DB', 'RAW_DATA', 'WAREHOUSE_DB']
        
        return [
            {
                'QUERY_ID': f'01c{i:05d}-0000-{random.randint(1000,9999)}-0000-{random.randint(10000,99999)}',
                'QUERY_TEXT': f'INSERT INTO {random.choice(["fact_sales", "agg_daily_metrics", "dim_product"])} SELECT * FROM staging_{random.choice(["orders", "events", "users"])} WHERE load_date = CURRENT_DATE()',
                'USER_NAME': random.choice(users),
                'WAREHOUSE_NAME': random.choice(warehouses),
                'DATABASE_NAME': random.choice(databases),
                'START_TIME': (datetime.now() - timedelta(hours=random.randint(1, days * 24))).isoformat(),
                'ELAPSED_SECONDS': random.uniform(30, 600),
                'GB_SCANNED': random.uniform(10, 500),
                'GB_WRITTEN': random.uniform(1, 100),
                'ROWS_PRODUCED': random.randint(100000, 50000000),
                'CREDITS_USED_CLOUD_SERVICES': random.uniform(0.01, 0.5)
            }
            for i in range(min(limit, 50))
        ]
    
    def get_storage_usage(self) -> List[Dict]:
        """Get storage usage by database."""
        databases = ['ANALYTICS_DB', 'RAW_DATA', 'WAREHOUSE_DB', 'REPORTING_DB', 'DEV_DB', 'STAGING_DB']
        return [
            {
                'DATABASE_NAME': db,
                'DATABASE_GB': random.uniform(50, 2000),
                'FAILSAFE_GB': random.uniform(10, 400),
                'TOTAL_GB': random.uniform(60, 2400)
            }
            for db in databases
        ]
    
    def get_cluster_load(self, days: int = 7) -> List[Dict]:
        """Get cluster load and concurrency metrics."""
        warehouses = ['ANALYTICS_WH', 'ETL_WH', 'REPORTING_WH']
        results = []
        base_time = datetime.now()
        
        for wh in warehouses:
            for i in range(days * 24):
                results.append({
                    'WAREHOUSE_NAME': wh,
                    'HOUR': (base_time - timedelta(hours=i)).isoformat(),
                    'AVG_CONCURRENT_QUERIES': random.uniform(0.5, 8),
                    'MAX_CONCURRENT_QUERIES': random.uniform(2, 15),
                    'AVG_QUEUED': random.uniform(0, 2),
                    'MAX_QUEUED': random.uniform(0, 10),
                    'AVG_QUEUED_PROVISIONING': random.uniform(0, 1),
                    'AVG_BLOCKED': random.uniform(0, 0.5)
                })
        
        return results
    
    def get_warehouse_configurations(self) -> List[Dict]:
        """Get warehouse configurations including auto-suspend settings."""
        configs = [
            ('ANALYTICS_WH', 'STARTED', 'LARGE', 'STANDARD', 1, 3, 'STANDARD', 300, True),
            ('ETL_WH', 'STARTED', 'X-LARGE', 'STANDARD', 1, 1, 'STANDARD', 60, True),
            ('REPORTING_WH', 'SUSPENDED', 'MEDIUM', 'STANDARD', 1, 2, 'ECONOMY', 120, True),
            ('DEV_WH', 'SUSPENDED', 'SMALL', 'STANDARD', 1, 1, 'STANDARD', 60, True),
            ('DATA_SCIENCE_WH', 'STARTED', 'LARGE', 'STANDARD', 1, 4, 'STANDARD', 300, True),
            ('TRANSFORM_WH', 'SUSPENDED', 'MEDIUM', 'STANDARD', 1, 1, 'STANDARD', 180, True),
        ]
        
        return [
            {
                'WAREHOUSE_NAME': c[0],
                'STATE': c[1],
                'SIZE': c[2],
                'TYPE': c[3],
                'MIN_CLUSTER_COUNT': c[4],
                'MAX_CLUSTER_COUNT': c[5],
                'SCALING_POLICY': c[6],
                'AUTO_SUSPEND': c[7],
                'AUTO_RESUME': c[8],
                'RESOURCE_MONITOR': None,
                'CREATED_ON': (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat(),
                'OWNER': 'SYSADMIN'
            }
            for c in configs
        ]
    
    def analyze_query_patterns(self, days: int = 7) -> Dict:
        """Analyze query patterns for potential bottlenecks."""
        return {
            'hourly': [
                {
                    'HOUR_OF_DAY': h,
                    'QUERY_COUNT': int(random.gauss(2000, 500) * (1 + 0.5 * (1 if 9 <= h <= 17 else 0))),
                    'AVG_ELAPSED_SEC': random.uniform(1, 10),
                    'TOTAL_TB_SCANNED': random.uniform(0.1, 5)
                }
                for h in range(24)
            ],
            'by_type': [
                {'QUERY_TYPE': 'SELECT', 'QUERY_COUNT': random.randint(20000, 50000), 'AVG_ELAPSED_SEC': random.uniform(1, 5), 'TOTAL_ELAPSED_SEC': random.uniform(50000, 150000)},
                {'QUERY_TYPE': 'INSERT', 'QUERY_COUNT': random.randint(5000, 15000), 'AVG_ELAPSED_SEC': random.uniform(5, 15), 'TOTAL_ELAPSED_SEC': random.uniform(25000, 100000)},
                {'QUERY_TYPE': 'CREATE_TABLE_AS_SELECT', 'QUERY_COUNT': random.randint(1000, 5000), 'AVG_ELAPSED_SEC': random.uniform(10, 30), 'TOTAL_ELAPSED_SEC': random.uniform(10000, 50000)},
                {'QUERY_TYPE': 'UPDATE', 'QUERY_COUNT': random.randint(500, 2000), 'AVG_ELAPSED_SEC': random.uniform(2, 8), 'TOTAL_ELAPSED_SEC': random.uniform(1000, 10000)},
                {'QUERY_TYPE': 'DELETE', 'QUERY_COUNT': random.randint(100, 500), 'AVG_ELAPSED_SEC': random.uniform(1, 5), 'TOTAL_ELAPSED_SEC': random.uniform(100, 2000)},
                {'QUERY_TYPE': 'MERGE', 'QUERY_COUNT': random.randint(200, 1000), 'AVG_ELAPSED_SEC': random.uniform(5, 20), 'TOTAL_ELAPSED_SEC': random.uniform(1000, 15000)},
            ],
            'by_user': [
                {'USER_NAME': 'ETL_SERVICE', 'QUERY_COUNT': random.randint(10000, 25000), 'AVG_ELAPSED_SEC': random.uniform(5, 15), 'TOTAL_GB_SCANNED': random.uniform(500, 2000)},
                {'USER_NAME': 'ANALYTICS_USER', 'QUERY_COUNT': random.randint(5000, 15000), 'AVG_ELAPSED_SEC': random.uniform(2, 8), 'TOTAL_GB_SCANNED': random.uniform(200, 800)},
                {'USER_NAME': 'REPORT_USER', 'QUERY_COUNT': random.randint(3000, 10000), 'AVG_ELAPSED_SEC': random.uniform(1, 5), 'TOTAL_GB_SCANNED': random.uniform(100, 500)},
                {'USER_NAME': 'DATA_SCIENTIST', 'QUERY_COUNT': random.randint(1000, 5000), 'AVG_ELAPSED_SEC': random.uniform(10, 30), 'TOTAL_GB_SCANNED': random.uniform(300, 1000)},
                {'USER_NAME': 'ADMIN', 'QUERY_COUNT': random.randint(100, 500), 'AVG_ELAPSED_SEC': random.uniform(0.5, 2), 'TOTAL_GB_SCANNED': random.uniform(1, 50)},
            ]
        }
    
    def get_cost_trends(self, days: int = 30) -> List[Dict]:
        """Get daily cost trends."""
        base_time = datetime.now()
        return [
            {
                'DATE': (base_time - timedelta(days=i)).strftime('%Y-%m-%d'),
                'TOTAL_CREDITS': random.uniform(50, 150),
                'COMPUTE_CREDITS': random.uniform(40, 130),
                'CLOUD_SERVICES_CREDITS': random.uniform(2, 15)
            }
            for i in range(days, 0, -1)
        ]
    
    def analyze_bottlenecks(self) -> Dict:
        """Comprehensive bottleneck analysis."""
        return {
            'queuing': [
                {'WAREHOUSE_NAME': 'ANALYTICS_WH', 'QUEUED_QUERIES': random.randint(50, 200), 'AVG_QUEUE_TIME_SEC': random.uniform(5, 30), 'MAX_QUEUE_TIME_SEC': random.uniform(30, 120), 'TOTAL_QUERIES': random.randint(5000, 15000)},
                {'WAREHOUSE_NAME': 'REPORTING_WH', 'QUEUED_QUERIES': random.randint(20, 80), 'AVG_QUEUE_TIME_SEC': random.uniform(3, 15), 'MAX_QUEUE_TIME_SEC': random.uniform(15, 60), 'TOTAL_QUERIES': random.randint(2000, 8000)},
            ],
            'spilling': [
                {'WAREHOUSE_NAME': 'DATA_SCIENCE_WH', 'SPILLING_QUERIES': random.randint(10, 50), 'GB_SPILLED_LOCAL': random.uniform(5, 50), 'GB_SPILLED_REMOTE': random.uniform(0, 10)},
                {'WAREHOUSE_NAME': 'ETL_WH', 'SPILLING_QUERIES': random.randint(5, 30), 'GB_SPILLED_LOCAL': random.uniform(2, 20), 'GB_SPILLED_REMOTE': random.uniform(0, 5)},
            ],
            'compilation': [
                {'WAREHOUSE_NAME': 'ANALYTICS_WH', 'HIGH_COMPILE_QUERIES': random.randint(20, 100), 'AVG_COMPILE_SEC': random.uniform(5, 15), 'MAX_COMPILE_SEC': random.uniform(15, 45)},
            ],
            'failures': [
                {'ERROR_CODE': '100183', 'ERROR_MESSAGE': 'Statement reached its statement or warehouse timeout', 'FAILURE_COUNT': random.randint(5, 30)},
                {'ERROR_CODE': '90105', 'ERROR_MESSAGE': 'Cannot perform operation. Object does not exist', 'FAILURE_COUNT': random.randint(2, 15)},
                {'ERROR_CODE': '100038', 'ERROR_MESSAGE': 'Numeric value out of range', 'FAILURE_COUNT': random.randint(1, 10)},
            ]
        }
    
    def get_database_costs(self, days: int = 30) -> List[Dict]:
        """Get cost breakdown by database."""
        databases = ['ANALYTICS_DB', 'RAW_DATA', 'WAREHOUSE_DB', 'REPORTING_DB', 'DEV_DB', 'STAGING_DB']
        return [
            {
                'DATABASE_NAME': db,
                'QUERY_COUNT': random.randint(1000, 20000),
                'TOTAL_HOURS': random.uniform(10, 200),
                'AVG_ELAPSED_SEC': random.uniform(1, 15),
                'TB_SCANNED': random.uniform(0.5, 20),
                'CLOUD_SERVICES_CREDITS': random.uniform(1, 50)
            }
            for db in databases
        ]
    
    def get_recommendations(self) -> List[Dict]:
        """Generate optimization recommendations based on analysis."""
        recommendations = [
            {
                'category': 'Cost Optimization',
                'severity': 'Medium',
                'title': 'Consider reducing auto-suspend for ANALYTICS_WH',
                'description': 'Warehouse ANALYTICS_WH has auto-suspend of 300 seconds. Consider reducing to 60-120 seconds to save costs during idle periods.',
                'warehouse': 'ANALYTICS_WH'
            },
            {
                'category': 'Performance',
                'severity': 'High',
                'title': 'High queue times on ANALYTICS_WH',
                'description': '156 queries experienced avg queue time of 18.5s. Consider increasing cluster count or warehouse size.',
                'warehouse': 'ANALYTICS_WH'
            },
            {
                'category': 'Performance',
                'severity': 'Medium',
                'title': 'Query spilling detected on DATA_SCIENCE_WH',
                'description': '35 queries spilled to disk. Consider increasing warehouse size for memory-intensive queries.',
                'warehouse': 'DATA_SCIENCE_WH'
            },
            {
                'category': 'Right-sizing',
                'severity': 'High',
                'title': 'Warehouse DEV_WH may be oversized',
                'description': 'Warehouse DEV_WH (size: SMALL) has low average concurrency (0.15). Consider downsizing.',
                'warehouse': 'DEV_WH'
            }
        ]
        return recommendations
    
    def get_queued_queries(self, days: int = 7) -> List[Dict]:
        """Get information about queries that were queued."""
        users = ['ANALYTICS_USER', 'ETL_SERVICE', 'REPORT_USER']
        warehouses = ['ANALYTICS_WH', 'REPORTING_WH']
        
        return [
            {
                'QUERY_ID': f'01d{i:05d}-0000-{random.randint(1000,9999)}-0000-{random.randint(10000,99999)}',
                'QUERY_TEXT': f'SELECT COUNT(*) FROM {random.choice(["fact_sales", "fact_orders", "dim_customer"])} WHERE date_col BETWEEN ... AND ...',
                'USER_NAME': random.choice(users),
                'WAREHOUSE_NAME': random.choice(warehouses),
                'START_TIME': (datetime.now() - timedelta(hours=random.randint(1, days * 24))).isoformat(),
                'TOTAL_SEC': random.uniform(30, 300),
                'QUEUE_SEC': random.uniform(5, 60),
                'PROVISIONING_SEC': random.uniform(0, 15),
                'EXECUTION_SEC': random.uniform(20, 250)
            }
            for i in range(50)
        ]
    
    def get_hourly_credit_usage(self, days: int = 7) -> List[Dict]:
        """Get hourly credit usage pattern."""
        results = []
        for dow in range(7):
            for hour in range(24):
                # Simulate higher usage during business hours on weekdays
                base = 2.0 if dow < 5 else 0.5
                peak_factor = 1.5 if 9 <= hour <= 17 and dow < 5 else 1.0
                results.append({
                    'HOUR_OF_DAY': hour,
                    'DAY_OF_WEEK': dow,
                    'AVG_CREDITS': random.uniform(0.5, 3) * base * peak_factor,
                    'TOTAL_CREDITS': random.uniform(5, 30) * base * peak_factor
                })
        return results
    
    # ================================================================
    # NEW METHODS - User Analytics, Forecasting, Security, etc.
    # ================================================================
    
    def get_user_analytics(self, days: int = 30) -> Dict:
        """Get user-level analytics."""
        users = ['john.smith', 'jane.doe', 'etl_service', 'bi_tool', 'data_scientist', 'analyst_1', 'analyst_2', 'dbt_runner']
        
        top_users = [
            {
                'USER_NAME': user,
                'QUERY_COUNT': random.randint(500, 15000),
                'TOTAL_HOURS': random.uniform(10, 200),
                'AVG_QUERY_SEC': random.uniform(1, 30),
                'TB_SCANNED': random.uniform(0.5, 50),
                'FAILED_QUERIES': random.randint(0, 100),
                'WAREHOUSES_USED': random.randint(1, 5),
                'DATABASES_ACCESSED': random.randint(1, 8)
            }
            for user in users
        ]
        top_users.sort(key=lambda x: x['TOTAL_HOURS'], reverse=True)
        
        activity_trend = [
            {
                'DATE': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                'ACTIVE_USERS': random.randint(15, 45),
                'TOTAL_QUERIES': random.randint(5000, 25000)
            }
            for i in range(days, 0, -1)
        ]
        
        roles = ['ANALYST', 'DATA_ENGINEER', 'SYSADMIN', 'ACCOUNTADMIN', 'PUBLIC', 'DEVELOPER']
        role_usage = [
            {
                'ROLE_NAME': role,
                'QUERY_COUNT': random.randint(1000, 50000),
                'UNIQUE_USERS': random.randint(1, 20),
                'TOTAL_HOURS': random.uniform(10, 500)
            }
            for role in roles
        ]
        role_usage.sort(key=lambda x: x['QUERY_COUNT'], reverse=True)
        
        return {
            'top_users': top_users,
            'activity_trend': activity_trend,
            'role_usage': role_usage
        }
    
    def get_cost_forecast(self, days: int = 30, forecast_days: int = 30) -> Dict:
        """Get cost forecast and projections."""
        daily_data = [
            {
                'DATE': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                'DAILY_CREDITS': random.uniform(40, 80),
                'COMPUTE_CREDITS': random.uniform(35, 70),
                'CLOUD_CREDITS': random.uniform(3, 10)
            }
            for i in range(days, 0, -1)
        ]
        
        weekly_comparison = [
            {'PERIOD': 'This Week', 'TOTAL_CREDITS': random.uniform(350, 500), 'AVG_HOURLY_CREDITS': random.uniform(2, 4)},
            {'PERIOD': 'Last Week', 'TOTAL_CREDITS': random.uniform(300, 450), 'AVG_HOURLY_CREDITS': random.uniform(1.8, 3.5)}
        ]
        
        avg_daily = sum(d['DAILY_CREDITS'] for d in daily_data) / len(daily_data)
        trend_factor = random.uniform(0.95, 1.15)
        
        return {
            'daily_data': daily_data,
            'weekly_comparison': weekly_comparison,
            'forecast': {
                'avg_daily_credits': avg_daily,
                'projected_30_day': avg_daily * forecast_days * trend_factor,
                'trend_factor': trend_factor,
                'trend_direction': 'increasing' if trend_factor > 1.05 else ('decreasing' if trend_factor < 0.95 else 'stable')
            }
        }
    
    def get_query_fingerprints(self, days: int = 7, min_count: int = 5) -> List[Dict]:
        """Get query fingerprints - grouped similar queries."""
        patterns = [
            'SELECT * FROM fact_sales WHERE date BETWEEN ? AND ?',
            'SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id',
            'INSERT INTO staging_table SELECT * FROM raw_data WHERE ...',
            'UPDATE dim_customer SET status = ? WHERE customer_id = ?',
            'SELECT p.*, o.* FROM products p JOIN orders o ON ...',
            'MERGE INTO target USING source ON target.id = source.id ...',
            'SELECT COUNT(*) FROM events WHERE event_type = ?',
            'DELETE FROM temp_table WHERE created_at < ?'
        ]
        
        return [
            {
                'FINGERPRINT': f'FP{i:08d}',
                'SAMPLE_QUERY': pattern,
                'EXECUTION_COUNT': random.randint(100, 5000),
                'AVG_DURATION_SEC': random.uniform(0.5, 60),
                'MAX_DURATION_SEC': random.uniform(30, 300),
                'MIN_DURATION_SEC': random.uniform(0.1, 5),
                'STDDEV_DURATION_SEC': random.uniform(1, 20),
                'TOTAL_GB_SCANNED': random.uniform(10, 500),
                'AVG_GB_SCANNED': random.uniform(0.1, 10),
                'UNIQUE_USERS': random.randint(1, 15),
                'WAREHOUSES_USED': random.randint(1, 4),
                'TOTAL_HOURS': random.uniform(5, 100)
            }
            for i, pattern in enumerate(patterns)
        ]
    
    def get_data_freshness(self) -> List[Dict]:
        """Get data freshness monitoring."""
        databases = ['PRODUCTION', 'ANALYTICS', 'RAW_DATA']
        schemas = ['PUBLIC', 'STAGING', 'MARTS']
        tables = ['fact_sales', 'fact_orders', 'dim_customer', 'dim_product', 'dim_date', 'raw_events', 'stg_transactions']
        
        results = []
        for _ in range(30):
            hours_since = random.choice([1, 6, 12, 24, 48, 168, 720, 2000])
            results.append({
                'DATABASE_NAME': random.choice(databases),
                'SCHEMA_NAME': random.choice(schemas),
                'TABLE_NAME': random.choice(tables) + f'_{random.randint(1,99)}',
                'ROW_COUNT': random.randint(10000, 50000000),
                'SIZE_GB': random.uniform(0.1, 50),
                'LAST_ALTERED': (datetime.now() - timedelta(hours=hours_since)).isoformat(),
                'CREATED': (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat(),
                'HOURS_SINCE_UPDATE': hours_since,
                'FRESHNESS_STATUS': 'Fresh' if hours_since < 24 else ('Recent' if hours_since < 168 else ('Stale' if hours_since < 720 else 'Very Stale'))
            })
        
        results.sort(key=lambda x: x['SIZE_GB'], reverse=True)
        return results
    
    def get_unused_objects(self, days: int = 30) -> Dict:
        """Get unused warehouses and tables."""
        unused_warehouses = [
            {'WAREHOUSE_NAME': 'OLD_DEV_WH', 'SIZE': 'SMALL'},
            {'WAREHOUSE_NAME': 'TEST_WH_BACKUP', 'SIZE': 'XSMALL'}
        ]
        
        unused_tables = [
            {
                'DATABASE_NAME': 'ARCHIVE',
                'SCHEMA_NAME': 'OLD_DATA',
                'TABLE_NAME': f'backup_table_{i}',
                'ROW_COUNT': random.randint(100000, 10000000),
                'SIZE_GB': random.uniform(1, 20),
                'LAST_ALTERED': (datetime.now() - timedelta(days=random.randint(60, 365))).isoformat(),
                'DAYS_SINCE_ALTERED': random.randint(60, 365)
            }
            for i in range(10)
        ]
        
        return {
            'unused_warehouses': unused_warehouses,
            'unused_tables': unused_tables
        }
    
    def get_login_history(self, days: int = 7) -> Dict:
        """Get user login history and security monitoring."""
        users = ['john.smith', 'jane.doe', 'etl_service', 'bi_tool', 'admin_user']
        
        summary = [
            {
                'USER_NAME': user,
                'LOGIN_COUNT': random.randint(5, 100),
                'UNIQUE_IPS': random.randint(1, 5),
                'LAST_LOGIN': (datetime.now() - timedelta(hours=random.randint(0, 48))).isoformat(),
                'FAILED_LOGINS': random.randint(0, 5)
            }
            for user in users
        ]
        
        failed_logins = [
            {
                'EVENT_TIMESTAMP': (datetime.now() - timedelta(hours=random.randint(1, days * 24))).isoformat(),
                'USER_NAME': random.choice(users),
                'CLIENT_IP': f'192.168.{random.randint(1,255)}.{random.randint(1,255)}',
                'REPORTED_CLIENT_TYPE': random.choice(['SNOWFLAKE_UI', 'JDBC_DRIVER', 'PYTHON_DRIVER']),
                'ERROR_CODE': random.choice(['390100', '390114', '390144']),
                'ERROR_MESSAGE': random.choice(['Incorrect username or password', 'User temporarily locked', 'Invalid authentication token'])
            }
            for _ in range(random.randint(3, 15))
        ]
        
        hourly_pattern = [
            {'HOUR_OF_DAY': hour, 'LOGIN_COUNT': random.randint(5, 50) if 8 <= hour <= 18 else random.randint(0, 10)}
            for hour in range(24)
        ]
        
        return {
            'summary': summary,
            'failed_logins': failed_logins,
            'hourly_pattern': hourly_pattern
        }
    
    def get_table_storage_details(self) -> List[Dict]:
        """Get detailed table-level storage breakdown."""
        databases = ['PRODUCTION', 'ANALYTICS', 'RAW_DATA']
        schemas = ['PUBLIC', 'STAGING', 'MARTS']
        tables = ['fact_sales', 'fact_orders', 'dim_customer', 'dim_product', 'events_log', 'transactions']
        
        results = []
        for _ in range(50):
            size = random.uniform(0.1, 100)
            results.append({
                'DATABASE_NAME': random.choice(databases),
                'SCHEMA_NAME': random.choice(schemas),
                'TABLE_NAME': random.choice(tables) + f'_{random.randint(1,99)}',
                'ROW_COUNT': random.randint(10000, 100000000),
                'SIZE_GB': size,
                'ACTIVE_GB': size * 0.85,
                'TIME_TRAVEL_GB': size * 0.10,
                'FAILSAFE_GB': size * 0.05,
                'CLONE_GB': 0,
                'CLUSTERING_KEY': random.choice([None, 'date_column', 'customer_id', 'LINEAR(date_column, region)']),
                'IS_TRANSIENT': random.choice(['NO', 'NO', 'NO', 'YES']),
                'CREATED': (datetime.now() - timedelta(days=random.randint(30, 500))).isoformat(),
                'LAST_ALTERED': (datetime.now() - timedelta(hours=random.randint(1, 720))).isoformat()
            })
        
        results.sort(key=lambda x: x['SIZE_GB'], reverse=True)
        return results
    
    def get_week_over_week_comparison(self) -> Dict:
        """Compare key metrics between this week and last week."""
        this_week_credits = random.uniform(400, 600)
        last_week_credits = random.uniform(350, 550)
        
        return {
            'credits': [
                {'THIS_WEEK_CREDITS': this_week_credits, 'LAST_WEEK_CREDITS': last_week_credits}
            ],
            'queries': [
                {'PERIOD': 'This Week', 'QUERY_COUNT': random.randint(80000, 120000), 'AVG_DURATION_SEC': random.uniform(3, 8), 'FAILED_QUERIES': random.randint(50, 200), 'TB_SCANNED': random.uniform(20, 50)},
                {'PERIOD': 'Last Week', 'QUERY_COUNT': random.randint(75000, 115000), 'AVG_DURATION_SEC': random.uniform(3, 8), 'FAILED_QUERIES': random.randint(40, 180), 'TB_SCANNED': random.uniform(18, 48)}
            ],
            'users': [
                {'THIS_WEEK_USERS': random.randint(30, 50), 'LAST_WEEK_USERS': random.randint(28, 48)}
            ],
            'credit_change_pct': ((this_week_credits - last_week_credits) / last_week_credits) * 100
        }
    
    def get_query_optimization_opportunities(self) -> List[Dict]:
        """Get query optimization opportunities."""
        opportunities = []
        
        # Full table scans
        for i in range(8):
            opportunities.append({
                'QUERY_ID': f'01f{i:05d}-scan-{random.randint(1000,9999)}',
                'QUERY_TEXT': f'SELECT * FROM large_table_{i} WHERE non_clustered_col = ...',
                'USER_NAME': random.choice(['analyst_1', 'bi_tool', 'data_scientist']),
                'WAREHOUSE_NAME': 'ANALYTICS_WH',
                'DATABASE_NAME': 'PRODUCTION',
                'ELAPSED_SEC': random.uniform(60, 300),
                'GB_SCANNED': random.uniform(50, 500),
                'ROWS_PRODUCED': random.randint(100, 10000),
                'PARTITIONS_SCANNED': random.randint(1000, 5000),
                'PARTITIONS_TOTAL': random.randint(1000, 5000),
                'PARTITION_SCAN_PCT': random.uniform(85, 100),
                'ISSUE_TYPE': 'Full Table Scan',
                'RECOMMENDATION': 'Consider adding clustering keys or filtering on partitioned columns'
            })
        
        # Spilling queries
        for i in range(5):
            opportunities.append({
                'QUERY_ID': f'01s{i:05d}-spill-{random.randint(1000,9999)}',
                'QUERY_TEXT': f'SELECT customer_id, SUM(...) FROM fact_table_{i} GROUP BY customer_id ORDER BY ...',
                'USER_NAME': random.choice(['etl_service', 'data_engineer']),
                'WAREHOUSE_NAME': 'ETL_WH',
                'DATABASE_NAME': 'ANALYTICS',
                'ELAPSED_SEC': random.uniform(120, 600),
                'LOCAL_SPILL_GB': random.uniform(5, 50),
                'REMOTE_SPILL_GB': random.uniform(0, 10),
                'ISSUE_TYPE': 'Memory Spilling',
                'RECOMMENDATION': 'Consider using a larger warehouse or optimizing query to reduce memory usage'
            })
        
        # SELECT * queries
        for i in range(5):
            opportunities.append({
                'QUERY_ID': f'01x{i:05d}-star-{random.randint(1000,9999)}',
                'QUERY_TEXT': f'SELECT * FROM wide_table_{i} WHERE ...',
                'USER_NAME': random.choice(['analyst_1', 'analyst_2', 'report_user']),
                'WAREHOUSE_NAME': 'REPORTING_WH',
                'DATABASE_NAME': 'PRODUCTION',
                'ELAPSED_SEC': random.uniform(30, 120),
                'GB_SCANNED': random.uniform(10, 100),
                'ISSUE_TYPE': 'SELECT * Usage',
                'RECOMMENDATION': 'Consider selecting only required columns to reduce data scanned'
            })
        
        return opportunities
    
    # ================================================================
    # DATABASE-SPECIFIC MONITORING (Mock Data)
    # ================================================================
    
    def get_database_list(self) -> List[Dict]:
        """Get list of all databases."""
        databases = [
            {'DATABASE_NAME': 'PRODUCTION', 'DATABASE_OWNER': 'SYSADMIN', 'CREATED': '2023-01-15T10:30:00', 'LAST_ALTERED': '2025-01-20T14:22:00', 'COMMENT': 'Main production database'},
            {'DATABASE_NAME': 'ANALYTICS', 'DATABASE_OWNER': 'SYSADMIN', 'CREATED': '2023-02-20T08:15:00', 'LAST_ALTERED': '2025-01-21T09:45:00', 'COMMENT': 'Analytics and BI'},
            {'DATABASE_NAME': 'RAW_DATA', 'DATABASE_OWNER': 'DATA_ENGINEER', 'CREATED': '2023-03-10T11:00:00', 'LAST_ALTERED': '2025-01-19T16:30:00', 'COMMENT': 'Raw data landing zone'},
            {'DATABASE_NAME': 'STAGING', 'DATABASE_OWNER': 'ETL_SERVICE', 'CREATED': '2023-04-05T09:00:00', 'LAST_ALTERED': '2025-01-21T12:00:00', 'COMMENT': 'ETL staging area'},
            {'DATABASE_NAME': 'DEV', 'DATABASE_OWNER': 'DEVELOPER', 'CREATED': '2024-01-10T14:30:00', 'LAST_ALTERED': '2025-01-18T10:15:00', 'COMMENT': 'Development environment'},
            {'DATABASE_NAME': 'SANDBOX', 'DATABASE_OWNER': 'ANALYST', 'CREATED': '2024-06-01T08:00:00', 'LAST_ALTERED': '2025-01-15T11:00:00', 'COMMENT': 'Analyst sandbox'},
        ]
        return databases
    
    def get_database_overview(self, database_name: str, days: int = 30) -> Dict:
        """Get comprehensive overview metrics for a specific database."""
        return {
            'query_metrics': {
                'TOTAL_QUERIES': random.randint(50000, 200000),
                'UNIQUE_USERS': random.randint(10, 50),
                'WAREHOUSES_USED': random.randint(2, 6),
                'AVG_QUERY_SEC': random.uniform(2, 15),
                'TOTAL_QUERY_HOURS': random.uniform(100, 500),
                'TB_SCANNED': random.uniform(5, 50),
                'TB_WRITTEN': random.uniform(0.5, 10),
                'FAILED_QUERIES': random.randint(50, 500),
                'AVG_QUEUE_SEC': random.uniform(0, 8)
            },
            'storage': {
                'STORAGE_TB': random.uniform(0.5, 5),
                'FAILSAFE_GB': random.uniform(10, 100)
            },
            'objects': {
                'SCHEMA_COUNT': random.randint(3, 12),
                'TABLE_COUNT': random.randint(50, 300),
                'TOTAL_ROWS': random.randint(100000000, 5000000000)
            }
        }
    
    def get_database_cost_analysis(self, database_name: str, days: int = 30) -> Dict:
        """Analyze costs for a specific database."""
        warehouses = ['ANALYTICS_WH', 'REPORTING_WH', 'ETL_WH', 'DEV_WH']
        sizes = ['X-Small', 'Small', 'Medium', 'Large']
        size_credits = {'X-Small': 1, 'Small': 2, 'Medium': 4, 'Large': 8}
        users = ['analyst_1', 'analyst_2', 'etl_service', 'bi_tool', 'data_scientist']
        
        by_warehouse = []
        for wh in warehouses[:random.randint(2, 4)]:
            size = random.choice(sizes)
            hours = random.uniform(10, 100)
            by_warehouse.append({
                'WAREHOUSE_NAME': wh,
                'WAREHOUSE_SIZE': size,
                'QUERY_COUNT': random.randint(5000, 50000),
                'TOTAL_HOURS': hours,
                'AVG_QUERY_SEC': random.uniform(1, 20),
                'TB_SCANNED': random.uniform(1, 20),
                'ESTIMATED_CREDITS': hours * size_credits.get(size, 4)
            })
        
        daily_volume = [
            {
                'DATE': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                'QUERY_COUNT': random.randint(2000, 8000),
                'TOTAL_HOURS': random.uniform(5, 25),
                'GB_SCANNED': random.uniform(50, 500),
                'UNIQUE_USERS': random.randint(5, 25)
            }
            for i in range(days, 0, -1)
        ]
        
        by_user = [
            {
                'USER_NAME': user,
                'QUERY_COUNT': random.randint(1000, 20000),
                'TOTAL_HOURS': random.uniform(5, 80),
                'AVG_QUERY_SEC': random.uniform(1, 15),
                'TB_SCANNED': random.uniform(0.5, 15)
            }
            for user in users
        ]
        by_user.sort(key=lambda x: x['TOTAL_HOURS'], reverse=True)
        
        return {
            'by_warehouse': by_warehouse,
            'daily_volume': daily_volume,
            'by_user': by_user
        }
    
    def get_database_slow_queries(self, database_name: str, days: int = 7, threshold_sec: int = 30) -> List[Dict]:
        """Get slow queries for a specific database."""
        users = ['analyst_1', 'analyst_2', 'etl_service', 'bi_tool']
        warehouses = ['ANALYTICS_WH', 'REPORTING_WH', 'ETL_WH']
        schemas = ['PUBLIC', 'STAGING', 'MARTS', 'RAW']
        query_types = ['SELECT', 'INSERT', 'CREATE_TABLE_AS_SELECT', 'MERGE']
        
        return [
            {
                'QUERY_ID': f'01slow{i:04d}-{random.randint(1000,9999)}',
                'QUERY_TEXT': f'SELECT ... FROM {database_name}.{random.choice(schemas)}.table_{i} WHERE ...',
                'USER_NAME': random.choice(users),
                'WAREHOUSE_NAME': random.choice(warehouses),
                'SCHEMA_NAME': random.choice(schemas),
                'QUERY_TYPE': random.choice(query_types),
                'ELAPSED_SEC': random.uniform(threshold_sec, 600),
                'EXECUTION_SEC': random.uniform(threshold_sec * 0.8, 500),
                'COMPILE_SEC': random.uniform(0.5, 10),
                'QUEUE_SEC': random.uniform(0, 30),
                'GB_SCANNED': random.uniform(1, 100),
                'ROWS_PRODUCED': random.randint(100, 1000000),
                'PARTITIONS_SCANNED': random.randint(100, 5000),
                'PARTITIONS_TOTAL': random.randint(100, 5000),
                'EXECUTION_STATUS': random.choice(['SUCCESS', 'SUCCESS', 'SUCCESS', 'FAIL']),
                'START_TIME': (datetime.now() - timedelta(hours=random.randint(1, days * 24))).isoformat()
            }
            for i in range(50)
        ]
    
    def get_database_bottlenecks(self, database_name: str, days: int = 7) -> Dict:
        """Identify bottlenecks for a specific database."""
        warehouses = ['ANALYTICS_WH', 'REPORTING_WH', 'ETL_WH']
        query_types = ['SELECT', 'INSERT', 'MERGE', 'CREATE_TABLE_AS_SELECT']
        
        queuing = [
            {
                'WAREHOUSE_NAME': wh,
                'QUEUED_QUERIES': random.randint(50, 500),
                'AVG_QUEUE_SEC': random.uniform(2, 20),
                'MAX_QUEUE_SEC': random.uniform(30, 120),
                'TOTAL_QUEUE_MINUTES': random.uniform(10, 200)
            }
            for wh in warehouses[:2]
        ]
        
        spilling = [
            {
                'WAREHOUSE_NAME': wh,
                'SPILLING_QUERIES': random.randint(20, 200),
                'LOCAL_SPILL_GB': random.uniform(5, 100),
                'REMOTE_SPILL_GB': random.uniform(0, 20)
            }
            for wh in warehouses[:2]
        ]
        
        compilation = [
            {
                'QUERY_TYPE': qt,
                'HIGH_COMPILE_QUERIES': random.randint(10, 100),
                'AVG_COMPILE_SEC': random.uniform(5, 15),
                'MAX_COMPILE_SEC': random.uniform(20, 60)
            }
            for qt in query_types[:3]
        ]
        
        failures = [
            {
                'ERROR_CODE': random.choice(['100183', '002003', '090106', '001003']),
                'ERROR_MESSAGE': random.choice([
                    'SQL compilation error: Object does not exist',
                    'Numeric value out of range',
                    'Query cancelled by user',
                    'Statement timed out'
                ]),
                'FAILURE_COUNT': random.randint(5, 50),
                'AFFECTED_USERS': random.randint(1, 10)
            }
            for _ in range(4)
        ]
        
        full_scans = [{
            'FULL_SCAN_COUNT': random.randint(50, 300),
            'AVG_GB_SCANNED': random.uniform(5, 50),
            'TOTAL_TB_SCANNED': random.uniform(1, 10)
        }]
        
        # Full scan details with suggested clustering columns
        tables_for_scan = ['fact_sales', 'fact_orders', 'events_log', 'transactions', 'user_activity']
        full_scan_details = [
            {
                'QUERY_ID': f'01scan{i:04d}-{random.randint(1000,9999)}',
                'QUERY_TEXT': f'SELECT customer_id, SUM(amount) FROM {database_name}.PUBLIC.{tables_for_scan[i % len(tables_for_scan)]} WHERE created_date >= \'2024-01-01\' GROUP BY customer_id',
                'USER_NAME': random.choice(['analyst_1', 'bi_tool', 'etl_service']),
                'WAREHOUSE_NAME': random.choice(warehouses),
                'ELAPSED_SEC': random.uniform(60, 300),
                'GB_SCANNED': random.uniform(20, 200),
                'PARTITIONS_SCANNED': random.randint(900, 1000),
                'PARTITIONS_TOTAL': 1000,
                'SCAN_PCT': random.uniform(90, 100),
                'TABLE_NAME': tables_for_scan[i % len(tables_for_scan)],
                'SUGGESTED_COLUMNS': random.choice([
                    'CREATED_DATE, CUSTOMER_ID',
                    'ORDER_DATE, REGION',
                    'EVENT_TIMESTAMP, USER_ID',
                    'TRANSACTION_DATE, ACCOUNT_ID'
                ])
            }
            for i in range(10)
        ]
        
        # Unclustered large tables
        unclustered_tables = [
            {
                'TABLE_SCHEMA': 'PUBLIC',
                'TABLE_NAME': table,
                'ROW_COUNT': random.randint(10000000, 100000000),
                'SIZE_GB': random.uniform(5, 50)
            }
            for table in ['events_log', 'raw_transactions', 'audit_trail', 'user_sessions']
        ]
        
        # Queued queries with details
        queued_queries = [
            {
                'QUERY_ID': f'01queue{i:04d}-{random.randint(1000,9999)}',
                'QUERY_TEXT': f'SELECT * FROM {database_name}.MARTS.report_table_{i} WHERE date_key >= CURRENT_DATE - 30',
                'USER_NAME': random.choice(['analyst_1', 'bi_tool', 'report_user']),
                'WAREHOUSE_NAME': random.choice(warehouses),
                'ELAPSED_SEC': random.uniform(30, 180),
                'QUEUE_SEC': random.uniform(10, 60),
                'GB_SCANNED': random.uniform(5, 50)
            }
            for i in range(8)
        ]
        
        return {
            'queuing': queuing,
            'spilling': spilling,
            'compilation': compilation,
            'failures': failures,
            'full_scans': full_scans,
            'full_scan_details': full_scan_details,
            'unclustered_tables': unclustered_tables,
            'queued_queries': queued_queries
        }
    
    def get_database_table_analysis(self, database_name: str) -> List[Dict]:
        """Get detailed table analysis for a database."""
        schemas = ['PUBLIC', 'STAGING', 'MARTS', 'RAW']
        tables = ['fact_sales', 'fact_orders', 'dim_customer', 'dim_product', 'dim_date', 'stg_events', 'raw_logs']
        
        results = []
        for _ in range(40):
            hours_since = random.choice([1, 6, 12, 24, 48, 168, 720, 2000])
            results.append({
                'TABLE_SCHEMA': random.choice(schemas),
                'TABLE_NAME': random.choice(tables) + f'_{random.randint(1,50)}',
                'ROW_COUNT': random.randint(10000, 100000000),
                'SIZE_GB': random.uniform(0.1, 50),
                'CLUSTERING_KEY': random.choice([None, None, 'date_key', 'customer_id', 'LINEAR(date_key, region)']),
                'CREATED': (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat(),
                'LAST_ALTERED': (datetime.now() - timedelta(hours=hours_since)).isoformat(),
                'DAYS_SINCE_UPDATE': hours_since // 24,
                'FRESHNESS': 'Fresh' if hours_since < 24 else ('Recent' if hours_since < 168 else ('Stale' if hours_since < 720 else 'Very Stale'))
            })
        
        results.sort(key=lambda x: x['SIZE_GB'], reverse=True)
        return results
    
    def get_database_query_patterns(self, database_name: str, days: int = 7) -> Dict:
        """Analyze query patterns for a specific database."""
        hourly = [
            {
                'HOUR_OF_DAY': hour,
                'QUERY_COUNT': random.randint(100, 2000) if 8 <= hour <= 18 else random.randint(20, 500),
                'AVG_DURATION_SEC': random.uniform(2, 15)
            }
            for hour in range(24)
        ]
        
        query_types = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'CREATE_TABLE_AS_SELECT', 'COPY']
        by_type = [
            {
                'QUERY_TYPE': qt,
                'QUERY_COUNT': random.randint(1000, 50000) if qt == 'SELECT' else random.randint(100, 10000),
                'AVG_DURATION_SEC': random.uniform(1, 30),
                'TB_SCANNED': random.uniform(0.1, 10)
            }
            for qt in query_types
        ]
        by_type.sort(key=lambda x: x['QUERY_COUNT'], reverse=True)
        
        schemas = ['PUBLIC', 'STAGING', 'MARTS', 'RAW', 'ARCHIVE']
        by_schema = [
            {
                'SCHEMA_NAME': schema,
                'QUERY_COUNT': random.randint(500, 30000),
                'UNIQUE_USERS': random.randint(3, 20),
                'AVG_DURATION_SEC': random.uniform(2, 20),
                'GB_SCANNED': random.uniform(10, 500)
            }
            for schema in schemas
        ]
        by_schema.sort(key=lambda x: x['QUERY_COUNT'], reverse=True)
        
        return {
            'hourly': hourly,
            'by_type': by_type,
            'by_schema': by_schema
        }
    
    def get_database_optimization_opportunities(self, database_name: str, days: int = 7) -> List[Dict]:
        """Get optimization opportunities for a database."""
        users = ['analyst_1', 'etl_service', 'bi_tool', 'data_scientist']
        warehouses = ['ANALYTICS_WH', 'REPORTING_WH', 'ETL_WH']
        schemas = ['PUBLIC', 'STAGING', 'MARTS']
        tables = ['fact_sales', 'fact_orders', 'dim_customer', 'events_log', 'transactions', 'user_activity']
        
        # Issues with specific recommendations including suggested columns
        issues = [
            ('Full Table Scan', 'fact_sales', 'Table fact_sales has no clustering key. Consider clustering on: ORDER_DATE, CUSTOMER_ID'),
            ('Full Table Scan', 'events_log', 'Add clustering key on events_log. Suggested columns: EVENT_TIMESTAMP, USER_ID'),
            ('Full Table Scan', 'transactions', 'Table transactions scans 95% of partitions. Cluster on: TRANSACTION_DATE, ACCOUNT_ID'),
            ('Remote Spilling', 'fact_orders', 'Use larger warehouse (costs more credits) or optimize query. Check for large JOINs on fact_orders.'),
            ('Heavy Local Spilling', 'dim_customer', 'Consider warehouse size upgrade or break query into smaller parts. Review ORDER BY on dim_customer.'),
            ('SELECT * on Large Table', 'fact_sales', 'Select only required columns from fact_sales. This reduces data scanned and credits used.'),
            ('High Compilation Time', None, 'Simplify query - reduce subqueries, CTEs, or UNION operations. Consider creating views for complex logic.')
        ]
        
        results = []
        for i in range(25):
            issue_type, table_name, recommendation = random.choice(issues)
            actual_table = table_name if table_name else random.choice(tables)
            schema = random.choice(schemas)
            
            results.append({
                'QUERY_ID': f'01opt{i:04d}-{random.randint(1000,9999)}',
                'QUERY_TEXT': f'SELECT {"*" if "SELECT *" in issue_type else "col1, col2, ..."} FROM {database_name}.{schema}.{actual_table} WHERE date_col >= ... {"GROUP BY customer_id ORDER BY total DESC" if "Spill" in issue_type else ""}',
                'USER_NAME': random.choice(users),
                'WAREHOUSE_NAME': random.choice(warehouses),
                'SCHEMA_NAME': schema,
                'TABLE_NAME': actual_table,
                'ELAPSED_SEC': random.uniform(30, 600),
                'GB_SCANNED': random.uniform(5, 200),
                'PARTITIONS_SCANNED': random.randint(500, 5000),
                'PARTITIONS_TOTAL': random.randint(500, 5000),
                'LOCAL_SPILL_GB': random.uniform(0, 50) if 'Spill' in issue_type else 0,
                'REMOTE_SPILL_GB': random.uniform(0, 10) if issue_type == 'Remote Spilling' else 0,
                'ISSUE_TYPE': issue_type,
                'RECOMMENDATION': recommendation,
                'START_TIME': (datetime.now() - timedelta(hours=random.randint(1, days * 24))).isoformat()
            })
        
        return results
    
    def get_database_recommendations(self, database_name: str, days: int = 30) -> List[Dict]:
        """Generate recommendations for a database."""
        recommendations = [
            {
                'severity': 'High',
                'category': 'Performance',
                'title': 'Significant Queue Times',
                'description': f'Average queue time of 8.3s on ANALYTICS_WH indicates warehouse contention. Consider scaling or spreading workloads.',
                'metric': '8.3s avg queue'
            },
            {
                'severity': 'High',
                'category': 'Cost',
                'title': 'Heavy Remote Spilling',
                'description': f'15.2 GB spilled to remote storage in the last {days} days. This is expensive and slow. Increase warehouse size or optimize queries.',
                'metric': '15.2 GB remote spill'
            },
            {
                'severity': 'Medium',
                'category': 'Performance',
                'title': 'Frequent Full Table Scans',
                'description': f'187 queries performed full table scans. Add clustering keys or improve WHERE clause filters.',
                'metric': '187 full scans'
            },
            {
                'severity': 'Medium',
                'category': 'Cost',
                'title': 'High Data Scanning Volume',
                'description': f'23.5 TB scanned in {days} days. Review queries for partition pruning and column selection.',
                'metric': '23.5 TB scanned'
            },
            {
                'severity': 'Low',
                'category': 'Reliability',
                'title': 'Moderate Query Failure Rate',
                'description': f'324 failed queries (2.1% failure rate). Review common error patterns.',
                'metric': '324 failures'
            }
        ]
        return recommendations
