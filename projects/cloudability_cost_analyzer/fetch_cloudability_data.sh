#!/bin/bash
# fetch_cloudability_data.sh
# Fetches raw cost data from Cloudability API in JSON or CSV format

set -e

echo ""
echo "========================================================================"
echo " CLOUDABILITY DATA FETCHER"
echo "========================================================================"

# Configuration
API_KEY="${CLOUDABILITY_API_KEY}"
CLUSTER_ID="${CLOUDABILITY_CLUSTER_ID}"
START_DATE="2025-01-01"
END_DATE="2026-02-28"
FORMAT="${1:-csv}"  # Default to CSV, can pass 'json' as argument
OUTPUT_FILE="costs_raw.csv"
RAW_OUTPUT_FILE="raw_data.json"

# Validate format
if [ "$FORMAT" != "csv" ] && [ "$FORMAT" != "json" ]; then
    echo ""
    echo "ERROR: Invalid format '$FORMAT'"
    echo "Usage: bash fetch_cloudability_data.sh [csv|json]"
    echo "  csv  - Fetch as CSV (default, faster)"
    echo "  json - Fetch as JSON (then convert to CSV)"
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
    echo "  export CLOUDABILITY_CLUSTER_ID='your-cluster-id'"
    echo "  bash fetch_cloudability_data.sh [csv|json]"
    echo ""
    echo "Examples:"
    echo "  bash fetch_cloudability_data.sh csv   # Direct CSV (faster) ✓"
    echo "  bash fetch_cloudability_data.sh json  # JSON then convert"
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
echo "[1/3] Configuration"
echo "      API Key: ${API_KEY:0:10}...${API_KEY: -5}"
echo "      Cluster ID: $CLUSTER_ID"
echo "      Date Range: $START_DATE to $END_DATE"
echo "      Format: $FORMAT"

# Step 1: Fetch from Cloudability API
echo ""
echo "[2/3] Fetching data from Cloudability API..."
echo "      Endpoint: https://api.cloudability.com/v1/costs"
echo "      Accept: text/$FORMAT"

if [ "$FORMAT" = "csv" ]; then
    # Fetch directly as CSV (faster, no conversion needed)
    curl -s -X GET "https://api.cloudability.com/v1/costs" \
      -H "Authorization: Bearer $API_KEY" \
      -H "Accept: text/csv" \
      --data-urlencode "startDate=$START_DATE" \
      --data-urlencode "endDate=$END_DATE" \
      --data-urlencode "dimensions=month,namespace,service" \
      --data-urlencode "metrics=cost.fairshare" \
      --data-urlencode "filters=clusterId:$CLUSTER_ID" \
      > "$OUTPUT_FILE"

    if [ ! -s "$OUTPUT_FILE" ]; then
        echo "      ✗ Failed to fetch CSV data - check API key and cluster ID"
        rm -f "$OUTPUT_FILE"
        exit 1
    fi

    echo "      ✓ CSV data fetched successfully"
    LINES=$(wc -l < "$OUTPUT_FILE")
    TOTAL_COST=$(awk -F, 'NR>1 {sum+=$NF} END {printf "%.2f", sum}' "$OUTPUT_FILE")

else
    # Fetch as JSON then convert
    curl -s -X GET "https://api.cloudability.com/v1/costs" \
      -H "Authorization: Bearer $API_KEY" \
      -H "Accept: application/json" \
      --data-urlencode "startDate=$START_DATE" \
      --data-urlencode "endDate=$END_DATE" \
      --data-urlencode "dimensions=month,namespace,service" \
      --data-urlencode "metrics=cost.fairshare" \
      --data-urlencode "filters=clusterId:$CLUSTER_ID" \
      > "$RAW_OUTPUT_FILE"

    if [ ! -s "$RAW_OUTPUT_FILE" ]; then
        echo "      ✗ Failed to fetch JSON data - check API key and cluster ID"
        rm -f "$RAW_OUTPUT_FILE"
        exit 1
    fi

    echo "      ✓ JSON data fetched successfully"

    # Step 2: Validate JSON and convert to CSV
    echo ""
    echo "[3/3] Converting JSON to CSV..."

    if ! jq empty "$RAW_OUTPUT_FILE" 2>/dev/null; then
        echo "      ✗ Invalid JSON response"
        cat "$RAW_OUTPUT_FILE"
        exit 1
    fi

    # Extract to CSV using jq
    jq -r '.costs[] | [.month, .namespace, .service, .metrics["cost.fairshare"]] | @csv' "$RAW_OUTPUT_FILE" > "$OUTPUT_FILE" 2>/dev/null

    if [ ! -s "$OUTPUT_FILE" ]; then
        echo "      ✗ No data extracted from JSON"
        echo "      Raw response:"
        cat "$RAW_OUTPUT_FILE"
        exit 1
    fi

    # Add header
    sed -i.bak '1s/^/Month,Namespace,Service,FairshareValue\n/' "$OUTPUT_FILE"
    rm -f "$OUTPUT_FILE.bak"

    LINES=$(wc -l < "$OUTPUT_FILE")
    TOTAL_COST=$(jq '[.costs[] | .metrics["cost.fairshare"]] | add' "$RAW_OUTPUT_FILE")
fi

echo "      ✓ CSV data ready: $OUTPUT_FILE"
echo ""
echo "========================================================================"
echo " SUMMARY"
echo "========================================================================"
echo "  Data format: $FORMAT"
echo "  Rows: $LINES (including header)"
echo "  Total Fairshare Cost: \$$TOTAL_COST"
echo ""
echo "  Sample data (first 10 rows):"
echo "  ---"
head -10 "$OUTPUT_FILE"
echo "  ---"
echo ""

if [ "$FORMAT" = "csv" ]; then
    echo "✓ CSV fetched directly (fast path)"
else
    echo "✓ JSON fetched and converted to CSV"
fi

echo "✓ Ready to process with: python3 chargeback_analysis.py"
echo ""
