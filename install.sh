#!/usr/bin/env bash
#
# install.sh — installs system and project dependencies for the mas project.
#
# Steps:
#   1. Install system packages from system-packages.txt (Debian/Ubuntu apt).
#   2. Verify Python 3.12+ is available.
#   3. Create a virtual environment (venv/).
#   4. Install the package with dev extras: pip install -e ".[dev]".
#
# System packages are declared in system-packages.txt; Python deps in pyproject.toml.
# The script is idempotent and can be re-run safely.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
PKG_FILE="$SCRIPT_DIR/system-packages.txt"

# --- Logging helpers ---
info() { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; }

# Global state set by check_python.
PY=""

# Run a command with sudo when not already root; falls back gracefully.
run_privileged() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        err "No root privileges and no sudo — cannot run: $*"
        return 1
    fi
}

# --- Step 1: system dependencies ---
install_system_deps() {
    info "Checking system dependencies..."

    if [ ! -f "$PKG_FILE" ]; then
        warn "$PKG_FILE not found; skipping system dependencies."
        return 0
    fi

    # Read packages into an array; skip comments and blank lines.
    local packages=()
    local line
    while IFS= read -r line || [ -n "$line" ]; do
        line="${line%%#*}"                        # strip inline comments
        line="${line#"${line%%[![:space:]]*}"}"   # trim leading whitespace
        line="${line%"${line##*[![:space:]]}"}"   # trim trailing whitespace
        [ -z "$line" ] && continue
        packages+=("$line")
    done < "$PKG_FILE"

    if [ "${#packages[@]}" -eq 0 ]; then
        info "No system packages listed; nothing to install."
        return 0
    fi

    if ! command -v apt-get >/dev/null 2>&1; then
        warn "apt-get not found — not a Debian/Ubuntu system."
        warn "Install these packages manually: ${packages[*]}"
        return 0
    fi

    if [ "$(id -u)" -ne 0 ] && ! command -v sudo >/dev/null 2>&1; then
        warn "No root privileges and no sudo — skipping apt installation."
        warn "Install these packages manually: ${packages[*]}"
        return 0
    fi

    info "Installing via apt-get: ${packages[*]}"
    # apt failures (e.g. unreachable PPAs in restricted environments) must not
    # block the Python steps — the toolchain is often already present.
    if ! run_privileged apt-get update -qq; then
        warn "apt-get update failed; continuing with package installation."
    fi
    if ! run_privileged apt-get install -y "${packages[@]}"; then
        warn "apt-get install failed; verify these packages are present: ${packages[*]}"
    fi
}

# --- Step 2: verify Python 3.12+ ---
check_python() {
    info "Checking for Python 3.12+..."

    local candidates=()
    command -v python3.12 >/dev/null 2>&1 && candidates+=("python3.12")
    command -v python3    >/dev/null 2>&1 && candidates+=("python3")

    if [ "${#candidates[@]}" -eq 0 ]; then
        err "No python3 found. Install Python 3.12+ and try again."
        exit 1
    fi

    for candidate in "${candidates[@]}"; do
        if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
            PY="$candidate"
            info "Python OK: $("$PY" --version 2>&1) ($PY)"
            return 0
        fi
    done

    local found
    found="$("${candidates[0]}" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
    err "Python 3.12+ required; found $found. Install python3.12 and try again."
    exit 1
}

# --- Step 3: virtual environment ---
create_venv() {
    if [ -d "$VENV_DIR" ]; then
        info "Reusing existing venv: $VENV_DIR"
    else
        info "Creating virtual environment: $VENV_DIR"
        "$PY" -m venv "$VENV_DIR"
    fi
}

# --- Step 4: Python dependencies ---
install_python_deps() {
    if [ ! -f "$SCRIPT_DIR/pyproject.toml" ]; then
        err "pyproject.toml not found in $SCRIPT_DIR. Are you running from the project root?"
        exit 1
    fi

    info "Installing Python dependencies (pip install -e \".[dev]\")..."
    "$VENV_DIR/bin/python" -m pip install --upgrade pip
    "$VENV_DIR/bin/python" -m pip install -e "$SCRIPT_DIR[dev]"
}

# --- Summary ---
print_summary() {
    info "Installation complete."
    cat <<'EOF'

Activate the environment and run the tests:

    source venv/bin/activate
    pytest -v
    python -m mas --version

EOF
}

main() {
    install_system_deps
    check_python
    create_venv
    install_python_deps
    print_summary
}

main "$@"
