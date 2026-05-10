#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/bin/scdframeware"
SCDTOOL_PATH="/bin/scdtool"
ROOT_FLAG="/root/.scdtool"

append_shell_rc() {
    local line="$1"
    local rcfile="$(echo $HOME)/.$(basename $SHELL)rc"
    if [ ! -f "$rcfile" ] || ! grep -Fxq "$line" "$rcfile" 2>/dev/null; then
        echo "$line" >> "$rcfile"
    fi
}

ensure_package() {
    if dpkg -s "$1" >/dev/null 2>&1; then
        echo "Package $1 already installed."
    else
        sudo apt install -y "$1"
    fi
}

if [ ! -d "$INSTALL_DIR" ]; then
    echo "Creating $INSTALL_DIR"
    sudo mkdir -p "$INSTALL_DIR"
else
    echo "$INSTALL_DIR already exists. Skipping creation."
fi

if [ ! -f "$ROOT_FLAG" ]; then
    echo "Creating empty root marker $ROOT_FLAG"
    sudo touch "$ROOT_FLAG"
    sudo chmod 600 "$ROOT_FLAG"
else
    echo "$ROOT_FLAG already exists."
fi

if [ ! -f "$SCDTOOL_PATH" ]; then
    if [ -f "$SCRIPT_DIR/scdtool.sh" ]; then
        echo "Copying $SCRIPT_DIR/scdtool.sh to $SCDTOOL_PATH"
        sudo cp "$SCRIPT_DIR/scdtool.sh" "$SCDTOOL_PATH"
        sudo chmod 755 "$SCDTOOL_PATH"
    else
        echo "Warning: $SCRIPT_DIR/scdtool.sh not found. Skipping /bin/scdtool creation."
    fi
else
    echo "$SCDTOOL_PATH already exists. Skipping copy."
fi

if [ "$(realpath "$SCRIPT_DIR")" != "$(realpath "$INSTALL_DIR")" ]; then
    echo "Moving repository contents to $INSTALL_DIR"
    shopt -s dotglob
    for item in "$SCRIPT_DIR"/* "$SCRIPT_DIR"/.[!.]* "$SCRIPT_DIR"/..?*; do
        [ -e "$item" ] || continue
        base="$(basename "$item")"
        if [ "$base" = "." ] || [ "$base" = ".." ]; then
            continue
        fi
        if [ "$item" = "$INSTALL_DIR" ] || [ "$item" = "$SCDTOOL_PATH" ]; then
            continue
        fi
        sudo mv "$item" "$INSTALL_DIR/"
    done
fi

sudo apt update
ensure_package make
ensure_package build-essential
ensure_package libssl-dev
ensure_package zlib1g-dev
ensure_package libbz2-dev
ensure_package libreadline-dev
ensure_package libsqlite3-dev
ensure_package wget
ensure_package curl
ensure_package llvm
ensure_package libncursesw5-dev
ensure_package xz-utils
ensure_package tk-dev
ensure_package libffi-dev
ensure_package liblzma-dev
ensure_package git

if ! command -v pyenv >/dev/null 2>&1; then
    echo "Installing pyenv"
    ensure_package pyenv
else
    echo "pyenv already installed."
fi

if command -v pyenv >/dev/null 2>&1; then
    if ! pyenv versions --bare | grep -qx "3.12.11"; then
        echo "Installing Python 3.12.11 via pyenv"
        pyenv install 3.12.11
    else
        echo "Python 3.12.11 already installed via pyenv."
    fi
    pyenv shell 3.12.11
fi

pip install --upgrade pip
pip install -r "$INSTALL_DIR/requirements.txt"

append_shell_rc 'export PYENV_ROOT="$HOME/.pyenv"'
append_shell_rc '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"'
append_shell_rc 'eval "$(pyenv init - zsh)"'
append_shell_rc 'export SCD_FRAMEWORK=1'

echo "Setup complete."

