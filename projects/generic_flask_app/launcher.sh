#!/bin/bash
# Simple launcher script - user can create a shortcut to this
# This opens the Flask app in the default browser automatically

cd "$(dirname "$0")"

echo "🚀 Starting Flask App..."
echo ""
echo "Opening browser in 3 seconds..."
sleep 3

# Open browser (works on macOS, Linux, and Windows with WSL)
if command -v open &> /dev/null; then
    open "http://localhost:5123"
elif command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:5123"
elif command -v start &> /dev/null; then
    start "http://localhost:5123"
fi

python run.py
