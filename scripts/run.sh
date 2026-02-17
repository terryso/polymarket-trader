#!/bin/bash
#
# run.sh - Start the Polymarket Trader system
#
# Usage:
#   ./scripts/run.sh [OPTIONS]
#
# Options:
#   -m, --mode MODE       Trading mode: paper (default) or live
#   -c, --config FILE     Path to configuration file
#   -d, --daemon          Run in daemon mode (background)
#   -l, --log-level LEVEL Log level: DEBUG, INFO, WARNING, ERROR
#   -h, --help            Show this help message
#
# Environment Variables:
#   BOT_MODE              Trading mode (paper/live)
#   BOT_CONFIG            Configuration file path
#   BOT_LOG_LEVEL         Log level
#
# Examples:
#   ./scripts/run.sh                         # Start in paper mode (foreground)
#   ./scripts/run.sh --mode live             # Start in live mode
#   ./scripts/run.sh --daemon                # Start in daemon mode
#   ./scripts/run.sh -m live -d -l DEBUG     # Live mode, daemon, debug logging
#

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
MODE="${BOT_MODE:-paper}"
CONFIG="${BOT_CONFIG:-}"
LOG_LEVEL="${BOT_LOG_LEVEL:-INFO}"
DAEMON=false

# PID and log files
PID_FILE="${PROJECT_ROOT}/.bot.pid"
LOG_DIR="${PROJECT_ROOT}/logs"
LOG_FILE="${LOG_DIR}/bot.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print usage
usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Start the Polymarket Trader system.

Options:
  -m, --mode MODE       Trading mode: paper (default) or live
  -c, --config FILE     Path to configuration file
  -d, --daemon          Run in daemon mode (background)
  -l, --log-level LEVEL Log level: DEBUG, INFO, WARNING, ERROR
  -h, --help            Show this help message

Environment Variables:
  BOT_MODE              Trading mode (paper/live)
  BOT_CONFIG            Configuration file path
  BOT_LOG_LEVEL         Log level

Examples:
  $(basename "$0")                         # Start in paper mode (foreground)
  $(basename "$0") --mode live             # Start in live mode
  $(basename "$0") --daemon                # Start in daemon mode
  $(basename "$0") -m live -d -l DEBUG     # Live mode, daemon, debug logging

Exit Codes:
  0   Success
  1   Error (configuration, dependencies, etc.)
  2   Another instance is already running
EOF
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

# Check if another instance is running
check_existing_instance() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null)

        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            log_error "Another instance is already running (PID: ${pid})"
            log_error "If this is incorrect, delete ${PID_FILE} and try again."
            exit 2
        else
            log_warning "Removing stale PID file (PID: ${pid})"
            rm -f "$PID_FILE"
        fi
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check virtual environment
    if [[ ! -d "${PROJECT_ROOT}/.venv" ]]; then
        log_error "Virtual environment not found at ${PROJECT_ROOT}/.venv"
        log_error "Please create it with: python3.11 -m venv .venv"
        exit 1
    fi

    # Check if virtual environment is activated or activate it
    if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        log_info "Activating virtual environment..."
        source "${PROJECT_ROOT}/.venv/bin/activate"
    fi

    # Check Python
    if ! command -v python &> /dev/null; then
        log_error "Python not found in virtual environment"
        exit 1
    fi

    # Check if src module is installed
    if ! python -c "import src" 2>/dev/null; then
        log_error "src module not found. Please run: pip install -e ."
        exit 1
    fi

    # Check configuration file if specified
    if [[ -n "$CONFIG" ]]; then
        if [[ ! -f "$CONFIG" ]]; then
            log_error "Configuration file not found: ${CONFIG}"
            exit 1
        fi
        log_info "Using configuration file: ${CONFIG}"
    fi

    # Check default .env file
    if [[ -z "$CONFIG" ]] && [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
        log_warning "No .env file found. Using default configuration."
    fi

    log_success "Prerequisites check passed"
}

# Create necessary directories
create_directories() {
    if [[ ! -d "$LOG_DIR" ]]; then
        log_info "Creating log directory: ${LOG_DIR}"
        mkdir -p "$LOG_DIR"
    fi
}

# Start the application
start_application() {
    local cmd_args=()

    cmd_args+=(--mode "$MODE")
    cmd_args+=(--log-level "$LOG_LEVEL")

    if [[ -n "$CONFIG" ]]; then
        cmd_args+=(--config "$CONFIG")
    fi

    if [[ "$DAEMON" == true ]]; then
        log_info "Starting in daemon mode..."
        log_info "Mode: ${MODE}"
        log_info "Log level: ${LOG_LEVEL}"
        log_info "Log file: ${LOG_FILE}"

        # Start in background
        nohup python -m src.main "${cmd_args[@]}" >> "$LOG_FILE" 2>&1 &
        local pid=$!

        # Wait a moment to check if process started successfully
        sleep 1

        if kill -0 "$pid" 2>/dev/null; then
            echo "$pid" > "$PID_FILE"
            log_success "Application started (PID: ${pid})"
            log_info "View logs: ./scripts/logs.sh -f"
            log_info "Check status: ./scripts/status.sh"
        else
            log_error "Failed to start application. Check logs: ${LOG_FILE}"
            exit 1
        fi
    else
        log_info "Starting in foreground mode..."
        log_info "Mode: ${MODE}"
        log_info "Log level: ${LOG_LEVEL}"
        log_info "Press Ctrl+C to stop"

        # Run in foreground
        exec python -m src.main "${cmd_args[@]}"
    fi
}

# Main function
main() {
    parse_args "$@"

    log_info "========================================="
    log_info "Polymarket Trader"
    log_info "========================================="

    check_existing_instance
    check_prerequisites
    create_directories
    start_application
}

# Run main
main "$@"
