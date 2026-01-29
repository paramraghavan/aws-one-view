# Fix: Insecure Download Error in Development

## The Problem

When clicking "Generate Script" in the browser, you get an error like:
- "Download blocked - Insecure connection"
- "This file was downloaded from an insecure source"
- Browser prevents download from HTTP (not HTTPS)

**Cause**: Flask runs on HTTP by default (`http://localhost:5000`), and modern browsers block downloads from non-HTTPS sites.

---

## Quick Solutions (Choose One)

### Solution 1: Browser - Allow Insecure Downloads (Quickest)

#### Chrome
1. When download is blocked, click the **blocked download icon** in address bar
2. Click "Keep" or "Allow download anyway"
3. Or go to `chrome://settings/security`
4. Scroll to "Safe Browsing"
5. Select "No protection (not recommended)" temporarily
6. **Remember to re-enable after testing!**

#### Firefox
1. When download is blocked, click "Keep" in the download panel
2. Or go to `about:config`
3. Search for `dom.block_download_insecure`
4. Set to `false`
5. **Remember to reset after testing!**

#### Edge
1. Click the **shield icon** in address bar when blocked
2. Click "Allow download"
3. Or go to `edge://settings/privacy`
4. Disable "Block downloads from unverified sources" temporarily

#### Safari
1. Safari usually allows localhost downloads
2. If blocked, go to Safari → Preferences → Security
3. Uncheck "Warn when visiting a fraudulent website" temporarily

---

### Solution 2: Run Flask with HTTPS (Recommended for Dev)

Generate a self-signed certificate and run Flask with HTTPS.

#### Step 1: Generate Self-Signed Certificate

```bash
cd aws_monitor_simple

# Generate certificate (valid for 365 days)
openssl req -x509 -newkey rsa:4096 -nodes \
  -out cert.pem -keyout key.pem -days 365 \
  -subj "/C=US/ST=State/L=City/O=Dev/CN=localhost"
```

This creates:
- `cert.pem` - SSL certificate
- `key.pem` - Private key

#### Step 2: Update main.py

Add SSL context to Flask:

```python
# At the bottom of main.py, replace:
if __name__ == '__main__':
    # ... existing argument parsing ...
    
    # Create SSL context for HTTPS
    import ssl
    import os
    
    ssl_context = None
    cert_file = 'cert.pem'
    key_file = 'key.pem'
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(cert_file, key_file)
        logger.info("Running with HTTPS (self-signed certificate)")
    else:
        logger.info("Running with HTTP (no certificate found)")
    
    # Run Flask app
    app.run(
        host=args.host, 
        port=args.port, 
        debug=args.debug,
        ssl_context=ssl_context  # Add this
    )
```

#### Step 3: Run and Access

```bash
python main.py

# Access with HTTPS
https://localhost:5000
```

**Note**: Browser will show certificate warning (expected with self-signed cert)
- Chrome: Click "Advanced" → "Proceed to localhost (unsafe)"
- Firefox: Click "Advanced" → "Accept the Risk and Continue"
- Edge: Click "Advanced" → "Continue to localhost (unsafe)"

---

### Solution 3: Use Different Response Method (Code Fix)

Instead of `send_file()`, return JSON with script content and let JavaScript handle download.

#### Update main.py

```python
@app.route('/api/generate-script', methods=['POST'])
def generate_script():
    """
    Generate Python monitoring script for cron/scheduler
    """
    data = request.get_json()
    
    try:
        generator = ScriptGenerator()
        script_content = generator.generate(data, role_arn=ROLE_ARN, session_name=SESSION_NAME)
        
        # Return as JSON instead of file
        return jsonify({
            'script': script_content,
            'filename': 'aws_monitor_job.py'
        })
    except Exception as e:
        logger.error(f"Script generation error: {e}")
        return jsonify({'error': str(e)}), 500
```

#### Update static/js/app.js

```javascript
async function generateScript() {
    // ... existing code ...
    
    try {
        const response = await fetch('/api/generate-script', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config)
        });
        
        if (!response.ok) throw new Error('Script generation failed');
        
        const data = await response.json();
        
        if (data.error) {
            showStatus(status, `Error: ${data.error}`, 'error');
            return;
        }
        
        // Create blob and download using JavaScript
        const blob = new Blob([data.script], { type: 'text/x-python' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = data.filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showStatus(status, '✅ Script downloaded! Schedule it with cron or Python scheduler.', 'success');
        
    } catch (error) {
        showStatus(status, `Error: ${error.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '📝 Generate Script';
    }
}
```

**Benefits**:
- Works with HTTP
- No certificate needed
- No browser warnings

---

### Solution 4: Use curl/wget (Alternative Download)

Skip the browser, use command line.

#### Get Script via curl

```bash
# Create config file
cat > script_config.json <<EOF
{
  "regions": ["us-east-1", "us-west-2"],
  "resources": {
    "types": ["ec2", "rds"],
    "filters": {}
  },
  "checks": ["performance", "cost", "alerts"],
  "thresholds": {"cpu": 80},
  "notification": {"email": "admin@example.com"}
}
EOF

