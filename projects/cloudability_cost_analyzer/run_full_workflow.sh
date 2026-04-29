#!/bin/bash
# run_full_workflow.sh
# Complete workflow: Fetch → Split by month → Analyze

set -e

print_banner() {
    echo ""
    echo "========================================================================"
    echo " CLOUDABILITY CHARGEBACK - FULL WORKFLOW"
    echo " Fetch → Split by Month → Analyze"
    echo "========================================================================"
    echo ""
}

print_usage() {
    echo "Usage: bash run_full_workflow.sh [OPTION]"
    echo ""
    echo "Options:"
    echo "  real          Fetch real data and process (requires API credentials)"
    echo "  sample        Generate sample data and process"
    echo "  help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  bash run_full_workflow.sh sample"
    echo ""
    echo "  export CLOUDABILITY_API_KEY='your-key'"
    echo "  export CLOUDABILITY_CLUSTER_ID='your-id'"
    echo "  bash run_full_workflow.sh real"
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

run_real() {
    FETCH_FORMAT="${1:-csv}"

    echo "[1/4] Checking Cloudability credentials..."

    if [ -z "$CLOUDABILITY_API_KEY" ]; then
        echo ""
        echo "✗ Error: CLOUDABILITY_API_KEY not set"
        echo ""
        echo "Set your credentials:"
        echo "  export CLOUDABILITY_API_KEY='your-api-key'"
        echo "  export CLOUDABILITY_CLUSTER_ID='your-cluster-id'"
        echo ""
        exit 1
    fi

    if [ -z "$CLOUDABILITY_CLUSTER_ID" ]; then
        echo ""
        echo "✗ Error: CLOUDABILITY_CLUSTER_ID not set"
        echo ""
        exit 1
    fi

    echo "✓ Credentials found"
    echo ""

    echo "[2/4] Fetching data from Cloudability..."
    bash fetch_cloudability_data.sh "$FETCH_FORMAT"

    echo ""
    echo "[3/4] Splitting into monthly files..."
    python3 split_costs_by_month.py --input costs_raw.csv --output-dir ./monthly

    echo ""
    echo "[4/4] Running chargeback analysis..."
    python3 chargeback_analysis.py
}

run_sample() {
    echo "[1/4] Generating sample data..."
    python3 generate_sample_cloudability_data.py --seed 42

    echo ""
    echo "[2/4] Splitting into monthly files..."
    python3 split_costs_by_month.py --input costs_raw.csv --output-dir ./monthly

    echo ""
    echo "[3/4] Running chargeback analysis..."
    python3 chargeback_analysis.py

    echo ""
    echo "✓ Complete workflow finished with sample data"
    echo ""
    echo "To use real Cloudability data instead:"
    echo "  export CLOUDABILITY_API_KEY='your-key'"
    echo "  export CLOUDABILITY_CLUSTER_ID='your-id'"
    echo "  bash run_full_workflow.sh real"
    echo ""
}

# Main flow
print_banner

if [ $# -eq 0 ]; then
    print_usage
    exit 0
fi

check_python

case "$1" in
    real)
        run_real "$2"
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
echo " WORKFLOW COMPLETE"
echo "========================================================================"
echo ""
echo "Output files:"
echo "  Combined:"
echo "    • costs_raw.csv                    (all months combined)"
echo "  Monthly files:"
echo "    • monthly/costs_2025_01.csv        (January 2025)"
echo "    • monthly/costs_2025_02.csv        (February 2025)"
echo "    • ... (one file per month)"
echo "  Analysis results:"
echo "    • chargeback_by_user_monthly.csv   (chargeback table)"
echo "    • summary_by_user.csv              (totals & statistics)"
echo "    • chargeback_with_mom_changes.csv  (month-over-month changes)"
echo "    • validation_monthly_totals.csv    (quality validation)"
echo ""
echo "Next steps:"
echo "  View combined data:  cat costs_raw.csv | head -20"
echo "  View January 2025:   cat monthly/costs_2025_01.csv"
echo "  View chargeback:     cat chargeback_by_user_monthly.csv"
echo ""
