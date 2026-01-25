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

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"
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
echo "To start the monitor:"
echo "  python3 main.py"
echo ""
echo "Then open: http://localhost:5000"
echo ""
