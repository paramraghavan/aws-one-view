# Simple Deployment - v1.4.0

## 🎯 Philosophy: Keep It Simple

**No Docker. No systemd. No complexity.**

Just a Flask app you can start and stop like any other Python script.

---

## 🚀 Quick Start (30 Seconds)

```bash
# 1. Extract
tar -xzf aws_monitor_simple.tar.gz
cd aws_monitor_simple

# 2. Setup
./setup.sh

# 3. Start
./start.sh

# 4. Open browser
http://localhost:5000
```

**Done!** ✅

---

## 📁 What You Get

### Core Files

- **setup.sh** - First-time setup (venv, dependencies, directories)
- **start.sh** - Start the Flask app
- **main.py** - Flask application
- **run_monitor.py** - Config-based monitoring

### Helper Scripts

- **deployment/backup.sh** - Backup configs and data
- **deployment/cleanup-logs.sh** - Clean old logs
- **deployment/check-status.sh** - Health check
- **deployment/validate-config.py** - Validate YAML configs

### Documentation

- **README.md** - User guide
- **docs/ADMIN_GUIDE.md** - Simple admin guide
- **docs/ADMIN_QUICKREF.md** - Quick reference
- **docs/CONFIG_CHEATSHEET.md** - Config quick ref
- **docs/CONFIG_MONITORING.md** - Config documentation

---

## 🛠️ Daily Usage

### Start the App

```bash
./start.sh
```

### Stop the App

```
Ctrl+C
```

### Check Health

```bash
curl http://localhost:5000/health
```

### Run in Background (Optional)

```bash
# Start
nohup ./start.sh > app.log 2>&1 &

# Stop
pkill -f "python main.py"

# Check
ps aux | grep "python main.py"
```

---

## 📊 Config-Based Monitoring

### Run a Config

```bash
python run_monitor.py configs/production-monitoring.yaml
```

### Schedule with Cron

```bash
# Edit crontab
crontab -e

# Add job (every 15 minutes)
*/15 * * * * cd /path/to/aws-monitor && python run_monitor.py configs/production-monitoring.yaml >> logs/cron.log 2>&1
```

---

## 🧰 Maintenance

### Backup

```bash
./deployment/backup.sh
```

### Clean Logs

```bash
./deployment/cleanup-logs.sh
```

### Validate Configs

```bash
python deployment/validate-config.py configs/*.yaml
```

### Check Status

```bash
./deployment/check-status.sh
```

---

## 🎯 What's Simple About This?

### ✅ No Services

- No systemd
- No Docker
- No Docker Compose
- Just a Flask app

### ✅ Simple Start/Stop

```bash
./start.sh     # Start
Ctrl+C         # Stop
```

That's it!

### ✅ Simple Deployment

```bash
./setup.sh     # Setup once
./start.sh     # Run anytime
```

Two commands. Done.

### ✅ Simple Maintenance

```bash
./deployment/backup.sh         # Backup
./deployment/cleanup-logs.sh   # Clean
./deployment/check-status.sh   # Check
```

Three scripts. All maintenance covered.

### ✅ Simple Updates

```bash
# Stop
Ctrl+C

# Update
tar -xzf new-version.tar.gz
cp -r new-version/* .

# Start
./start.sh
```

Simple.

---

## 📚 Documentation

All the docs you need, nothing you don't:

1. **README.md** - How to use
2. **ADMIN_GUIDE.md** - How to maintain
3. **CONFIG_MONITORING.md** - How to schedule
4. **TROUBLESHOOTING.md** - How to fix

---

## 🆚 What This Is NOT

❌ **Not a service** - You start/stop it manually (or with cron)
❌ **Not containerized** - No Docker needed
❌ **Not complex** - No 50-page deployment guide
❌ **Not automated** - No auto-start on boot (unless you want it)

---

## 🎯 What This IS

✅ **Simple** - Setup and start in 30 seconds
✅ **Flexible** - Run when you need it
✅ **Maintainable** - Clear scripts, clear docs
✅ **Practical** - Does what you need, nothing more

---

## 💡 Common Workflows

### Workflow 1: Interactive Use

```bash
# Morning
./start.sh

# Use browser
# http://localhost:5000

# Evening
Ctrl+C
```

**Time**: Start/stop in seconds

---

### Workflow 2: Scheduled Monitoring

```bash
# Setup once
crontab -e
# Add: */15 * * * * cd /path && python run_monitor.py configs/prod.yaml

# Check results anytime
cat logs/production-monitoring.log
cat output/production-monitoring.json
```

**Maintenance**: Zero (runs automatically)

---

### Workflow 3: On-Demand Reports

```bash
# Run when needed
python run_monitor.py configs/cost-report.yaml

# View results
cat output/cost-report.json
```

**Flexibility**: Run anytime, anywhere

---

## 🔧 Customization

### Custom Port

```bash
./start.sh --port 8080
```

### Network Access

```bash
./start.sh --host 0.0.0.0
# WARNING: Only on trusted networks!
```

### IAM Role

```bash
./start.sh --role-arn arn:aws:iam::123456:role/MonitoringRole
```

---

## 📊 File Structure

```
aws_monitor_simple/
├── setup.sh              ← Setup script
├── start.sh              ← Start script
├── main.py               ← Flask app
├── run_monitor.py        ← Config runner
├── configs/              ← YAML configs
├── logs/                 ← Application logs
├── output/               ← JSON outputs
├── deployment/           ← Helper scripts
│   ├── backup.sh
│   ├── cleanup-logs.sh
│   ├── check-status.sh
│   └── validate-config.py
└── docs/                 ← Documentation
    ├── ADMIN_GUIDE.md
    ├── ADMIN_QUICKREF.md
    ├── CONFIG_MONITORING.md
    └── ...
```

---

## 🎉 Summary

**Philosophy**: Keep it simple

**Setup**: 30 seconds
**Start**: 1 command
**Stop**: Ctrl+C
**Maintain**: 3 scripts

**No services. No containers. No complexity.**

**Just a simple, practical AWS monitoring tool.**

---

## 📞 Quick Reference

```bash
# Setup (first time)
./setup.sh

# Start
./start.sh

# Stop
Ctrl+C

# Background
nohup ./start.sh > app.log 2>&1 &

# Stop background
pkill -f "python main.py"

# Health
curl http://localhost:5000/health

# Status
./deployment/check-status.sh

# Backup
./deployment/backup.sh

# Clean
./deployment/cleanup-logs.sh

# Validate
python deployment/validate-config.py configs/*.yaml

# Monitor
python run_monitor.py configs/my-config.yaml
```

---

**That's it. Simple, practical, effective.** 🚀
