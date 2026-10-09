"""WSGI entry point for cPanel's Phusion Passenger."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admission_portal.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
