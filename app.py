import os
import sys

# Fix Passenger/CGI ASCII encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from flask import Flask, redirect, url_for
from db_manager import init_all_tables
from routes import register_blueprints


# مقداردهی اولیه دیتابیس
init_all_tables()

# ایجاد اپلیکیشن
app = Flask(__name__)
# app.py - اضافه کردن توابع سراسری تمپلیت

def format_number(value):
    """فرمت کردن اعداد با جداکننده هزارگان"""
    if value is None: 
        return "-"
    try:
        return "{:,}".format(int(float(value)))
    except (ValueError, TypeError):
        return str(value)

FIELD_LABELS = {
    "ErpCode": "شناسه هلو", "SideGroupErpCode": "کد گروه فرعی",
    "Code": "کد کالا", "Name": "نام کالا", "Few": "موجودی",
    "FewKarton": "موجودی کارتن", "BuyPrice": "قیمت خرید",
    "SellPrice": "قیمت فروش (تیپ 1)", "SellPrice2": "قیمت فروش (تیپ 2)",
    "SellPrice3": "قیمت فروش (تیپ 3)", "SellPrice4": "قیمت فروش (تیپ 4)",
    "SellPrice5": "قیمت فروش (تیپ 5)", "SellPrice6": "قیمت فروش (تیپ 6)",
    "SellPrice7": "قیمت فروش (تیپ 7)", "SellPrice8": "قیمت فروش (تیپ 8)",
    "SellPrice9": "قیمت فروش (تیپ 9)", "SellPrice10": "قیمت فروش (تیپ 10)",
    "CountInKarton": "تعداد در کارتن", "CountInBasteh": "تعداد در بسته",
    "Other1": "وزن ارسال", "Other2": "طول", "Other3": "عرض",
    "Other4": "ارتفاع", "Other5": "حالت محصول", "Other6": "شناسه باسلام",
    "Other7": "مقدار درج شده روی کالا", "Other8": "کد دسته بندی باسلام",
    "Other9": "درصد پورسانت باسلام", "Other10": "زمان آماده سازی",
    "A_Country": "کشور سازنده", "Place": "محل ساخت", "Model": "مدل کالا",
    "Service": "خدماتی", "UnitErpCode": "کد واحد",
    "DiscountPrice": "مبلغ تخفیف", "DiscountPercent": "درصد تخفیف",
    "MinFew": "حداقل موجودی", "MaxFew": "حداکثر موجودی",
    "MainGroupName_Display": "نام گروه اصلی",
    "SideGroupName_Display": "نام گروه فرعی"
}

# ثبت سراسری برای استفاده در تمام تمپلیت‌ها
app.jinja_env.globals.update(format_number=format_number)
app.jinja_env.globals.update(FIELD_LABELS=FIELD_LABELS)
# ثبت تمام بلوپرینت‌ها
register_blueprints(app)

# ریدایرکت صفحه اصلی
@app.route('/')
def index():
    return redirect(url_for('products.single_edit'))

if __name__ == '__main__':
    app.run(debug=True)