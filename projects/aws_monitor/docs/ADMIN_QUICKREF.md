# Admin Quick Reference Card

## 🚀 Deployment (One Command)

```bash
./deployment/deploy.sh
```

That's it! The script handles everything.

---

## 📋 Daily Commands

### Check Everything
```bash
./deployment/check-status.sh
```

### Check Logs
```bash
tail -f logs/*.log
```

### Health Check
```bash
curl http://localhost:5000/health
```

### Validate Configs
```bash
python deployment/validate-config.py configs/*.yaml
```

---

## 🔧 Service Management

### Status
```bash
sudo systemctl status aws-monitor
```

### Start/Stop/Restart
```bash
sudo systemctl start aws-monitor
sudo systemctl stop aws-monitor
sudo systemctl restart aws-monitor
```

### View Service Logs
```bash
sudo journalctl -u aws-monitor -f
```

---

## 🐳 Docker Commands

### Start All Services
```bash
docker-compose up -d
```

### View Logs
```bash
docker-compose logs -f
```

### Stop All
```bash
docker-compose down
```

### Restart
```bash
docker-compose restart
```

---

## 🛠️ Maintenance

### Backup
```bash
./deployment/backup.sh
```

### Clean Logs
```bash
./deployment/cleanup-logs.sh
./deployment/cleanup-logs.sh --dry-run  # Test first
```

### Update Application
```bash
# 1. Backup
./deployment/backup.sh

# 2. Stop
sudo systemctl stop aws-monitor

# 3. Update files
tar -xzf new-version.tar.gz
cp -r aws_monitor_simple/* /opt/aws-monitor/

# 4. Restart
sudo systemctl start aws-monitor

# 5. Verify
./deployment/check-status.sh
```

---

## 📊 Monitoring

### Web UI
```
http://localhost:5000
```

### Health Endpoint
```
http://localhost:5000/health
```

### Status API
```
http://localhost:5000/api/status
```

---

## 🐛 Troubleshooting

### Service Won't Start
```bash
sudo systemctl status aws-monitor
sudo journalctl -u aws-monitor -n 50
```

### Test Manually
```bash
cd /opt/aws-monitor
source venv/bin/activate
python main.py
```

### AWS Credentials
```bash
aws sts get-caller-identity --profile monitor
```

### Cron Jobs
```bash
cat /etc/cron.d/aws-monitor
grep CRON /var/log/syslog | tail
```

---

## 📁 Important Paths

| Item | Path |
|------|------|
| **Installation** | `/opt/aws-monitor` |
| **Logs** | `/opt/aws-monitor/logs` |
| **Output** | `/opt/aws-monitor/output` |
| **Configs** | `/opt/aws-monitor/configs` |
| **Backups** | `/opt/aws-monitor-backups` |
| **Service Logs** | `/var/log/aws-monitor` |
| **Systemd Service** | `/etc/systemd/system/aws-monitor.service` |
| **Cron Jobs** | `/etc/cron.d/aws-monitor` |

---

## ⚠️ Common Issues

### Port 5000 In Use
```bash
# Find what's using it
sudo lsof -i :5000

# Change port
python main.py --port 8080
```

### High Disk Usage
```bash
# Check usage
du -sh /opt/aws-monitor/*

# Clean logs
./deployment/cleanup-logs.sh
```

### AWS Credentials Missing
```bash
# Configure
aws configure --profile monitor

# Test
aws sts get-caller-identity --profile monitor
```

---

## 🔐 Security Checklist

- [ ] AWS credentials configured securely
- [ ] File permissions set correctly (600 for credentials)
- [ ] Service runs as non-root user
- [ ] Firewall configured (allow only localhost:5000)
- [ ] Logs are rotated
- [ ] Backups are working
- [ ] IAM role has minimum permissions
- [ ] CloudTrail is enabled

---

## 📞 Emergency Procedures

### Service Down
```bash
# 1. Check status
sudo systemctl status aws-monitor

# 2. Try restart
sudo systemctl restart aws-monitor

# 3. Check logs
sudo journalctl -u aws-monitor -n 100

# 4. Test manually
cd /opt/aws-monitor && python main.py
```

### Restore from Backup
```bash
# 1. Stop service
sudo systemctl stop aws-monitor

# 2. Restore
tar -xzf /opt/aws-monitor-backups/backup-file.tar.gz -C /opt/aws-monitor

# 3. Start service
sudo systemctl start aws-monitor

# 4. Verify
./deployment/check-status.sh
```

---

## 📚 Full Documentation

- **ADMIN_GUIDE.md** - Complete admin guide
- **CONFIG_MONITORING.md** - Config file documentation
- **TROUBLESHOOTING.md** - Detailed troubleshooting
- **README.md** - User documentation

---

## 💡 Pro Tips

**Quick Health Check**
```bash
# Add to .bashrc
alias awsm-status='/opt/aws-monitor/deployment/check-status.sh'
alias awsm-health='curl -s http://localhost:5000/health | jq'
```

**Watch Logs in Real-Time**
```bash
watch -n 10 'tail -5 /opt/aws-monitor/logs/*.log'
```

**Monitor Disk Usage**
```bash
watch -n 60 'du -sh /opt/aws-monitor/* 2>/dev/null'
```

**Auto-Backup Before Updates**
```bash
# Add to update script
./deployment/backup.sh && echo "Backup complete, proceeding..."
```

---

## 🎯 Performance Tips

1. **Reduce Discovery Time**
   - Select only needed resource types
   - Use filters (tags, names)
   - Monitor fewer regions

2. **Optimize Logging**
   - Set log level appropriately
   - Clean old logs regularly
   - Compress inactive logs

3. **Efficient Scheduling**
   - Critical resources: 5-15 min
   - Non-critical: 1+ hours
   - Cost tracking: Daily

---

## ✅ Pre-Flight Checklist

Before going to production:

- [ ] Deployed with `./deployment/deploy.sh`
- [ ] Service starts automatically (`systemctl enable aws-monitor`)
- [ ] Health check responds (`curl localhost:5000/health`)
- [ ] AWS credentials work
- [ ] Configs validated
- [ ] Cron jobs scheduled
- [ ] Backups scheduled
- [ ] Log rotation configured
- [ ] Monitoring in place
- [ ] Tested disaster recovery

---

**Need Help?**

1. Run status check: `./deployment/check-status.sh`
2. Read admin guide: `docs/ADMIN_GUIDE.md`
3. Check logs: `tail -f logs/*.log`
