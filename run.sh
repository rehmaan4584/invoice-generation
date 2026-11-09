#!/usr/bin/env bash
set -e

echo "======================================================================="
echo "    AI INVOICE PROCESSING & INTERNAL PURCHASE RECORD APPLICATION       "
echo "======================================================================="

# Verify Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10+."
    exit 1
fi

echo "[1/2] Checking dependencies..."
python3 -m pip install --prefer-binary -r requirements.txt

echo "[2/2] Launching Streamlit..."
streamlit run app.py