# Generate and download script
curl -X POST http://localhost:5000/api/generate-script \
  -H "Content-Type: application/json" \
  -d @script_config.json \
  -o aws_monitor_job.py

# Verify
ls -lh aws_monitor_job.py
```

#### Or use wget

```bash
wget --post-file=script_config.json \
  --header="Content-Type: application/json" \
  -O aws_monitor_job.py \
  http://localhost:5000/api/generate-script
```

---

### Solution 5: Run on Different Port with Firewall Exception

Some browsers are more lenient with certain ports.

```bash
# Try port 8080 (often allowed)
python main.py --port 8080

# Access at:
http://localhost:8080
```

---

### Solution 6: Use ngrok for HTTPS Tunnel (Advanced)

Create HTTPS tunnel to localhost.

#### Install ngrok

```bash
# macOS
brew install ngrok

# Linux
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin
```

#### Run ngrok

```bash
# Start Flask
python main.py

# In another terminal, start ngrok
ngrok http 5000
```

#### Access via HTTPS

```
Forwarding: https://abc123.ngrok.io -> http://localhost:5000

# Use the HTTPS URL
https://abc123.ngrok.io
```

**Benefits**:
- Real HTTPS connection
- No browser warnings
- Can share with others

**Note**: Free tier has limitations

---

## Recommended Solutions by Use Case

### For Quick Testing (5 seconds)
**Use Solution 1**: Allow insecure downloads in browser
- Chrome: Click "Keep" when blocked
- Fastest solution

### For Regular Development (5 minutes)
**Use Solution 2**: Run with self-signed HTTPS
- Generate certificate once
- Works permanently
- Professional setup

### For Production-Like Testing (10 minutes)
**Use Solution 6**: Use ngrok
- Real HTTPS
- Can share with team
- Test like production

### For CI/CD or Scripts (No browser)
**Use Solution 4**: curl/wget
- Automated
- No browser needed
- Perfect for scripts

---

## Step-by-Step: Recommended Setup (HTTPS with Self-Signed Cert)

### Complete Setup

```bash
# 1. Navigate to project
cd aws_monitor_simple

# 2. Generate certificate (one time)
openssl req -x509 -newkey rsa:4096 -nodes \
  -out cert.pem -keyout key.pem -days 365 \
  -subj "/C=US/ST=Dev/L=Local/O=Development/CN=localhost"

# You'll see:
# cert.pem created
# key.pem created

# 3. Update main.py (see code above)

# 4. Run with HTTPS
python main.py

# Output:
# INFO - Running with HTTPS (self-signed certificate)
# INFO - Server: https://0.0.0.0:5000

# 5. Open browser
https://localhost:5000

# 6. Accept certificate warning (one time)
# Chrome: "Advanced" → "Proceed to localhost (unsafe)"
# Firefox: "Advanced" → "Accept the Risk and Continue"

# 7. Done! Downloads now work without issues
```

### Add to .gitignore

```bash
# Don't commit certificates to git
echo "cert.pem" >> .gitignore
echo "key.pem" >> .gitignore
```

---

## Troubleshooting

### Issue: "Certificate verify failed"

**Solution**: Use `--insecure` flag with curl
```bash
curl --insecure -X POST https://localhost:5000/api/generate-script ...
```

### Issue: "Port already in use"

**Solution**: Use different port
```bash
python main.py --port 8080
```

### Issue: "Permission denied" when generating certificate

**Solution**: Don't use sudo for openssl
```bash
# Run in your project directory (no sudo needed)
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

### Issue: Browser still blocks download

**Solution**: Clear browser cache
```bash
# Chrome
chrome://settings/clearBrowserData
# Select "Cached images and files"
# Clear data

# Firefox  
about:preferences#privacy
# Click "Clear Data"
```

### Issue: "ssl module not available"

**Solution**: Python was compiled without SSL
```bash
# Check Python SSL support
python -c "import ssl; print(ssl.OPENSSL_VERSION)"

# If error, reinstall Python with SSL
# macOS
brew reinstall python

# Linux
sudo apt-get install python3-dev libssl-dev
```

---

## Production Recommendations

### For Production Deployment

**Don't use self-signed certificates in production!**

Instead:
1. **Use reverse proxy** (nginx, Apache) with proper SSL
2. **Get real certificate** from Let's Encrypt (free)
3. **Use cloud load balancer** (AWS ALB, Cloudflare)

### Example: nginx with Let's Encrypt

```nginx
server {
    listen 443 ssl;
    server_name monitor.example.com;
    
    ssl_certificate /etc/letsencrypt/live/monitor.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/monitor.example.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Summary

**Quickest Fix** (30 seconds):
```
Browser → Allow insecure download
```

**Best for Dev** (5 minutes):
```
Generate self-signed cert → Run with HTTPS
```

**No Browser** (command line):
```
Use curl to download script
```

**Most Professional**:
```
Use ngrok for real HTTPS tunnel
```

Choose the solution that fits your needs and environment!
