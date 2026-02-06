#!/bin/bash
# AWS Monitor - Setup Script

echo "============================================"
echo "AWS Monitor - Setup"
echo "============================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.8"

if [ -z "$python_version" ]; then
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python $python_version found"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment exists"
fi

# Activate and install dependencies
echo ""
echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Create directories
echo "Creating directories..."
mkdir -p logs output configs
echo "✅ Directories created"
echo ""

# Check AWS CLI
echo "Checking AWS CLI configuration..."
if command -v aws &> /dev/null; then
    echo "✅ AWS CLI found"
    
    # Check if monitor profile exists
    if aws configure list --profile monitor &> /dev/null; then
        echo "✅ AWS profile 'monitor' is configured"
    else
        echo "⚠️  AWS profile 'monitor' not found"
        echo ""
        echo "Please configure it:"
        echo "  aws configure --profile monitor"
        echo ""
        echo "Or manually edit ~/.aws/credentials:"
        echo "  [monitor]"
        echo "  aws_access_key_id = YOUR_KEY"
        echo "  aws_secret_access_key = YOUR_SECRET"
        echo "  region = us-east-1"
    fi
else
    echo "⚠️  AWS CLI not found (optional)"
    echo "You can configure AWS credentials manually in ~/.aws/credentials"
fi

echo ""
echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo ""
echo "Quick start:"
echo ""
echo "  1. Start the web UI:"
echo "     ./start.sh"
echo ""
echo "  2. Open browser:"
echo "     http://localhost:5000"
echo ""
echo "  3. Or run config-based monitoring:"
echo "     python run_monitor.py configs/production-monitoring.yaml"
echo ""
echo "For help:"
echo "  - README.md - User guide"
echo "  - docs/CONFIG_CHEATSHEET.md - Config quick reference"
echo "  - docs/ADMIN_QUICKREF.md - Admin commands"
echo ""

