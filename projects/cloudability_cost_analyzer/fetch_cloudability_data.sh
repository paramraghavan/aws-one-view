#!/bin/bash
# fetch_cloudability_data.sh
# Fetches raw cost data from Cloudability API V3 in CSV format
# Uses API V3 with basic auth format (-u API_KEY:API_PASS)

set -e

echo ""
echo "========================================================================"
echo " CLOUDABILITY DATA FETCHER (API V3)"
echo "========================================================================"

# Configuration
API_KEY="${CLOUDABILITY_API_KEY}"
API_PASS="${CLOUDABILITY_API_PASS}"
CLUSTER_ID="${CLOUDABILITY_CLUSTER_ID}"
START_DATE="2025-01-01"
END_DATE="2026-03-31"
ENDPOINT="${1:-allocations}"  # Default to allocations, can pass 'reporting' as argument
OUTPUT_FILE="costs_raw.csv"

# Validate endpoint
if [ "$ENDPOINT" != "allocations" ] && [ "$ENDPOINT" != "reporting" ]; then
    echo ""
    echo "ERROR: Invalid endpoint '$ENDPOINT'"
    echo "Usage: bash fetch_cloudability_data.sh [allocations|reporting]"
    echo "  allocations - /v3/containers/allocations (default)"
    echo "  reporting   - /v3/reporting/cost/run"
    echo ""
    exit 1
fi

# Validate inputs
if [ -z "$API_KEY" ]; then
    echo ""
    echo "ERROR: CLOUDABILITY_API_KEY not set"
    echo ""
    echo "Usage:"
    echo "  export CLOUDABILITY_API_KEY='your-api-key'"
    echo "  export CLOUDABILITY_API_PASS='your-api-password'"
    echo "  export CLOUDABILITY_CLUSTER_ID='your-cluster-id'"
    echo "  bash fetch_cloudability_data.sh [allocations|reporting]"
    echo ""
    echo "Examples:"
    echo "  bash fetch_cloudability_data.sh allocations  # Container allocations ✓"
    echo "  bash fetch_cloudability_data.sh reporting    # Cost reporting"
    echo ""
    exit 1
fi

if [ -z "$API_PASS" ]; then
    echo ""
    echo "ERROR: CLOUDABILITY_API_PASS not set"
    echo ""
    exit 1
fi

if [ -z "$CLUSTER_ID" ]; then
    echo ""
    echo "ERROR: CLOUDABILITY_CLUSTER_ID not set"
    echo ""
    exit 1
fi

echo ""
echo "[1/2] Configuration"
echo "      API Key: ${API_KEY:0:10}...${API_KEY: -5}"
echo "      API Pass: ${API_PASS:0:10}...${API_PASS: -5}"
echo "      Cluster ID: $CLUSTER_ID"
echo "      Date Range: $START_DATE to $END_DATE"
echo "      Endpoint: $ENDPOINT"

# Step 1: Fetch from Cloudability API V3
echo ""
echo "[2/2] Fetching data from Cloudability API V3..."

if [ "$ENDPOINT" = "allocations" ]; then
    # Using /v3/containers/allocations endpoint
    echo "      Endpoint: https://api.cloudability.com/v3/containers/allocations"

    curl -k -s -u "${API_KEY}:${API_PASS}" -X GET \
      "https://api.cloudability.com/v3/containers/allocations?pretty=true&start=${START_DATE}&end=${END_DATE}&filters=cluster==${CLUSTER_ID}&costType=adjusted_amortized_cost" \
      --header 'Accept: text/csv' \
      > "$OUTPUT_FILE"

else
    # Using /v3/reporting/cost/run endpoint
    echo "      Endpoint: https://api.cloudability.com/v3/reporting/cost/run"

    curl -k -s -u "${API_KEY}:${API_PASS}" -X GET \
      "https://api.cloudability.com/v3/reporting/cost/run?start_date=${START_DATE}&end_date=${END_DATE}&filters=cluster==${CLUSTER_ID}&dimensions=service_name&dimensions=usage_family&metrics=total_amortized_cost&sort=total_amortized_costDESC" \
      --header 'Accept: text/csv' \
      > "$OUTPUT_FILE"
fi

# Validate response
if [ ! -s "$OUTPUT_FILE" ]; then
    echo "      ✗ Failed to fetch data - empty response"
    echo ""
    echo "      Possible issues:"
    echo "      • API key or password is invalid"
    echo "      • Cluster ID doesn't exist"
    echo "      • Date range has no data"
    rm -f "$OUTPUT_FILE"
    exit 1
fi

# Check if response is an error message
if head -1 "$OUTPUT_FILE" | grep -qi "error\|unauthorized\|forbidden\|not found"; then
    echo "      ✗ API returned an error:"
    head -5 "$OUTPUT_FILE"
    rm -f "$OUTPUT_FILE"
    exit 1
fi

echo "      ✓ CSV data fetched successfully"
LINES=$(wc -l < "$OUTPUT_FILE")

# Try to calculate total cost from the last column
if [ "$LINES" -gt 1 ]; then
    TOTAL_COST=$(awk -F, 'NR>1 {sum+=$(NF)} END {printf "%.2f", sum}' "$OUTPUT_FILE")
else
    TOTAL_COST="0.00"
fi

echo ""
echo "========================================================================"
echo " SUMMARY"
echo "========================================================================"
echo "  Endpoint: $ENDPOINT"
echo "  Rows: $LINES (including header)"
echo "  Total Cost: \$$TOTAL_COST"
echo ""
echo "  Sample data (first 10 rows):"
echo "  ---"
head -10 "$OUTPUT_FILE"
echo "  ---"
echo ""

echo "✓ CSV data ready: $OUTPUT_FILE"
echo "✓ Ready to process with: python3 chargeback_analysis.py"
echo ""
