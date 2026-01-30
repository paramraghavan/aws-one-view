# Quick Fix: "Insecure Download" Error

## The Problem

When you click "Generate Script", the browser blocks the download with an error like:
- ❌ "Download blocked - Insecure connection"
- ❌ "This file was downloaded from an insecure source"
- ❌ Browser prevents download from HTTP

**Why?** Modern browsers block file downloads from HTTP (non-HTTPS) connections for security.

---

## ⚡ Quick Solution (2 Minutes) - Use HTTPS

### Step 1: Generate SSL Certificate

```bash
cd aws_monitor_simple

# Make script executable
chmod +x generate_cert.sh

# Generate certificate (one-time setup)
./generate_cert.sh
```

**Output:**
```
✅ Certificate generated successfully!

Files created:
  - certs/cert.pem (certificate)
  - certs/key.pem (private key)
```

### Step 2: Run with HTTPS

```bash
# Run with SSL
python main.py --ssl
```

**Output:**
```
INFO - ✅ Running with HTTPS (self-signed certificate)
INFO - Server: https://0.0.0.0:5000
INFO - ⚠️  Browser will show security warning - click 'Advanced' and 'Proceed to localhost'
```

### Step 3: Access via HTTPS

Open browser: **https://localhost:5000** (note the `https://`)

**First time only:** Browser shows security warning
1. Click **"Advanced"**
2. Click **"Proceed to localhost (unsafe)"** or **"Accept the Risk and Continue"**

### Step 4: Generate Script

Now file downloads work perfectly! ✅

---

## 🔧 Alternative Solutions

### Solution 1: Allow HTTP Downloads in Browser (Quick but Less Secure)

**Note:** Updated JavaScript now handles downloads client-side, which should work even over HTTP. Try the app first - downloads should work now!

If downloads still don't work:

#### Chrome
1. When download blocked, click the **download icon** in address bar
2. Click **"Keep"** or **"Download anyway"**

#### Firefox  
1. Click **"Keep"** in download warning
2. Or: `about:config` → search `dom.block_download_insecure` → set to `false`

#### Edge
1. Click **shield icon** → **"Allow download"**

---

### Solution 2: Use Command Line (No Browser Needed)

Create a config file:
```bash
cat > script_config.json <<EOF
{
  "regions": ["us-east-1"],
  "resources": {
    "types": ["ec2", "rds"],
    "filters": {}
  },
  "checks": ["performance", "cost", "alerts"],
  "thresholds": {"cpu": 80, "memory": 85},
  "notification": {"email": "admin@example.com"}
}
EOF
```

Download script via curl:
```bash
curl -X POST http://localhost:5000/api/generate-script \
  -H "Content-Type: application/json" \
  -d @script_config.json \
  -o aws_monitor_job.py

# Verify
ls -lh aws_monitor_job.py
```

---

## 🎯 Recommended Setup

### Development (Daily Use)

**Use HTTPS with self-signed certificate:**
```bash
# One-time setup
./generate_cert.sh

# Every time you start
python main.py --ssl

# Access
https://localhost:5000
```

**Benefits:**
- ✅ Downloads work perfectly
- ✅ No browser warnings after first time
- ✅ Professional development setup
- ✅ Works like production

---

### Quick Testing (One-Time Use)

**Use HTTP with browser allowlist:**
```bash
# Start normally
python main.py

# Access
http://localhost:5000

# When download blocked, click "Keep" in browser
```

**Benefits:**
- ✅ Fastest to start
- ✅ No certificate needed
- ⚠️  Less secure
- ⚠️  Browser warnings every time

---

## 📋 Troubleshooting

### Issue: generate_cert.sh not found

**Solution:** Make sure you're in the project directory
```bash
cd aws_monitor_simple
ls generate_cert.sh  # Should exist
chmod +x generate_cert.sh
./generate_cert.sh
```

### Issue: "openssl: command not found"

**Solution:** Install OpenSSL

**macOS:**
```bash
brew install openssl
```

**Ubuntu/Debian:**
```bash
sudo apt-get install openssl
```

**Windows:**
```bash
# Use Git Bash or WSL
# Or download from: https://slproweb.com/products/Win32OpenSSL.html
```

### Issue: "SSL certificate files not found"

**Solution:** Generate certificates first
```bash
./generate_cert.sh
# Then run with --ssl
python main.py --ssl
```

