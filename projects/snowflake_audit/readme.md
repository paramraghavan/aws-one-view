# Snowflake Audit Checker

Use flask/html5/bootstrap which connects to snow flake end point We have a config file with the credentails and a lsit
of database and corresponding schema to conenct
The ui dispalys all the database and schema and tables
and the user select schema or select a free tables inside the schema On run it goes an check for any Create, or Update
or Delete operation performed for a given date range , defaults today.(early morning 12.00 am not now)  Logs the
findings and shows on ui as well , Allow user to enter schedule interval per schema. the user selection are save to
user-select.csv for the run you can select on schema or multiple schema

## Features

- Connects to Snowflake using credentials and configuration stored in a local config file.
- Displays all configured databases and schemas via a user-friendly web interface.
- Allow users to select tables to be monitored
- Save the user selected options for each database
- Allows users to select a database/schema/table(s)  and specify a date range (defaults to today) to::
    - Check for **Create**, **Update**, and **Delete** operations.
    - Display and log the audit findings in real time.
- Optional
    - Supports scheduled checks at customizable intervals:
        - Every 30 minutes, 4 hours, 6 hours, 12 hours, or daily.
        - Option to trigger manual checks.
    - Schedule information is saved to a file and persists across application restarts.

## Configuration

Create a `config.json` file with the following structure:

```json
{
  "snowflake": {
    "account": "your_account_identifier",
    "user": "your_username",
    "password": "your_password",
    "warehouse": "your_warehouse",
    "role": "your_role"
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
  "log_file": "snowflake_operations.log"
}
```

## Getting Started

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the app:**

   ```bash
   python app.py
   ```

3. **Access the UI:**

   Open your browser and go to `http://localhost:5000`

## project structure
```text
project/
├── app.py                # Main Flask application
├── config.py             # Snowflake configuration handler
├── templates/
│   ├── base.html         # Base template with Bootstrap
│   ├── index.html        # Main UI page
│   └── results.html      # Results display page
├── static/
│   ├── css/
│   │   └── styles.css    # Custom styles
│   └── js/
│       └── main.js       # Client-side JavaScript
├── config.json           # Snowflake credentials and database config
├── user-select.csv       # Saved user selections
└── requirements.txt      # Project dependencies
```