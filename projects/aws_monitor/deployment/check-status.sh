#!/bin/bash
# AWS Monitor - Simple Status Checker

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "AWS Monitor - Status Check"
echo "============================"
echo ""

# Check if app is running
echo "1. Checking Application:"
if pgrep -f "python.*main.py" > /dev/null; then
    echo -e "${GREEN}✓${NC} App is running"
    ps aux | grep "[p]ython.*main.py" | awk '{print "   PID: " $2 " | CPU: " $3 "% | MEM: " $4 "%"}'
else
    echo -e "${RED}✗${NC} App is not running"
    echo "   Start with: ./start.sh"
fi
echo ""

# Check web endpoints
echo "2. Checking Web Endpoints:"
if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Health endpoint responding"
else
    echo -e "${RED}✗${NC} Health endpoint not responding"
fi

if curl -f -s http://localhost:5000/api/status > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Status API responding"
else
    echo -e "${RED}✗${NC} Status API not responding"
fi
echo ""

# Check AWS connectivity
echo "3. Checking AWS Connectivity:"
if aws sts get-caller-identity --profile monitor &>/dev/null; then
    echo -e "${GREEN}✓${NC} AWS credentials working"
    aws sts get-caller-identity --profile monitor 2>/dev/null | grep "Arn" | sed 's/^/   /'
else
    echo -e "${RED}✗${NC} AWS credentials not working"
    echo "   Configure with: aws configure --profile monitor"
fi
echo ""

# Check recent logs
echo "4. Checking Recent Logs:"
if [ -d "logs" ]; then
    recent_logs=$(find logs -name "*.log" -mmin -60 2>/dev/null | wc -l)
    if [ $recent_logs -gt 0 ]; then
        echo -e "${GREEN}✓${NC} Found $recent_logs log file(s) updated in last hour"
    else
        echo -e "${YELLOW}⚠${NC} No logs updated recently"
    fi
    
    # Check for errors
    recent_errors=$(find logs -name "*.log" -mmin -60 -exec grep -i "ERROR\|CRITICAL\|FAILED" {} \; 2>/dev/null | wc -l)
    if [ $recent_errors -eq 0 ]; then
        echo -e "${GREEN}✓${NC} No errors in last hour"
    else
        echo -e "${YELLOW}⚠${NC} Found $recent_errors error(s) in last hour"
    fi
else
    echo -e "${YELLOW}⚠${NC} Logs directory not found"
fi
echo ""

# Check disk space
echo "5. Checking Disk Space:"
if [ -d "logs" ]; then
    logs_size=$(du -sh logs 2>/dev/null | cut -f1)
    echo "   Logs: $logs_size"
fi

if [ -d "output" ]; then
    output_size=$(du -sh output 2>/dev/null | cut -f1)
    echo "   Output: $output_size"
fi
echo ""

# Check configurations
echo "6. Checking Configuration:"
if [ -d "configs" ]; then
    config_count=$(find configs -name "*.yaml" -o -name "*.yml" 2>/dev/null | wc -l)
    echo -e "${GREEN}✓${NC} Found $config_count configuration file(s)"
else
    echo -e "${YELLOW}⚠${NC} Configs directory not found"
fi
echo ""

# Summary
echo "================================"
echo "Summary"
echo "================================"

all_good=true

# Check critical items
if ! pgrep -f "python.*main.py" > /dev/null; then
    all_good=false
fi

if ! curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
    all_good=false
fi

if ! aws sts get-caller-identity --profile monitor &>/dev/null; then
    all_good=false
fi

if [ "$all_good" = true ]; then
    echo -e "${GREEN}✓ All systems operational${NC}"
else
    echo -e "${YELLOW}⚠ Some issues need attention${NC}"
fi

echo ""
echo "Quick Actions:"
echo "  Start app:   ./start.sh"
echo "  Stop app:    Ctrl+C (or pkill -f 'python main.py')"
echo "  View logs:   tail -f logs/*.log"
echo "  Health:      curl http://localhost:5000/health"
echo ""

