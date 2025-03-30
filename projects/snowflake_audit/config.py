import json
import os
import csv
from datetime import datetime, timedelta
import logging


class Config:
    def __init__(self, config_file='config.json'):
        """Initialize configuration from config file"""
        try:
            with open(config_file, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            logging.error(f"Error loading config file: {e}")
            self.config = {
                "snowflake": {},
                "databases": [],
                "default_interval": 24,
                "log_file": "snowflake_operations.log"
            }

        # Setup logging
        logging.basicConfig(
            filename=self.config.get("log_file", "snowflake_operations.log"),
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Create console handler
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        logging.getLogger('').addHandler(console)

        self.logger = logging.getLogger(__name__)

    def get_snowflake_config(self):
        """Return Snowflake connection parameters"""
        return self.config.get("snowflake", {})

    def get_databases(self):
        """Return configured databases and schemas"""
        return self.config.get("databases", [])

    def get_default_interval(self):
        """Return default monitoring interval in hours"""
        return self.config.get("default_interval", 24)

    def get_date_range(self, hours=None):
        """Return default date range for queries (from beginning of day to now)"""
        if hours is None:
            hours = self.get_default_interval()

        end_date = datetime.now()
        # Default to beginning of current day
        if hours == 24:
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = end_date - timedelta(hours=hours)

        return start_date, end_date

    def save_user_selections(self, selections, intervals=None):
        """Save user selections to CSV file"""
        try:
            with open('user-select.csv', 'w', newline='') as csvfile:
                fieldnames = ['database', 'schema', 'interval']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for selection in selections:
                    db_schema = selection.split('.')
                    if len(db_schema) == 2:
                        database, schema = db_schema
                        interval = intervals.get(selection,
                                                 self.get_default_interval()) if intervals else self.get_default_interval()
                        writer.writerow({
                            'database': database,
                            'schema': schema,
                            'interval': interval
                        })
            self.logger.info(f"Saved {len(selections)} user selections to user-select.csv")
            return True
        except Exception as e:
            self.logger.error(f"Error saving user selections: {e}")
            return False

    def load_user_selections(self):
        """Load previously saved user selections"""
        selections = []
        intervals = {}

        try:
            if os.path.exists('user-select.csv'):
                with open('user-select.csv', 'r') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        selection = f"{row['database']}.{row['schema']}"
                        selections.append(selection)
                        intervals[selection] = int(row.get('interval', self.get_default_interval()))
                self.logger.info(f"Loaded {len(selections)} user selections from user-select.csv")
            return selections, intervals
        except Exception as e:
            self.logger.error(f"Error loading user selections: {e}")
            return [], {}