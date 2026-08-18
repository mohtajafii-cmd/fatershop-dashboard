# routes/purchase.py
import sqlite3
import json
import jdatetime
import datetime
from flask import Blueprint, render_template, jsonify, request
from db_manager import (
    search_products_unified, 
    search_customers_advanced,
    get_cost_headers, 
    get_income_headers,
    normalize_persian_text
)

purchase_bp = Blueprint('purchase', __name__)

import os
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'holoo_cache.db')


def _get_api():
    """دریافت نمونه API با مدیریت خطا"""
    try:
        from holoo_api import HolooAPI
        import json as _json
        import os
        
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file = os.path.join(BASE_DIR, 'config.json')
        if not os.path.exists(config_file):
            return None
            
        with open(config_file, 'r', encoding='utf-8') as f:
            config = _json.load(f)
            
        api = HolooAPI(config)
        return api if api else None
    except Exception as e:
        print(f"❌ API Init Error in Purchase module: {e}")
        return None


def _load_config():
    """بارگذاری تنظیمات از config.json"""
    try:
        import os
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file = os.path.join(BASE_DIR, 'config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content:
                    return json.loads(content)
    except Exception as e:
        print(f"Error loading config in purchase module: {e}")
    
    return {
        "ip": "127.0.0.1", "port": "8080", "username": "admin",
        "password": "", "dbname": "Holoo1",
        "default_customer_erp": "", "default_bank_account": ""
    }


# ==================== صفحات ====================

@purchase_bp.route('/purchase/invoice')
def purchase_invoice_page():
    """صفحه ثبت فاکتور خرید"""
    return render_template('purchase_invoice.html')


# ==================== APIهای جستجو ====================

@purchase_bp.route('/api/purchase/products')
def api_purchase_products():
    """جستجوی کالاها برای فاکتور خرید"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    try:
        products, _ = search_products_unified(
            query=query, page=1, per_page=20, include_price=False
        )
        result = []
        for product in products:
            buy_price = product.get('BuyPrice', 0)
            sell_price = product.get('SellPrice', 0)
            few = product.get('Few', 0)
            result.append({
                "ErpCode": product.get('ErpCode'),
                "Name": product.get('Name'),
                "Code": product.get('Code'),
                "BuyPrice": float(buy_price) if float(buy_price) > 0 else float(sell_price),
                "SellPrice": float(sell_price),
                "Few": float(few)
            })
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error searching products for purchase: {e}")
        return jsonify([]), 500


@purchase_bp.route('/api/purchase/suppliers/search')
def api_purchase_suppliers_search():
    """جستجوی پیشرفته تامین‌کنندگان برای فاکتور خرید"""
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 20, type=int)
    if not query or len(query) < 1:
        return jsonify([])
    try:
        suppliers = search_customers_advanced(query, limit, is_seller=1)
        return jsonify(suppliers)
    except Exception as e:
        print(f"❌ Error searching suppliers: {e}")
        return jsonify([]), 500


@purchase_bp.route('/api/purchase/suppliers/search/all')
def api_purchase_suppliers_search_all():
    """جستجوی تامین‌کنندگان بدون فیلتر is_seller (برای تست/fallback)"""
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 20, type=int)
    if not query or len(query) < 1:
        return jsonify([])
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        search_term = f"%{query}%"
        c.execute('''
            SELECT erp_code, code, name FROM customers
            WHERE name LIKE ? OR code LIKE ?
            ORDER BY name LIMIT ?
        ''', (search_term, search_term, limit))
        rows = c.fetchall()
        conn.close()
        result = []
        for row in rows:
            result.append({
                "ErpCode": row[0],
                "Code": row[1] or '',
                "Name": row[2] or ''
            })
        return jsonify(result)
    except Exception as e:
        print(f"❌ API Error (suppliers/all): {e}")
        return jsonify([]), 500


@purchase_bp.route('/api/purchase/suppliers/default')
def api_purchase_suppliers_default():
    """دریافت تامین‌کننده پیش‌فرض"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        config = _load_config()
        default_erp = config.get('default_customer_erp', '')
        
        if default_erp:
            c.execute(
                'SELECT erp_code, code, name FROM customers WHERE erp_code = ? AND is_seller = 1',
                (default_erp,)
            )
            row = c.fetchone()
            if row:
                conn.close()
                return jsonify({
                    "ErpCode": row[0],
                    "Code": row[1] or '',
                    "Name": row[2] or ''
                })
        
        # اولین تامین‌کننده به عنوان fallback
        c.execute('SELECT erp_code, code, name FROM customers WHERE is_seller = 1 LIMIT 1')
        row = c.fetchone()
        conn.close()
        
        if row:
            return jsonify({
                "ErpCode": row[0],
                "Code": row[1] or '',
                "Name": row[2] or ''
            })
        return jsonify({"error": "No supplier found"}), 404
    except Exception as e:
        print(f"❌ Error getting default supplier: {e}")
        return jsonify({"error": str(e)}), 500


@purchase_bp.route('/api/suppliers/count')
def api_suppliers_count():
    """دریافت تعداد تامین‌کنندگان"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # اطمینان از وجود ستون is_seller
        c.execute("PRAGMA table_info(customers)")
        columns = [col[1] for col in c.fetchall()]
        if 'is_seller' not in columns:
            c.execute('ALTER TABLE customers ADD COLUMN is_seller INTEGER DEFAULT 0')
            conn.commit()
        c.execute('SELECT COUNT(*) FROM customers WHERE is_seller = 1')
        count = c.fetchone()[0]
        conn.close()
        return jsonify({"count": count})
    except Exception as e:
        print(f"❌ Error counting suppliers: {e}")
        return jsonify({"count": 0, "error": str(e)})


# ==================== تبدیل تاریخ ====================

@purchase_bp.route('/api/convert-date', methods=['POST'])
def convert_date():
    """تبدیل تاریخ شمسی به میلادی با jdatetime (دقیق)"""
    try:
        data = request.json
        shamsi_date = data.get('shamsi_date', '').strip()
        
        if not shamsi_date:
            return jsonify({"status": "error", "message": "تاریخ وارد نشده است"}), 400
        
        # تبدیل اعداد فارسی به انگلیسی
        persian_to_english = {
            '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
            '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
        }
        normalized_date = shamsi_date
        for persian, english in persian_to_english.items():
            normalized_date = normalized_date.replace(persian, english)
        
        parts = normalized_date.split('/')
        if len(parts) != 3:
            return jsonify({
                "status": "error",
                "message": "فرمت تاریخ صحیح نیست. مثال: ۱۴۰۵/۰۴/۲۲ یا 1405/04/22"
            }), 400
        
        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
        except ValueError:
            return jsonify({
                "status": "error",
                "message": "تاریخ باید شامل اعداد باشد"
            }), 400
        
        # اعتبارسنجی
        if year < 1300 or year > 1500:
            return jsonify({
                "status": "error",
                "message": f"سال {year} معتبر نیست. سال باید بین ۱۳۰۰ تا ۱۵۰۰ باشد"
            }), 400
        if month < 1 or month > 12:
            return jsonify({
                "status": "error",
                "message": f"ماه {month} معتبر نیست"
            }), 400
        if day < 1 or day > 31:
            return jsonify({
                "status": "error",
                "message": f"روز {day} معتبر نیست"
            }), 400
        
        # استفاده از jdatetime برای تبدیل دقیق
        try:
            shamsi = jdatetime.date(year, month, day)
            miladi = shamsi.togregorian()
            miladi_str = miladi.strftime('%Y-%m-%d')
        except Exception as e:
            # Fallback: روش تقریبی
            print(f"⚠️ jdatetime error: {e}, using fallback")
            miladi_year = year + 621
            miladi_month = month
            miladi_day = day
            if miladi_month == 2 and miladi_day > 28:
                miladi_day = 28
            elif miladi_day > 30 and miladi_month in (4, 6, 9, 11):
                miladi_day = 30
            miladi_date = datetime.date(miladi_year, miladi_month, miladi_day)
            miladi_str = miladi_date.strftime('%Y-%m-%d')
        
        return jsonify({
            "status": "success",
            "miladi_date": miladi_str,
            "shamsi_date": shamsi_date,
            "normalized": normalized_date
        })
    except Exception as e:
        print(f"❌ Error converting date: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"خطا در تبدیل تاریخ: {str(e)}"
        }), 500


# ==================== سرفصل‌های هزینه و درآمد ====================

@purchase_bp.route('/api/meta/cost-headers')
def api_cost_headers():
    """دریافت لیست سرفصل‌های هزینه از هلو (API مستقیم)"""
    api = _get_api()
    if not api:
        return jsonify([]), 500
    return jsonify(api.get_cost_headers())


@purchase_bp.route('/api/meta/income-headers')
def api_income_headers():
    """دریافت لیست سرفصل‌های درآمد از هلو (API مستقیم)"""
    api = _get_api()
    if not api:
        return jsonify([]), 500
    return jsonify(api.get_income_headers())


@purchase_bp.route('/api/meta/cost-headers/db')
def api_cost_headers_db():
    """دریافت لیست سرفصل‌های هزینه از دیتابیس محلی"""
    try:
        headers = get_cost_headers()
        return jsonify(headers)
    except Exception as e:
        print(f"❌ Error fetching cost headers from DB: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500


@purchase_bp.route('/api/meta/income-headers/db')
def api_income_headers_db():
    """دریافت لیست سرفصل‌های درآمد از دیتابیس محلی"""
    try:
        headers = get_income_headers()
        return jsonify(headers)
    except Exception as e:
        print(f"❌ Error fetching income headers from DB: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500