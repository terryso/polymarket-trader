#!/bin/bash
#
# restart.sh - Restart the Polymarket Trader system
#
# Usage:
#   ./scripts/restart.sh [OPTIONS]
#
# Options:
#   -m, --mode MODE       Trading mode: paper or live (preserves current mode if not specified)
#   -c, --config FILE     Path to configuration file
#   -f, --force           Force stop before restart (SIGKILL)
#   -t, --timeout N       Timeout in seconds to wait for graceful shutdown (default: 30)
#   -d, --daemon          Run in daemon mode (background)
#   -l, --log-level LEVEL Log level: DEBUG, INFO, WARNING, ERROR
#   -h, --help            Show this help message
#
# Examples:
#   ./scripts/restart.sh              # Restart (graceful stop then start)
#   ./scripts/restart.sh --mode live  # Restart in live mode
#   ./scripts/restart.sh -d           # Restart in daemon mode
#   ./scripts/restart.sh --force      # Force stop then start
#

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
MODE="${BOT_MODE:-}"
CONFIG="${BOT_CONFIG:-}"
LOG_LEVEL="${BOT_LOG_LEVEL:-}"
DAEMON=false
FORCE=false
TIMEOUT=30

# PID file
PID_FILE="${PROJECT_ROOT}/.bot.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print usage
usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Restart the Polymarket Trader system (stop then start).

Options:
  -m, --mode MODE       Trading mode: paper or live (preserves current mode if not specified)
  -c, --config FILE     Path to configuration file
  -f, --force           Force stop before restart (SIGKILL)
  -t, --timeout N       Timeout in seconds to wait for graceful shutdown (default: 30)
  -d, --daemon          Run in daemon mode (background)
  -l, --log-level LEVEL Log level: DEBUG, INFO, WARNING, ERROR
  -h, --help            Show this help message

Environment Variables:
  BOT_MODE              Trading mode (paper/live)
  BOT_CONFIG            Configuration file path
  BOT_LOG_LEVEL         Log level

Examples:
  $(basename "$0")              # Restart (graceful stop then start)
  $(basename "$0") --mode live  # Restart in live mode
  $(basename "$0") -d           # Restart in daemon mode
  $(basename "$0") --force      # Force stop then start

Exit Codes:
  0   Success
  1   Error
EOF
}

# Log message
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[${timestamp}] [${level}] ${message}"
}

log_info() {
    log "INFO" "$@"
}

log_error() {
    log "ERROR" "${RED}$*${NC}" >&2
}

log_warning() {
    log "WARN" "${YELLOW}$*${NC}"
}

log_success() {
    log "INFO" "${GREEN}$*${NC}"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -m|--mode)
                MODE="$2"
                shift 2
                ;;
            -c|--config)
                CONFIG="$2"
                shift 2
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -d|--daemon)
                DAEMON=true
                shift
                ;;
            -l|--log-level)
                LOG_LEVEL="$2"
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

# Build stop arguments
build_stop_args() {
    local args=()

    if [[ "$FORCE" == true ]]; then
        args+=(--force)
    fi

    args+=(--timeout "$TIMEOUT")

    echo "${args[@]}"
}

# Build run arguments
build_run_args() {
    local args=()

    if [[ -n "$MODE" ]]; then
        args+=(--mode "$MODE")
    fi

    if [[ -n "$CONFIG" ]]; then
        args+=(--config "$CONFIG")
    fi

    if [[ "$DAEMON" == true ]]; then
        args+=(--daemon)
    fi

    if [[ -n "$LOG_LEVEL" ]]; then
        args+=(--log-level "$LOG_LEVEL")
    fi

    echo "${args[@]}"
}

# Main function
main() {
    parse_args "$@"

    log_info "========================================="
    log_info "Restarting Polymarket Trader"
    log_info "========================================="

    # Stop the application
    log_info "Stopping application..."
    local stop_args
    stop_args=$(build_stop_args)

    if ! "${SCRIPT_DIR}/stop.sh" $stop_args; then
        log_warning "Stop command returned non-zero exit code, continuing with start..."
    fi

    # Brief pause to ensure cleanup is complete
    sleep 1

    # Start the application
    log_info "Starting application..."
    local run_args
    run_args=$(build_run_args)

    exec "${SCRIPT_DIR}/run.sh" $run_args
}

# Run main
main "$@"
