#!/bin/bash
# AWS Resource Monitor - Setup and Run Script

set -e

echo "==================================="
echo "AWS Resource Monitor - Setup"
echo "==================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed"
    exit 1
fi

echo "✓ Python 3 found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Check AWS credentials
echo ""
echo "Checking AWS credentials..."
if python3 -c "import boto3; boto3.client('sts').get_caller_identity()" 2>/dev/null; then
    echo "✓ AWS credentials configured"
else
    echo ""
    echo "⚠ AWS credentials not configured!"
    echo ""
    echo "Configure credentials using one of these methods:"
    echo "  1. Run: aws configure"
    echo "  2. Set environment variables:"
    echo "     export AWS_ACCESS_KEY_ID='your-key'"
    echo "     export AWS_SECRET_ACCESS_KEY='your-secret'"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start the application
echo ""
echo "==================================="
echo "Starting AWS Resource Monitor"
echo "==================================="
echo ""
echo "Access the application at:"
echo "  http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python3 main.py
