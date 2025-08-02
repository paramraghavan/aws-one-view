- Sync tables from source to traget database
- scope small tables only 50 to 500 mb
- sync runs every 60 mins

## Create /etc/systemd/system/snowflake-sync.service:
```ini
[Unit]
Description=Snowflake Database Sync Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/your/app
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
## Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable snowflake-sync
sudo systemctl start snowflake-sync
```