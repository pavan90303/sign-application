#!/bin/bash
# Vercel Build Script for SignAI Pro Django Application
set -e

echo "=== Installing Dependencies ==="
python3 -m pip install -r requirements.txt

echo "=== Collecting Static Files ==="
python3 manage.py collectstatic --noinput --clear

echo "=== Build Completed Successfully ==="
