#!/bin/bash
# ./bacup.sh
source venv/bin/activate
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi
python3 app.py