### Issue: Browser shows "Your connection is not private"

**This is normal for self-signed certificates!**

**Chrome:**
1. Click "Advanced"
2. Click "Proceed to localhost (unsafe)"

**Firefox:**
1. Click "Advanced"
2. Click "Accept the Risk and Continue"

**Edge:**
1. Click "Advanced"
2. Click "Continue to localhost (unsafe)"

**Safari:**
1. Click "Show Details"
2. Click "visit this website"

### Issue: Port 5000 already in use

**Solution:** Use different port
```bash
python main.py --ssl --port 8443
# Access: https://localhost:8443
```

### Issue: Downloads still blocked even with HTTPS

**Solution:** Clear browser cache
```bash
# Chrome: chrome://settings/clearBrowserData
# Firefox: about:preferences#privacy → Clear Data
# Edge: edge://settings/clearBrowserData
```

Then restart browser and try again.

---

## 🚀 Complete Workflow

### First Time Setup

```bash
# 1. Navigate to project
cd aws_monitor_simple

# 2. Generate SSL certificate (one-time)
chmod +x generate_cert.sh
./generate_cert.sh

# 3. Configure AWS profile
aws configure --profile monitor

# 4. Start with HTTPS
python main.py --ssl

# 5. Open browser (accept certificate warning first time)
https://localhost:5000
```

### Every Day After

```bash
# 1. Start server
python main.py --ssl

# 2. Open browser
https://localhost:5000

# 3. Done! No more warnings or download issues
```

---

## 📊 Comparison

| Method | Setup Time | Security | Downloads Work | Recommended |
|--------|-----------|----------|----------------|-------------|
| **HTTPS with cert** | 2 min (once) | ✅ High | ✅ Yes | ⭐⭐⭐⭐⭐ |
| **HTTP + browser allow** | 30 sec | ⚠️ Low | ⚠️ Sometimes | ⭐⭐ |
| **Command line (curl)** | 0 sec | ✅ OK | ✅ Yes | ⭐⭐⭐ |

---

## 💡 Pro Tips

### 1. Add Alias for Quick Start

```bash
# Add to ~/.bashrc or ~/.zshrc
alias awsmon='cd ~/aws_monitor_simple && python main.py --ssl'

# Then just run:
awsmon
```

### 2. Create Desktop Shortcut

**macOS/Linux:**
```bash
cat > ~/Desktop/AWS_Monitor.command <<EOF
#!/bin/bash
cd ~/aws_monitor_simple
python main.py --ssl
EOF
chmod +x ~/Desktop/AWS_Monitor.command
```

Double-click to start!

### 3. Use with VS Code

Add to `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "AWS Monitor (HTTPS)",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/main.py",
      "args": ["--ssl"],
      "console": "integratedTerminal"
    }
  ]
}
```

Press F5 to start with HTTPS!

---

## ❓ FAQ

**Q: Do I need to generate certificates every time?**  
A: No! Generate once, use forever (or until they expire in 365 days).

**Q: Are self-signed certificates safe?**  
A: Yes for development on localhost. Don't use them in production.

**Q: Will this work on other computers on my network?**  
A: Yes, but they'll need to accept the certificate warning too. For production, use a real certificate (Let's Encrypt).

**Q: Can I use port 443 (default HTTPS)?**  
A: Yes, but you'll need sudo: `sudo python main.py --ssl --port 443`

**Q: What if I forget to use --ssl flag?**  
A: The app will remind you:
```
⚠️  Running with HTTP - file downloads may be blocked by browser
💡 Use --ssl flag for HTTPS: python main.py --ssl
```

---

## ✅ Summary

**Recommended for Development:**

```bash
# One-time setup (2 minutes)
./generate_cert.sh

# Every day (10 seconds)
python main.py --ssl
# Open: https://localhost:5000
```

**No more download errors! 🎉**

---

## 📚 Additional Resources

- [docs/FIX_INSECURE_DOWNLOAD.md](FIX_INSECURE_DOWNLOAD.md) - Detailed troubleshooting
- [README.md](../README.md) - Full documentation
- OpenSSL documentation: https://www.openssl.org/docs/

---

**Need help?** Check the troubleshooting section above or the detailed guide at `docs/FIX_INSECURE_DOWNLOAD.md`
