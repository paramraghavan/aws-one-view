#!/bin/bash
# AWS Monitor - Simple Startup Script

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "AWS Monitor - Starting..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    source venv/bin/activate
fi

# Create directories if they don't exist
mkdir -p logs output configs

# Check AWS credentials
echo "Checking AWS credentials..."
if aws sts get-caller-identity --profile monitor &>/dev/null; then
    echo -e "${GREEN}✓ AWS credentials OK${NC}"
else
    echo -e "${YELLOW}⚠ AWS credentials not configured${NC}"
    echo "  Run: aws configure --profile monitor"
    echo ""
fi

# Parse arguments
HOST="127.0.0.1"
PORT="5000"
ROLE_ARN=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --role-arn)
            ROLE_ARN="--role-arn $2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo ""
echo "Starting Flask app..."
echo "  URL: http://${HOST}:${PORT}"
echo ""
echo -e "${GREEN}Press Ctrl+C to stop${NC}"
echo ""

# Start the app
python main.py --host "$HOST" --port "$PORT" $ROLE_ARN
