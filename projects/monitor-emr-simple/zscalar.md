# Zscaler/Corporate Network Troubleshooting Guide

## 🔒 Common Corporate Network Issues

### Problem: Zscaler Blocking EMR URLs

**Error Messages:**

- "Connection timeout"
- "SSL certificate verification failed"
- "Access denied" or "URL blocked"
- "Proxy authentication required"

## ✅ **Immediate Solutions**

### **1. Work with IT/Security Team**

**Request URL Whitelisting:**

```
YARN ResourceManager APIs:
- http://[emr-master]:8088/ws/v1/cluster/info
- http://[emr-master]:8088/ws/v1/cluster/metrics  
- http://[emr-master]:8088/ws/v1/cluster/nodes
- http://[emr-master]:8088/ws/v1/cluster/apps

Spark History Server APIs:
- http://[emr-master]:18080/api/v1/applications

Business Justification:
- Critical for production EMR cluster monitoring
- Prevents outages through proactive health monitoring
- Internal infrastructure APIs, not external web browsing
- Required for compliance and SLA monitoring

Whitelist these URLs in Zscaler policy.

```

### **2. Configure Proxy in Application**

**Method A: Environment Variables**

```bash
# Set proxy environment variables before running
export HTTP_PROXY=http://corporate-proxy:8080
export HTTPS_PROXY=https://corporate-proxy:8080
export NO_PROXY=localhost,127.0.0.1,internal-domain.com

# Run the application
python emr_health_monitor.py
```

**Method B: Configuration File**
Add to `emr_health_config.yaml`:

```yaml
network:
  http_proxy: 'http://corporate-proxy:8080'
  https_proxy: 'https://corporate-proxy:8080'
  request_timeout: 30
  verify_ssl: true
  user_agent: 'EMR-Health-Monitor/1.0'
```

### **3. Network Architecture Solutions**

**Option A: Deploy on Internal Network**

- Deploy monitoring service on same network as EMR clusters
- Bypasses Zscaler for internal-to-internal communication
- Use jump server or bastion host for access

**Option B: VPN Access**

- Connect monitoring server through corporate VPN
- Direct network access to EMR clusters
- May still need URL whitelisting

**Option C: AWS Private Endpoints**

- Use VPC endpoints for AWS services
- Keep traffic within AWS network
- Reduces corporate proxy dependency

## 🔧 **Advanced Configuration**

### **Custom Request Headers**

Some corporate proxies require specific headers:

```python
# Add to requests session configuration
headers = {
    'User-Agent': 'EMR-Health-Monitor/1.0',
    'X-Corporate-App': 'EMR-Monitoring',
    'Accept': 'application/json'
}
session.headers.update(headers)
```

### **Proxy Authentication**

If your proxy requires authentication:

```bash
# With username/password
export HTTP_PROXY=http://username:password@proxy:8080

# With domain authentication  
export HTTP_PROXY=http://domain\\username:password@proxy:8080
```

### **SSL Certificate Issues**

If corporate proxy intercepts SSL certificates:

⚠️ **Only use these with IT approval:**

```yaml
network:
  verify_ssl: false  # ONLY if approved by security team
```

Or provide corporate CA bundle:

```python
import requests

session.verify = '/path/to/corporate-ca-bundle.crt'
```

## 🌐 **Alternative Network Paths**

### **1. SSH Tunneling**

Create SSH tunnel to EMR master:

```bash
# Forward YARN port
ssh -L 8088:emr-master:8088 user@jump-server

# Forward Spark port  
ssh -L 18080:emr-master:18080 user@jump-server

# Update config to use localhost
yarn_url: "http://localhost:8088"
spark_url: "http://localhost:18080"
```

### **2. AWS Session Manager**

Use AWS Systems Manager for secure access:

```bash
# Port forwarding via SSM
aws ssm start-session \
  --target i-1234567890abcdef0 \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["8088"],"localPortNumber":["8088"]}'
```

### **3. API Gateway Proxy**

Create AWS API Gateway proxy for EMR APIs:

- Deploy Lambda function to proxy requests
- Use API Gateway with corporate authentication
- Route through approved AWS endpoints

## 🔍 **Troubleshooting Steps**

### **Step 1: Test Connectivity**

```bash
# Test direct connection
curl -v http://emr-master:8088/ws/v1/cluster/info

# Test with proxy
curl -v --proxy http://proxy:8080 http://emr-master:8088/ws/v1/cluster/info

# Test DNS resolution
nslookup emr-master
```

### **Step 2: Check Zscaler Logs**

- Access Zscaler admin portal
- Review blocked URL logs
- Identify specific policy blocking access
- Request policy exception

### **Step 3: Verify Network Path**

```bash
# Trace network route
traceroute emr-master

# Check port accessibility
telnet emr-master 8088
telnet emr-master 18080
```

### **Step 4: Test with Python**

```python
import requests
import os

# Test with proxy
proxies = {
    'http': os.environ.get('HTTP_PROXY'),
    'https': os.environ.get('HTTPS_PROXY')
}

try:
    response = requests.get(
        'http://emr-master:8088/ws/v1/cluster/info',
        proxies=proxies,
        timeout=30
    )
    print(f"Success: {response.status_code}")
    print(response.json())
except Exception as e:
    print(f"Error: {e}")
```

## 📋 **Information to Collect for IT Team**

**For Whitelist Request:**

- EMR cluster hostnames/IPs
- Required ports (8088, 18080)
- Specific API endpoints
- Business justification
- Service owner contact info

**For Troubleshooting:**

- Zscaler policy name blocking access
- Error messages from application logs
- Network topology diagram
- Proxy server details
- SSL certificate chain info

## 🚀 **Quick Fixes by Scenario**

### **Scenario 1: "Connection Timeout"**

```yaml
# Increase timeouts
network:
  request_timeout: 60
```

### **Scenario 2: "SSL Certificate Error"**

```yaml
# Use HTTP instead of HTTPS for internal APIs
clusters:
  production:
    yarn_url: "http://emr-master:8088"  # Not https://
    spark_url: "http://emr-master:18080"
```

### **Scenario 3: "Proxy Authentication Required"**

```bash
export HTTP_PROXY=http://username:password@proxy:8080
```

### **Scenario 4: "URL Blocked by Policy"**

- Contact IT team with business justification
- Request Zscaler policy exception
- Provide specific URLs and use case

## 📞 **Escalation Path**

1. **Level 1**: Local IT support for proxy configuration
2. **Level 2**: Network security team for Zscaler policies
3. **Level 3**: Cloud/AWS team for VPC networking
4. **Level 4**: Security team for policy exceptions

## 🔐 **Security Best Practices**

- **Never disable SSL verification** without security team approval
- **Use service accounts** with minimal required permissions
- **Log all proxy bypass requests** for audit trail
- **Regularly review** whitelist policies
- **Document** all network configuration changes
