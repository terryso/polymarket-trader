#!/bin/bash
#
# logs.sh - View Polymarket Trader logs
#
# Usage:
#   ./scripts/logs.sh [OPTIONS]
#
# Options:
#   -f, --follow        Follow log output (tail -f)
#   -n, --lines N       Number of lines to show (default: 50)
#   -l, --level LEVEL   Filter by log level (DEBUG, INFO, WARNING, ERROR)
#   -s, --search TEXT   Search for text in logs
#   -h, --help          Show this help message
#
# Examples:
#   ./scripts/logs.sh              # Show last 50 lines
#   ./scripts/logs.sh -f           # Follow log output
#   ./scripts/logs.sh -n 100       # Show last 100 lines
#   ./scripts/logs.sh -l ERROR     # Show only ERROR level logs
#   ./scripts/logs.sh -s "market"  # Search for "market" in logs
#   ./scripts/logs.sh -f -l ERROR  # Follow and show only errors
#

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
FOLLOW=false
LINES=50
LEVEL=""
SEARCH=""

# Log file
LOG_DIR="${PROJECT_ROOT}/logs"
LOG_FILE="${LOG_DIR}/bot.log"

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

View Polymarket Trader logs.

Options:
  -f, --follow        Follow log output (tail -f)
  -n, --lines N       Number of lines to show (default: 50)
  -l, --level LEVEL   Filter by log level (DEBUG, INFO, WARNING, ERROR)
  -s, --search TEXT   Search for text in logs
  -h, --help          Show this help message

Examples:
  $(basename "$0")              # Show last 50 lines
  $(basename "$0") -f           # Follow log output
  $(basename "$0") -n 100       # Show last 100 lines
  $(basename "$0") -l ERROR     # Show only ERROR level logs
  $(basename "$0") -s "market"  # Search for "market" in logs
  $(basename "$0") -f -l ERROR  # Follow and show only errors

Log Levels:
  DEBUG    - Detailed debugging information
  INFO     - General information
  WARNING  - Warning messages
  ERROR    - Error messages only
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -f|--follow)
                FOLLOW=true
                shift
                ;;
            -n|--lines)
                LINES="$2"
                shift 2
                ;;
            -l|--level)
                LEVEL="$2"
                shift 2
                ;;
            -s|--search)
                SEARCH="$2"
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
}

# Colorize log output
colorize() {
    # Add colors to log levels
    sed -E \
        -e "s/\[ERROR\]/\\\\033[0;31m[ERROR]\\\\033[0m/g" \
        -e "s/\[WARN(ING)?\]/\\\\033[0;33m[WARN]\\1\\\\033[0m/g" \
        -e "s/\[INFO\]/\\\\033[0;32m[INFO]\\\\033[0m/g" \
        -e "s/\[DEBUG\]/\\\\033[0;34m[DEBUG]\\\\033[0m/g"
}

# Validate log level
validate_level() {
    local level="$1"
    local level_upper
    level_upper=$(echo "$level" | tr '[:lower:]' '[:upper:]')

    case "$level_upper" in
        DEBUG|INFO|WARNING|ERROR)
            echo "$level_upper"
            return 0
            ;;
        *)
            echo -e "${RED}Error: Invalid log level: ${level}${NC}" >&2
            echo -e "${YELLOW}Valid levels: DEBUG, INFO, WARNING, ERROR${NC}" >&2
            return 1
            ;;
    esac
}

# Filter by level using safe piped grep (no eval)
filter_by_level() {
    local level="$1"
    grep -E "\[${level}\]"
}

# Filter by search text using safe piped grep (no eval)
filter_by_search() {
    local search_text="$1"
    grep -i -- "$search_text"
}

# Check if log file exists
check_log_file() {
    if [[ ! -f "$LOG_FILE" ]]; then
        echo -e "${YELLOW}Log file not found: ${LOG_FILE}${NC}"
        echo -e "${YELLOW}The application may not be running or hasn't written any logs yet.${NC}"
        exit 0
    fi
}

# View logs
view_logs() {
    check_log_file

    # Validate level if provided
    if [[ -n "$LEVEL" ]]; then
        LEVEL=$(validate_level "$LEVEL") || exit 1
    fi

    if [[ "$FOLLOW" == true ]]; then
        echo -e "${BLUE}Following ${LOG_FILE}...${NC}"
        echo -e "${BLUE}Press Ctrl+C to stop${NC}"
        echo ""

        # Build safe pipeline without eval
        if [[ -n "$LEVEL" ]] && [[ -n "$SEARCH" ]]; then
            tail -f "$LOG_FILE" | filter_by_level "$LEVEL" | filter_by_search "$SEARCH" | colorize
        elif [[ -n "$LEVEL" ]]; then
            tail -f "$LOG_FILE" | filter_by_level "$LEVEL" | colorize
        elif [[ -n "$SEARCH" ]]; then
            tail -f "$LOG_FILE" | filter_by_search "$SEARCH" | colorize
        else
            tail -f "$LOG_FILE" | colorize
        fi
    else
        echo -e "${BLUE}Last ${LINES} lines from ${LOG_FILE}:${NC}"
        echo ""

        # Build safe pipeline without eval
        if [[ -n "$LEVEL" ]] && [[ -n "$SEARCH" ]]; then
            tail -n "$LINES" "$LOG_FILE" | filter_by_level "$LEVEL" | filter_by_search "$SEARCH" | colorize
        elif [[ -n "$LEVEL" ]]; then
            tail -n "$LINES" "$LOG_FILE" | filter_by_level "$LEVEL" | colorize
        elif [[ -n "$SEARCH" ]]; then
            tail -n "$LINES" "$LOG_FILE" | filter_by_search "$SEARCH" | colorize
        else
            tail -n "$LINES" "$LOG_FILE" | colorize
        fi
    fi
}

# Main function
main() {
    parse_args "$@"
    view_logs
}

# Run main
main "$@"
