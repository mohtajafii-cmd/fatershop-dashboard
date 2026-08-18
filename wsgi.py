# wsgi.py - نقطه ورود اپلیکیشن Flask برای cPanel/Passenger
import sys
import os

# ✅ تنظیم مسیر پروژه
PROJECT_PATH = '/home/stpskkfm/repositories/fatershop'
sys.path.insert(0, PROJECT_PATH)

# ✅ فعال‌سازی محیط مجازی پایتون 3.12
VENV_PATH = '/home/stpskkfm/virtualenv/repositories/fatershop/3.12'
activate_this = os.path.join(VENV_PATH, 'bin', 'activate_this.py')

if os.path.exists(activate_this):
    exec(open(activate_this).read(), {'__file__': activate_this})
else:
    # Fallback: اگر activate_this.py وجود نداشت، مسیر bin را به PATH اضافه کن
    venv_bin = os.path.join(VENV_PATH, 'bin')
    if venv_bin not in sys.path:
        sys.path.insert(0, venv_bin)

# ✅ ایمپورت اپلیکیشن فلَسک
# متغیر باید دقیقاً "application" باشد چون در Setup Python App این نام را وارد کرده‌اید
from app import app as application