#!/usr/bin/env bash
set -e

if command -v pyenv >/dev/null 2>&1; then
  PYENV_ROOT="$(pyenv root 2>/dev/null || echo "${PYENV_ROOT:-$HOME/.pyenv}")"
  export PYENV_ROOT
  export PATH="$PYENV_ROOT/bin:$PATH"
  eval "$(pyenv init --path)" 2>/dev/null || true
  eval "$(pyenv init -)" 2>/dev/null || true
  export PATH="$PYENV_ROOT/shims:$PATH"

  PYENV_SELECTED="$(pyenv versions --bare | awk '/^3\.12([.].*)?$/ {print}' | sort -V | tail -n1)"
  if [ -n "$PYENV_SELECTED" ]; then
    pyenv shell "$PYENV_SELECTED" >/dev/null 2>&1 || true
    # echo "Using pyenv Python $PYENV_SELECTED"
  else
    echo "pyenv: no installed 3.12.x version found. Using system Python."
  fi
fi

PYTHON=python3
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  PYTHON=python
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -d "$SCRIPT_DIR/scdframeware" ]; then
  "$PYTHON" "$SCRIPT_DIR/scdframeware/main.py"
else
# if system env SCD_FRAMEWORK is not set, run setup
if [ -z "$SCD_FRAMEWORK" ]; then
     echo "Running setup..."
     "$SCRIPT_DIR/setup.sh"
fi
  "$PYTHON" "$SCRIPT_DIR/main.py"
fi

# if user run tihs tool with scdtool --setup, run setup
if [ "$1" = "--setup" ]; then
    echo "Running setup..."
    "$SCRIPT_DIR/setup.sh"
    exit 0
fi
#  Update other time
# if user run tihs tool with scdtool --uninstall run uninstall
# if [ "$1" = "--uninstall" ]; then 
#     echo "Running uninstall..."
#     "$SCRIPT_DIR/uninstall.sh"
#     exit 0
# fi
