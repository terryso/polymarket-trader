#!/bin/bash
#
# status.sh - Check the status of the Polymarket Trader system
#
# Usage:
#   ./scripts/status.sh [OPTIONS]
#
# Options:
#   -j, --json          Output in JSON format
#   -a, --api           Also check API health endpoint
#   -H, --host HOST     API host (default: localhost)
#   -p, --port PORT     API port (default: 8000)
#   -h, --help          Show this help message
#
# Exit Codes:
#   0   System is running
#   1   System is stopped
#   2   System is in error state
#
# Examples:
#   ./scripts/status.sh               # Check if process is running
#   ./scripts/status.sh --json        # Output in JSON format
#   ./scripts/status.sh --api         # Also check API health
#   ./scripts/status.sh -H 0.0.0.0    # Check API on all interfaces
#   ./scripts/status.sh -p 8080       # Check API on port 8080
#

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
JSON_OUTPUT=false
CHECK_API=false
HOST="localhost"
PORT=8000

# PID file
PID_FILE="${PROJECT_ROOT}/.bot.pid"
API_URL=""  # Will be constructed from HOST and PORT

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print usage
usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Check the status of the Polymarket Trader system.

Options:
  -j, --json          Output in JSON format
  -a, --api           Also check API health endpoint
  -H, --host HOST     API host (default: localhost)
  -p, --port PORT     API port (default: 8000)
  -h, --help          Show this help message

Exit Codes:
  0   System is running
  1   System is stopped
  2   System is in error state

Examples:
  $(basename "$0")               # Check if process is running
  $(basename "$0") --json        # Output in JSON format
  $(basename "$0") --api         # Also check API health
  $(basename "$0") -H 0.0.0.0    # Check API on all interfaces
  $(basename "$0") -p 8080       # Check API on port 8080
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -j|--json)
                JSON_OUTPUT=true
                shift
                ;;
            -a|--api)
                CHECK_API=true
                shift
                ;;
            -H|--host)
                HOST="$2"
                shift 2
                ;;
            -p|--port)
                PORT="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo -e "${RED}Error: Unknown option: $1${NC}"
                usage
                exit 1
                ;;
        esac
    done

    # Construct API URL
    API_URL="http://${HOST}:${PORT}"
}

# Get PID from file
get_pid() {
    if [[ -f "$PID_FILE" ]]; then
        cat "$PID_FILE" 2>/dev/null
    fi
}

# Check if process is running
is_running() {
    local pid="$1"
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

# Get process info
get_process_info() {
    local pid="$1"
    local info=""

    if [[ -n "$pid" ]]; then
        # Get process details using ps
        info=$(ps -p "$pid" -o pid,ppid,%cpu,%mem,etime,command 2>/dev/null | tail -1 || echo "")
    fi

    echo "$info"
}

# Get process uptime
get_uptime() {
    local pid="$1"

    if is_running "$pid"; then
        ps -p "$pid" -o etime= 2>/dev/null | xargs || echo "unknown"
    else
        echo "N/A"
    fi
}

# Check API health
check_api_health() {
    local response
    local http_code

    if command -v curl &> /dev/null; then
        response=$(curl -s -w "\n%{http_code}" "${API_URL}/health" 2>/dev/null || echo -e "\n000")
        http_code=$(echo "$response" | tail -1)

        if [[ "$http_code" == "200" ]]; then
            echo "healthy"
        else
            echo "unhealthy (HTTP $http_code)"
        fi
    else
        echo "curl not available"
    fi
}

# Get API status (full response)
get_api_status() {
    if command -v curl &> /dev/null; then
        curl -s "${API_URL}/health" 2>/dev/null || echo '{"status": "unreachable"}'
    else
        echo '{"status": "curl not available"}'
    fi
}

# Output status as JSON
output_json() {
    local pid
    pid=$(get_pid)

    local running=false
    local uptime="N/A"
    local api_status="not_checked"
    local process_info=""

    if is_running "$pid"; then
        running=true
        uptime=$(get_uptime "$pid")
        process_info=$(get_process_info "$pid")
    fi

    if [[ "$CHECK_API" == true ]]; then
        api_status=$(get_api_status)
    fi

    cat << EOF
{
    "process": {
        "pid": ${pid:-null},
        "running": ${running},
        "uptime": "${uptime}"
    },
    "api": {
        "url": "${API_URL}",
        "status": $(if [[ "$CHECK_API" == true ]]; then echo "$api_status"; else echo '"not_checked"'; fi)
    },
    "pid_file": "${PID_FILE}"
}
EOF
}

# Output status as text
output_text() {
    local pid
    pid=$(get_pid)

    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}Polymarket Trader Status${NC}"
    echo -e "${BLUE}=========================================${NC}"
    echo ""

    if [[ -z "$pid" ]]; then
        echo -e "Status:    ${RED}STOPPED${NC}"
        echo -e "PID File:  Not found"
        return 1
    fi

    if is_running "$pid"; then
        echo -e "Status:    ${GREEN}RUNNING${NC}"
        echo -e "PID:       ${pid}"
        echo -e "Uptime:    $(get_uptime "$pid")"
        echo -e "PID File:  ${PID_FILE}"

        # Show process details
        echo ""
        echo -e "${BLUE}Process Info:${NC}"
        get_process_info "$pid" | awk '{printf "  PID: %s\n  CPU: %s%%\n  Memory: %s%%\n  Time: %s\n", $1, $3, $4, $5}'

        # Check API if requested
        if [[ "$CHECK_API" == true ]]; then
            echo ""
            echo -e "${BLUE}API Health:${NC}"
            echo -e "  URL: ${API_URL}"
            echo -e "  Status: $(check_api_health)"
        fi

        return 0
    else
        echo -e "Status:    ${RED}STOPPED${NC}"
        echo -e "PID:       ${pid} (stale)"
        echo -e "PID File:  ${PID_FILE} (stale)"
        return 1
    fi
}

# Main function
main() {
    parse_args "$@"

    local exit_code=0

    if [[ "$JSON_OUTPUT" == true ]]; then
        output_json
        # Determine exit code based on process status
        local pid
        pid=$(get_pid)
        if ! is_running "$pid"; then
            exit_code=1
        fi
    else
        output_text || exit_code=$?
    fi

    exit $exit_code
}

# Run main
main "$@"
