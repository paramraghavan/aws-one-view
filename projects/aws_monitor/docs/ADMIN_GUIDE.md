# Simple Admin Guide - Flask App

## 🚀 Quick Start (30 Seconds)

```bash
# 1. Setup (first time only)
./setup.sh

# 2. Start
./start.sh

# 3. Open browser
http://localhost:5000
```

Done! ✅

---

## 📋 Daily Commands

### Start the App

```bash
./start.sh
```

Or manually:
```bash
source venv/bin/activate
python main.py
```

**Custom port/host:**
```bash
./start.sh --port 8080
./start.sh --host 0.0.0.0  # WARNING: Exposes to network!
```

---

### Stop the App

```
Press Ctrl+C in the terminal
```

---

### Run in Background

```bash
# Start in background
nohup ./start.sh > app.log 2>&1 &

# Check if running
ps aux | grep "python main.py"

# Stop it
pkill -f "python main.py"

# View logs
tail -f app.log
```

---

### Check Health

```bash
# Simple check
curl http://localhost:5000/health

# Detailed status
curl http://localhost:5000/api/status
```

---

## 🛠️ Maintenance

### Backup

```bash
# Backup configs and recent data
./deployment/backup.sh
```

**What it backs up:**
- Configuration files
- Recent outputs
- Scripts

**Restore:**
```bash
tar -xzf /path/to/backup.tar.gz
```

---

### Clean Old Logs

```bash
# Test what would be deleted
./deployment/cleanup-logs.sh --dry-run

# Actually delete old logs (30+ days)
./deployment/cleanup-logs.sh

# Keep only 7 days
./deployment/cleanup-logs.sh --days 7
```

**Schedule weekly cleanup:**
```bash
# Add to your crontab
crontab -e

# Add this line (runs Sunday 2 AM)
0 2 * * 0 /path/to/aws-monitor/deployment/cleanup-logs.sh
```

---

### Validate Configs

**Before using a config, validate it:**

```bash
# Single config
python deployment/validate-config.py configs/production-monitoring.yaml

# All configs
python deployment/validate-config.py configs/*.yaml
```

**Output:**
```
✅ Configuration is valid - no issues found
```

or

```
❌ ERRORS (2):
   - Missing required field: regions
   - Invalid resource type: ec3
```

---

### Update Application

```bash
# 1. Stop the app (Ctrl+C)

# 2. Backup
./deployment/backup.sh

# 3. Extract new version
tar -xzf aws-monitor-new-version.tar.gz

# 4. Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# 5. Validate configs
python deployment/validate-config.py configs/*.yaml

# 6. Start again
./start.sh
```

---

## 📊 Config-Based Monitoring

### Run a Config Manually

```bash
source venv/bin/activate
python run_monitor.py configs/production-monitoring.yaml
```

---

### Schedule with Cron

```bash
# Edit crontab
crontab -e

# Add monitoring jobs
*/15 * * * * cd /path/to/aws-monitor && source venv/bin/activate && python run_monitor.py configs/production-monitoring.yaml >> logs/cron.log 2>&1

# Save and exit
```

**Common schedules:**
```bash
# Every 15 minutes
*/15 * * * * ...

# Every hour
0 * * * * ...

# Every 6 hours
0 */6 * * * ...

# Daily at 9 AM
0 9 * * * ...
```

---

## 🐛 Troubleshooting

### App Won't Start

**Check Python version:**
```bash
python3 --version  # Need 3.8+
```

**Check dependencies:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Check port in use:**
```bash
# Check if port 5000 is taken
lsof -i :5000

# Use different port
./start.sh --port 8080
```

---

### AWS Credentials Not Working

**Test credentials:**
```bash
aws sts get-caller-identity --profile monitor
```

**Configure credentials:**
```bash
aws configure --profile monitor
```

**Or manually edit:** `~/.aws/credentials`
```ini
[monitor]
aws_access_key_id = YOUR_KEY
aws_secret_access_key = YOUR_SECRET
region = us-east-1
```

---

### High Disk Usage

**Check sizes:**
```bash
du -sh logs/
du -sh output/
```

**Clean up:**
```bash
./deployment/cleanup-logs.sh
```

---

### Can't Access from Other Machines

**By default**, the app only listens on localhost (127.0.0.1).

**To allow network access:**
```bash
./start.sh --host 0.0.0.0
```

**⚠️ WARNING**: This exposes the app to your network. Only do this on trusted networks!

