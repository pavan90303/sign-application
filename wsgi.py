"""
Root WSGI Entrypoint for Vercel and Production WSGI Servers.
Delegates to backend/A2SL/wsgi.py.
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / 'backend'

for d in (BACKEND_DIR, ROOT_DIR):
    d_str = str(d)
    if d_str not in sys.path:
        sys.path.insert(0, d_str)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'A2SL.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

# Vercel Serverless Python runtime looks for 'app'
app = application
