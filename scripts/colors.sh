#!/bin/bash
#
# Color and formatting definitions for visual output
# Source this file to use colors in your scripts: source scripts/colors.sh
#

# Check if terminal supports colors
if [ -t 1 ]; then
    # Regular colors
    export COLOR_BLACK='\033[0;30m'
    export COLOR_RED='\033[0;31m'
    export COLOR_GREEN='\033[0;32m'
    export COLOR_YELLOW='\033[0;33m'
    export COLOR_BLUE='\033[0;34m'
    export COLOR_MAGENTA='\033[0;35m'
    export COLOR_CYAN='\033[0;36m'
    export COLOR_WHITE='\033[0;37m'

    # Bold colors
    export COLOR_BOLD_BLACK='\033[1;30m'
    export COLOR_BOLD_RED='\033[1;31m'
    export COLOR_BOLD_GREEN='\033[1;32m'
    export COLOR_BOLD_YELLOW='\033[1;33m'
    export COLOR_BOLD_BLUE='\033[1;34m'
    export COLOR_BOLD_MAGENTA='\033[1;35m'
    export COLOR_BOLD_CYAN='\033[1;36m'
    export COLOR_BOLD_WHITE='\033[1;37m'

    # Background colors
    export BG_BLACK='\033[40m'
    export BG_RED='\033[41m'
    export BG_GREEN='\033[42m'
    export BG_YELLOW='\033[43m'
    export BG_BLUE='\033[44m'
    export BG_MAGENTA='\033[45m'
    export BG_CYAN='\033[46m'
    export BG_WHITE='\033[47m'

    # Reset
    export COLOR_RESET='\033[0m'

    # Formatting
    export TEXT_BOLD='\033[1m'
    export TEXT_DIM='\033[2m'
    export TEXT_UNDERLINE='\033[4m'
    export TEXT_BLINK='\033[5m'
    export TEXT_REVERSE='\033[7m'
    export TEXT_HIDDEN='\033[8m'
else
    # No color support - use empty strings
    export COLOR_BLACK=''
    export COLOR_RED=''
    export COLOR_GREEN=''
    export COLOR_YELLOW=''
    export COLOR_BLUE=''
    export COLOR_MAGENTA=''
    export COLOR_CYAN=''
    export COLOR_WHITE=''
    export COLOR_BOLD_BLACK=''
    export COLOR_BOLD_RED=''
    export COLOR_BOLD_GREEN=''
    export COLOR_BOLD_YELLOW=''
    export COLOR_BOLD_BLUE=''
    export COLOR_BOLD_MAGENTA=''
    export COLOR_BOLD_CYAN=''
    export COLOR_BOLD_WHITE=''
    export BG_BLACK=''
    export BG_RED=''
    export BG_GREEN=''
    export BG_YELLOW=''
    export BG_BLUE=''
    export BG_MAGENTA=''
    export BG_CYAN=''
    export BG_WHITE=''
    export COLOR_RESET=''
    export TEXT_BOLD=''
    export TEXT_DIM=''
    export TEXT_UNDERLINE=''
    export TEXT_BLINK=''
    export TEXT_REVERSE=''
    export TEXT_HIDDEN=''
fi

# Semantic colors
export COLOR_SUCCESS="${COLOR_BOLD_GREEN}"
export COLOR_ERROR="${COLOR_BOLD_RED}"
export COLOR_WARNING="${COLOR_BOLD_YELLOW}"
export COLOR_INFO="${COLOR_BOLD_BLUE}"
export COLOR_HIGHLIGHT="${COLOR_BOLD_CYAN}"
export COLOR_MUTED="${COLOR_DIM}"

# Status symbols
export SYMBOL_SUCCESS="✅"
export SYMBOL_ERROR="❌"
export SYMBOL_WARNING="⚠️ "
export SYMBOL_INFO="ℹ️ "
export SYMBOL_RUNNING="🔄"
export SYMBOL_STOPPED="⏳"
export SYMBOL_QUESTION="❓"
export SYMBOL_ROCKET="🚀"
export SYMBOL_BUILD="🏗️ "
export SYMBOL_TEST="🧪"
export SYMBOL_MONITOR="📊"
export SYMBOL_WRENCH="🔧"
export SYMBOL_DEPLOY="🚢"
export SYMBOL_DOCS="📚"
export SYMBOL_CODE="💻"
export SYMBOL_DATABASE="💾"
export SYMBOL_STAR="⭐"
export SYMBOL_FIRE="🔥"

# Helper functions for colored output
print_success() {
    echo -e "${COLOR_SUCCESS}${SYMBOL_SUCCESS} $1${COLOR_RESET}"
}

print_error() {
    echo -e "${COLOR_ERROR}${SYMBOL_ERROR} $1${COLOR_RESET}"
}

print_warning() {
    echo -e "${COLOR_WARNING}${SYMBOL_WARNING}$1${COLOR_RESET}"
}

print_info() {
    echo -e "${COLOR_INFO}${SYMBOL_INFO} $1${COLOR_RESET}"
}

print_highlight() {
    echo -e "${COLOR_HIGHLIGHT}$1${COLOR_RESET}"
}

print_header() {
    echo -e "\n${COLOR_BOLD_CYAN}╔══════════════════════════════════════════════════════╗${COLOR_RESET}"
    echo -e "${COLOR_BOLD_CYAN}║${COLOR_RESET}  $1"
    echo -e "${COLOR_BOLD_CYAN}╚══════════════════════════════════════════════════════╝${COLOR_RESET}\n"
}

print_section() {
    echo -e "\n${COLOR_BOLD_WHITE}┌──────────────────────────────────────────────────────┐${COLOR_RESET}"
    echo -e "${COLOR_BOLD_WHITE}│${COLOR_RESET}  $1"
    echo -e "${COLOR_BOLD_WHITE}└──────────────────────────────────────────────────────┘${COLOR_RESET}"
}

print_step() {
    local current=$1
    local total=$2
    local message=$3
    echo -e "${COLOR_INFO}[$current/$total]${COLOR_RESET} $message"
}