---

## 📁 Important Files

| File/Dir | Purpose |
|----------|---------|
| `start.sh` | Start the web UI |
| `setup.sh` | Initial setup |
| `main.py` | Flask application |
| `run_monitor.py` | Run config-based monitoring |
| `configs/` | Configuration files |
| `logs/` | Application logs |
| `output/` | JSON output from monitoring |
| `venv/` | Python virtual environment |

---

## 📝 Useful Scripts

### deployment/backup.sh
Backs up configs and data

```bash
./deployment/backup.sh
```

---

### deployment/cleanup-logs.sh
Cleans old logs

```bash
./deployment/cleanup-logs.sh
./deployment/cleanup-logs.sh --dry-run  # Test first
```

---

### deployment/validate-config.py
Validates YAML configs

```bash
python deployment/validate-config.py configs/*.yaml
```

---

## 🔐 Security Tips

1. **Never expose to internet** without a reverse proxy (nginx, Apache)
2. **Use IAM roles** instead of access keys when possible
3. **Rotate credentials** regularly
4. **Monitor access logs**
5. **Keep configs** in version control (Git)

---

## 💡 Pro Tips

### Alias for Quick Start

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
alias awsm='cd /path/to/aws-monitor && ./start.sh'
alias awsm-stop='pkill -f "python main.py"'
alias awsm-health='curl -s http://localhost:5000/health | python -m json.tool'
```

Then just type:
```bash
awsm           # Start
awsm-health    # Check health
awsm-stop      # Stop
```

---

### Watch Logs in Real-Time

```bash
tail -f logs/*.log
```

Or use `watch`:
```bash
watch -n 5 'tail -10 logs/production-monitoring.log'
```

---

### Quick Health Check Script

Create `check.sh`:
```bash
#!/bin/bash
if curl -f -s http://localhost:5000/health > /dev/null; then
    echo "✅ App is healthy"
else
    echo "❌ App is down"
    exit 1
fi
```

---

## 📚 Documentation

| Doc | Purpose |
|-----|---------|
| `README.md` | User guide |
| `CONFIG_CHEATSHEET.md` | Config quick reference |
| `CONFIG_MONITORING.md` | Complete config guide |
| `TROUBLESHOOTING.md` | Detailed troubleshooting |
| `ADMIN_QUICKREF.md` | Admin command reference |

---

## 🎯 Common Workflows

### Workflow 1: Daily Usage

```bash
# Morning
./start.sh

# Do your work in browser
# http://localhost:5000

# Evening
Ctrl+C (stop)
```

---

### Workflow 2: Scheduled Monitoring

```bash
# Setup once
crontab -e
# Add: */15 * * * * cd /path && python run_monitor.py configs/prod.yaml

# Check logs later
tail -f logs/production-monitoring.log
```

---

### Workflow 3: On-Demand Reports

```bash
# Run a config manually
source venv/bin/activate
python run_monitor.py configs/cost-report.yaml

# View output
cat output/cost-report.json
```

---

## 📞 Quick Reference

```bash
# Setup (first time)
./setup.sh

# Start app
./start.sh

# Stop app
Ctrl+C

# Background mode
nohup ./start.sh > app.log 2>&1 &

# Stop background
pkill -f "python main.py"

# Health check
curl http://localhost:5000/health

# Backup
./deployment/backup.sh

# Clean logs
./deployment/cleanup-logs.sh

# Validate config
python deployment/validate-config.py configs/my-config.yaml

# Run monitoring
python run_monitor.py configs/my-config.yaml
```

---

## ✅ Pre-Flight Checklist

Before using in "production":

- [ ] AWS credentials configured (`aws sts get-caller-identity --profile monitor`)
- [ ] Dependencies installed (`pip list | grep -i flask`)
- [ ] Configs validated (`python deployment/validate-config.py configs/*.yaml`)
- [ ] Health check works (`curl localhost:5000/health`)
- [ ] Logs directory exists (`ls logs/`)
- [ ] Backup script works (`./deployment/backup.sh`)
- [ ] Can start/stop cleanly

---

## 🎉 That's It!

**Simple deployment:**
- No Docker
- No systemd
- No complex setup
- Just Flask app

**Everything you need:**
- ✅ Easy start/stop
- ✅ Health checks
- ✅ Config validation
- ✅ Backups
- ✅ Log cleanup
- ✅ Cron scheduling

**Questions?** See the full docs or just run `./start.sh` and explore!
