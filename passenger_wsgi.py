# wsgi.py - نقطه ورود اپلیکیشن Flask برای cPanel/Passenger

import sys
import os

# مسیر واقعی پروژه
PROJECT_PATH = '/home/stpskkfm/public_html/authomation'

if PROJECT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_PATH)

# مسیر محیط مجازی واقعی
VENV_PATH = '/home/stpskkfm/virtualenv/public_html/authomation/3.12'

# اطمینان از دسترسی Python به site-packages
SITE_PACKAGES = os.path.join(
    VENV_PATH,
    'lib',
    'python3.12',
    'site-packages'
)

if SITE_PACKAGES not in sys.path:
    sys.path.insert(0, SITE_PACKAGES)

# ایمپورت اپلیکیشن Flask
from app import app as application