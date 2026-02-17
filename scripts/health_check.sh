#!/bin/bash
#
# health_check.sh - Health check for the Polymarket Trader system
#
# Usage:
#   ./scripts/health_check.sh [OPTIONS]
#
# Options:
#   -p, --port PORT     API port (default: 8000)
#   -H, --host HOST     API host (default: localhost)
#   -t, --timeout N     Request timeout in seconds (default: 5)
#   -q, --quiet         Quiet mode (exit code only)
#   -j, --json          Output raw JSON response
#   -h, --help          Show this help message
#
# Exit Codes:
#   0   Healthy (API responding with 200)
#   1   Unhealthy (API not responding or error)
#   2   Configuration error
#
# Examples:
#   ./scripts/health_check.sh            # Check health
#   ./scripts/health_check.sh -q         # Quiet mode (exit code only)
#   ./scripts/health_check.sh --json     # Output JSON response
#   ./scripts/health_check.sh -p 8080    # Check on port 8080
#

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
HOST="localhost"
PORT=8000
TIMEOUT=5
QUIET=false
JSON_OUTPUT=false

# API URL (will be constructed)
API_URL=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print usage
usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Health check for the Polymarket Trader system.

This script checks the health of the API by calling the /health endpoint.
It's suitable for use in monitoring systems, load balancers, and cron jobs.

Options:
  -p, --port PORT     API port (default: 8000)
  -H, --host HOST     API host (default: localhost)
  -t, --timeout N     Request timeout in seconds (default: 5)
  -q, --quiet         Quiet mode (exit code only, no output)
  -j, --json          Output raw JSON response
  -h, --help          Show this help message

Exit Codes:
  0   Healthy (API responding with 200)
  1   Unhealthy (API not responding or error)
  2   Configuration error

Examples:
  $(basename "$0")            # Check health
  $(basename "$0") -q         # Quiet mode (exit code only)
  $(basename "$0") --json     # Output JSON response
  $(basename "$0") -p 8080    # Check on port 8080
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -p|--port)
                PORT="$2"
                shift 2
                ;;
            -H|--host)
                HOST="$2"
                shift 2
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            -j|--json)
                JSON_OUTPUT=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo -e "${RED}Error: Unknown option: $1${NC}"
                usage
                exit 2
                ;;
        esac
    done

    API_URL="http://${HOST}:${PORT}"
}

# Check if curl is available
check_curl() {
    if ! command -v curl &> /dev/null; then
        if [[ "$QUIET" != true ]]; then
            echo -e "${RED}Error: curl is not installed${NC}"
        fi
        exit 2
    fi
}

# Perform health check
health_check() {
    local response
    local http_code
    local url="${API_URL}/health"

    # Make request
    response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || echo -e "\n000")
    http_code=$(echo "$response" | tail -1)
    local body
    # Use sed instead of 'head -n -1' for macOS compatibility
    body=$(echo "$response" | sed '$d')

    # Handle different output modes
    if [[ "$JSON_OUTPUT" == true ]]; then
        if [[ "$http_code" == "200" ]]; then
            echo "$body"
            exit 0
        else
            echo "{\"status\": \"unhealthy\", \"http_code\": $http_code}"
            exit 1
        fi
    fi

    if [[ "$QUIET" == true ]]; then
        if [[ "$http_code" == "200" ]]; then
            exit 0
        else
            exit 1
        fi
    fi

    # Verbose output
    if [[ "$http_code" == "200" ]]; then
        echo -e "${GREEN}Healthy${NC}"
        echo "  URL: ${url}"
        echo "  HTTP Status: ${http_code}"
        echo "  Response: ${body}"
        exit 0
    else
        echo -e "${RED}Unhealthy${NC}"
        echo "  URL: ${url}"
        if [[ "$http_code" == "000" ]]; then
            echo "  Error: Connection failed or timed out"
        else
            echo "  HTTP Status: ${http_code}"
        fi
        exit 1
    fi
}

# Main function
main() {
    parse_args "$@"
    check_curl
    health_check
}

# Run main
main "$@"
