#!/bin/bash
#
# stop.sh - Stop the Polymarket Trader system
#
# Usage:
#   ./scripts/stop.sh [OPTIONS]
#
# Options:
#   -f, --force     Force stop (send SIGKILL instead of SIGTERM)
#   -t, --timeout N Timeout in seconds to wait for graceful shutdown (default: 30)
#   -h, --help      Show this help message
#
# Examples:
#   ./scripts/stop.sh           # Graceful stop (SIGTERM)
#   ./scripts/stop.sh --force   # Force stop (SIGKILL)
#   ./scripts/stop.sh -t 60     # Wait up to 60 seconds for graceful shutdown
#

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
FORCE=false
TIMEOUT=30

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

Stop the Polymarket Trader system gracefully.

Options:
  -f, --force       Force stop (send SIGKILL instead of SIGTERM)
  -t, --timeout N   Timeout in seconds to wait for graceful shutdown (default: 30)
  -h, --help        Show this help message

Examples:
  $(basename "$0")           # Graceful stop (SIGTERM)
  $(basename "$0") --force   # Force stop (SIGKILL)
  $(basename "$0") -t 60     # Wait up to 60 seconds for graceful shutdown

Exit Codes:
  0   Success (process stopped)
  1   Error (no process running, or failed to stop)
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -f|--force)
                FORCE=true
                shift
                ;;
            -t|--timeout)
                TIMEOUT="$2"
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

# Wait for process to exit
wait_for_exit() {
    local pid="$1"
    local timeout="$2"
    local count=0

    while is_running "$pid" && [[ $count -lt $timeout ]]; do
        sleep 1
        ((count++))
        printf "."
    done
    echo ""

    # Return 0 if process exited, 1 if still running
    if is_running "$pid"; then
        return 1
    else
        return 0
    fi
}

# Stop the application
stop_application() {
    local pid
    pid=$(get_pid)

    if [[ -z "$pid" ]]; then
        log_warning "No PID file found. System may not be running."
        exit 0
    fi

    if ! is_running "$pid"; then
        log_warning "Process (PID: ${pid}) is not running. Cleaning up PID file."
        rm -f "$PID_FILE"
        exit 0
    fi

    log_info "Stopping Polymarket Trader (PID: ${pid})..."

    if [[ "$FORCE" == true ]]; then
        log_warning "Force stopping (SIGKILL)..."
        kill -KILL "$pid" 2>/dev/null || {
            log_error "Failed to kill process ${pid}"
            exit 1
        }

        # Wait briefly for process to die
        sleep 1

        if is_running "$pid"; then
            log_error "Process ${pid} did not respond to SIGKILL"
            exit 1
        fi

        rm -f "$PID_FILE"
        log_success "Application stopped (forced)"
        exit 0
    fi

    # Graceful shutdown
    log_info "Sending SIGTERM for graceful shutdown..."
    kill -TERM "$pid" 2>/dev/null || {
        log_error "Failed to send SIGTERM to process ${pid}"
        exit 1
    }

    log_info "Waiting up to ${TIMEOUT} seconds for graceful shutdown"
    if wait_for_exit "$pid" "$TIMEOUT"; then
        rm -f "$PID_FILE"
        log_success "Application stopped gracefully"
        exit 0
    else
        log_warning "Graceful shutdown timed out after ${TIMEOUT} seconds"
        log_warning "Sending SIGKILL to force stop..."
        kill -KILL "$pid" 2>/dev/null || true

        sleep 1

        if is_running "$pid"; then
            log_error "Failed to stop process ${pid}"
            exit 1
        fi

        rm -f "$PID_FILE"
        log_success "Application stopped (forced after timeout)"
        exit 0
    fi
}

# Main function
main() {
    parse_args "$@"

    log_info "========================================="
    log_info "Stopping Polymarket Trader"
    log_info "========================================="

    stop_application
}

# Run main
main "$@"
