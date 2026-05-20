#!/usr/bin/env bash

help() {

  cat <<-EOF
Usage: main.sh

Auto-runs run.py.
Creates a venv (virtual environment) if it doesn't exist already and installs necessary packages to it.

EOF
}

setup-venv() {
  # Check for python version
  local venv_created=false

  command -v python &>/dev/null
  local has_python="$?"

  command -v python3 &>/dev/null
  local has_python3="$?"

  if [[ "$has_python" == 0 ]]; then
    python -m venv venv
    venv_created=true
  fi

  if [[ "$venv_created" == false && "$has_python3" == 0 ]]; then
    python3 -m venv venv
    venv_created=true
  fi

  if [[ "$venv_created" == false ]]; then
    echo "Python not installed. Please install python, then try again."
    exit 1
  fi

  # Install required packages in virtual environment
  source venv/bin/activate
  pip install -r requirements.txt
  deactivate
}

main() {
  if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    help
    exit 0
  fi
  # Check for an existing virtual environment
  if [[ ! -d "venv" ]]; then
    echo "virtual environment not found. Creating one.."
    setup-venv
  fi

  # Check venv can be sourced
  if [[ ! -f "venv/bin/activate" ]]; then
    echo "virtual environment set up incorrectly. pls fix."
    exit 1
  fi

  # Run the downloader
  source venv/bin/activate
  python run.py
}

main "$@"
