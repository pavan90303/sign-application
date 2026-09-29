"""
WSGI config for A2SL project.

It exposes the WSGI callable as a module-level variable named ``application``.
Also exposes ``app`` for Vercel Serverless Function compatibility.
"""

import os
import sys
from pathlib import Path

# Add backend and project root directories to sys.path so 'A2SL', 'apps', 'shared', etc. can be resolved
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent

for d in (BACKEND_DIR, PROJECT_DIR):
    d_str = str(d)
    if d_str not in sys.path:
        sys.path.insert(0, d_str)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'A2SL.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

# Vercel Serverless Python runtime looks for 'app'
app = application
