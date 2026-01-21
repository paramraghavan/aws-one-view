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
