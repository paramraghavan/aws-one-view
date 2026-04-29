#!/bin/bash
# run_chargeback.sh
# Unified entry point for chargeback analysis
# Supports both real Cloudability data and sample data

set -e

print_banner() {
    echo ""
    echo "========================================================================"
    echo " EMR ON KUBERNETES CLOUDABILITY CHARGEBACK ANALYSIS"
    echo " Jan 2025 - Feb 2026 | Monthly Breakdown by User"
    echo "========================================================================"
    echo ""
}

print_usage() {
    echo "Usage: bash run_chargeback.sh [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  real          Fetch from Cloudability API (requires API key & cluster ID)"
    echo "  sample        Generate sample/test data (no credentials needed)"
    echo "  help          Show this help message"
    echo ""
    echo "Options for 'real' command:"
    echo "  csv           Fetch as CSV directly (default, faster) ✓"
    echo "  json          Fetch as JSON then convert to CSV"
    echo ""
    echo "Examples:"
    echo "  bash run_chargeback.sh sample"
    echo ""
    echo "  export CLOUDABILITY_API_KEY='your-key'"
    echo "  export CLOUDABILITY_CLUSTER_ID='your-id'"
    echo "  bash run_chargeback.sh real csv   # Direct CSV (faster) ✓"
    echo "  bash run_chargeback.sh real json  # JSON then convert"
    echo ""
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo "✗ Python 3 not found. Please install Python 3.8+"
        exit 1
    fi

    if ! python3 -c "import pandas" 2>/dev/null; then
        echo "✗ pandas not installed"
        echo ""
        echo "Install dependencies:"
        echo "  pip install -r requirements.txt"
        echo ""
        exit 1
    fi
}

check_dependencies() {
    if ! command -v jq &> /dev/null; then
        echo "⚠ jq not found (needed for 'real' option)"
        echo "  Install: brew install jq (macOS) or apt-get install jq (Linux)"
    fi
}

run_real() {
    FETCH_FORMAT="${1:-csv}"  # Default to CSV, can pass 'json' as argument

    echo "[1/3] Checking Cloudability credentials..."

    if [ -z "$CLOUDABILITY_API_KEY" ]; then
        echo ""
        echo "✗ Error: CLOUDABILITY_API_KEY not set"
        echo ""
        echo "Set your credentials:"
        echo "  export CLOUDABILITY_API_KEY='your-api-key'"
        echo "  export CLOUDABILITY_CLUSTER_ID='your-cluster-id'"
        echo ""
        echo "Get API key from: Cloudability → Settings → API Keys"
        exit 1
    fi

    if [ -z "$CLOUDABILITY_CLUSTER_ID" ]; then
        echo ""
        echo "✗ Error: CLOUDABILITY_CLUSTER_ID not set"
        echo ""
        echo "Set your cluster ID:"
        echo "  export CLOUDABILITY_CLUSTER_ID='your-cluster-id'"
        echo ""
        exit 1
    fi

    echo "✓ Credentials found"
    echo ""

    echo "[2/3] Fetching data from Cloudability (format: $FETCH_FORMAT)..."
    bash fetch_cloudability_data.sh "$FETCH_FORMAT"

    echo "[3/3] Running analysis..."
    python3 chargeback_analysis.py
}

run_sample() {
    echo "[1/2] Generating sample data..."
    python3 generate_sample_cloudability_data.py --seed 42

    echo ""
    echo "[2/2] Running analysis..."
    python3 chargeback_analysis.py

    echo ""
    echo "========================================================================""
    echo " SAMPLE DATA RESULTS"
    echo "========================================================================"
    echo ""
    echo "✓ Analysis complete with sample data"
    echo ""
    echo "To use real Cloudability data instead:"
    echo "  export CLOUDABILITY_API_KEY='your-key'"
    echo "  export CLOUDABILITY_CLUSTER_ID='your-id'"
    echo "  bash run_chargeback.sh real"
    echo ""
}

# Main flow
print_banner

if [ $# -eq 0 ]; then
    print_usage
    exit 0
fi

check_python
check_dependencies

case "$1" in
    real)
        run_real "$2"  # Pass format (csv or json) as second argument
        ;;
    sample)
        run_sample
        ;;
    help|--help|-h)
        print_usage
        ;;
    *)
        echo "✗ Unknown command: $1"
        echo ""
        print_usage
        exit 1
        ;;
esac

echo ""
echo "========================================================================"
echo " OUTPUT FILES"
echo "========================================================================"
echo ""
echo "Main deliverables:"
echo "  • chargeback_by_user_monthly.csv  - Monthly chargeback by user"
echo "  • summary_by_user.csv             - Totals & statistics"
echo "  • chargeback_with_mom_changes.csv - Month-over-month changes"
echo "  • validation_monthly_totals.csv   - Quality validation"
echo ""
echo "View the results:"
echo "  cat chargeback_by_user_monthly.csv | head -20"
echo "  cat summary_by_user.csv"
echo ""
echo "For detailed guide:"
echo "  cat CHARGEBACK_QUICKSTART.md"
echo ""
