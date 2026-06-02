#!/usr/bin/env bash
#
# install.sh — installeert systeem- en project-dependencies voor het mas-project.
#
# Stappen:
#   1. Installeer systeem-packages uit system-packages.txt (Debian/Ubuntu apt).
#   2. Verifieer dat Python 3.12+ aanwezig is.
#   3. Maak een virtual environment aan (venv/).
#   4. Installeer het pakket met dev-extras: pip install -e ".[dev]".
#
# Systeem-packages staan in system-packages.txt; Python-deps in pyproject.toml.
# Het script is idempotent en kan veilig opnieuw worden uitgevoerd.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
PKG_FILE="$SCRIPT_DIR/system-packages.txt"

# --- Logging helpers ---
info() { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; }

# Globale state, gezet door check_python.
PY=""

# --- Stap 1: systeem-dependencies ---
install_system_deps() {
    info "Systeem-dependencies controleren..."

    if [ ! -f "$PKG_FILE" ]; then
        warn "$PKG_FILE niet gevonden; systeem-dependencies worden overgeslagen."
        return 0
    fi

    # Lees packages in een array; skip comments en lege regels.
    local packages=()
    local line
    while IFS= read -r line || [ -n "$line" ]; do
        line="${line%%#*}"              # strip inline/regel-comments
        line="$(echo "$line" | xargs)"  # trim witruimte
        [ -z "$line" ] && continue
        packages+=("$line")
    done < "$PKG_FILE"

    if [ "${#packages[@]}" -eq 0 ]; then
        info "Geen systeem-packages opgegeven; niets te installeren."
        return 0
    fi

    if ! command -v apt-get >/dev/null 2>&1; then
        warn "apt-get niet gevonden — geen Debian/Ubuntu systeem."
        warn "Installeer deze packages handmatig: ${packages[*]}"
        return 0
    fi

    local sudo_cmd=""
    if [ "$(id -u)" -eq 0 ]; then
        sudo_cmd=""
    elif command -v sudo >/dev/null 2>&1; then
        sudo_cmd="sudo"
    else
        warn "Geen root-rechten en geen sudo — apt-installatie overgeslagen."
        warn "Installeer deze packages handmatig: ${packages[*]}"
        return 0
    fi

    info "Installeren via apt-get: ${packages[*]}"
    # apt-failures (bv. onbereikbare/ongerelateerde repos in beperkte omgevingen)
    # mogen de Python-stappen niet blokkeren — de toolchain is vaak al aanwezig.
    if ! $sudo_cmd apt-get update -qq; then
        warn "apt-get update mislukt; ga door met installatie van de packages."
    fi
    if ! $sudo_cmd apt-get install -y "${packages[@]}"; then
        warn "apt-get install mislukt; controleer of deze packages al aanwezig zijn: ${packages[*]}"
    fi
}

# --- Stap 2: Python 3.12+ verifiëren ---
check_python() {
    info "Python 3.12+ controleren..."

    if command -v python3.12 >/dev/null 2>&1; then
        PY="python3.12"
    elif command -v python3 >/dev/null 2>&1; then
        PY="python3"
    else
        err "Geen python3 gevonden. Installeer Python 3.12+ en probeer opnieuw."
        exit 1
    fi

    if ! "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
        local found
        found="$("$PY" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
        err "Python 3.12+ vereist, gevonden $found ($PY)."
        exit 1
    fi

    info "Python OK: $("$PY" --version 2>&1) ($PY)"
}

# --- Stap 3: virtual environment ---
create_venv() {
    if [ -d "$VENV_DIR" ]; then
        info "Bestaande venv hergebruiken: $VENV_DIR"
    else
        info "Virtual environment aanmaken: $VENV_DIR"
        "$PY" -m venv "$VENV_DIR"
    fi
}

# --- Stap 4: Python-dependencies ---
install_python_deps() {
    info "Python-dependencies installeren (pip install -e \".[dev]\")..."
    "$VENV_DIR/bin/python" -m pip install --upgrade pip
    "$VENV_DIR/bin/python" -m pip install -e "$SCRIPT_DIR[dev]"
}

# --- Afsluitende samenvatting ---
print_summary() {
    info "Installatie voltooid."
    cat <<'EOF'

Activeer de omgeving en draai de tests:

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
