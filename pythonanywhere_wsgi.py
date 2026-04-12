"""
WSGI config for PythonAnywhere.
Paste the path to this file in the PythonAnywhere Web tab → WSGI config file.
"""
import os
import sys

# Replace 'joyvet' with your PythonAnywhere username if different
PA_USERNAME = os.environ.get('PA_USERNAME', 'joyvet')
PROJECT_PATH = f'/home/{PA_USERNAME}/joyvet'

if PROJECT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_PATH)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joyvet.settings.pythonanywhere')
os.environ.setdefault('PA_USERNAME', PA_USERNAME)

from django.core.wsgi import get_wsgi_application  # noqa: E402
application = get_wsgi_application()
