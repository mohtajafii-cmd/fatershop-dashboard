# routes/pos.py
import time
import json
from flask import Blueprint, render_template, jsonify, request
from db_manager import (
    search_products_unified, get_bank_accounts, save_product_batch,
    get_product_code_and_name_by_erp
)

pos_bp = Blueprint('pos', __name__)
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
        print(f"❌ API Init Error in POS module: {e}")
        return None


# ==================== صفحات ====================

@pos_bp.route('/pos/invoice')
def pos_invoice_page():
    """صفحه اصلی ثبت فاکتور تک فروشی"""
    return render_template('pos_invoice.html')


# ==================== APIهای جستجو ====================

@pos_bp.route('/api/pos/products')
def api_pos_products():
    """جستجوی کالاها برای POS (فروش) با قیمت‌های کامل و تخفیف"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    try:
        products, _ = search_products_unified(
            query=query, page=1, per_page=20, include_price=True
        )
        result = []
        for product in products:
            full_data = product.get('FullData', {})
            sell_price = product.get('SellPrice', 0)
            discount_price = full_data.get('DiscountPrice') or full_data.get('discountprice') or 0
            discount_percent = full_data.get('DiscountPercent') or full_data.get('discountpercent') or 0
            few_tak = product.get('FewTak', 0)
            few = product.get('Few', 0)
            morecodes = full_data.get('morecodes') or full_data.get('Morecodes') or []

            final_price = float(sell_price)
            if discount_price > 0:
                final_price = final_price - float(discount_price)
            elif discount_percent > 0:
                final_price = final_price - (final_price * float(discount_percent) / 100)

            result.append({
                "ErpCode": product.get('ErpCode'),
                "Name": product.get('Name'),
                "Code": product.get('Code'),
                "SellPrice": float(sell_price),
                "DiscountPrice": float(discount_price),
                "DiscountPercent": float(discount_percent),
                "FinalPrice": round(final_price, 0),
                "Few": float(few),
                "FewTak": float(few_tak),
                "morecodes": morecodes
            })
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error searching POS products: {e}")
        return jsonify([]), 500


@pos_bp.route('/api/pos/products/count')
def api_products_count():
    """دریافت تعداد کل کالاها"""
    try:
        from db_manager import get_products_count
        count = get_products_count()
        return jsonify({"count": count})
    except Exception as e:
        return jsonify({"count": 0, "error": str(e)})


@pos_bp.route('/api/pos/customers')
def api_pos_customers():
    """دریافت لیست مشتریان (محدود به ۱۰۰ مورد برای جلوگیری از کرش)"""
    try:
        import sqlite3
        conn = sqlite3.connect('instance/holoo_cache.db')
        c = conn.cursor()
        c.execute('SELECT erp_code, code, name FROM customers ORDER BY name LIMIT 100')
        rows = c.fetchall()
        conn.close()
        result = []
        for row in rows:
            result.append({
                "ErpCode": row[0],
                "Code": row[1] or '',
                "Name": row[2] or '',
                "DisplayName": f"{row[1] or '---'} - {row[2]}" if row[1] else row[2] or row[0]
            })
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error fetching POS customers: {e}")
        return jsonify([]), 500


@pos_bp.route('/api/pos/customers/search')
def api_customers_search():
    """جستجوی پیشرفته مشتریان برای POS"""
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 20, type=int)
    if not query or len(query) < 1:
        return jsonify([])
    try:
        from db_manager import search_customers_advanced
        customers = search_customers_advanced(query, limit, is_purchaser=1)
        return jsonify(customers)
    except Exception as e:
        print(f"❌ Error searching POS customers: {e}")
        return jsonify([]), 500


@pos_bp.route('/api/pos/customers/count')
def api_customers_count():
    """دریافت تعداد کل مشتریان"""
    try:
        import sqlite3
        conn = sqlite3.connect('instance/holoo_cache.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM customers')
        count = c.fetchone()[0]
        conn.close()
        return jsonify({"count": count})
    except Exception as e:
        return jsonify({"count": 0})


@pos_bp.route('/api/pos/customers/default')
def api_default_customer():
    """دریافت مشتری پیش‌فرض (مشتری با کد 00007 یا تنظیمات)"""
    try:
        import sqlite3
        conn = sqlite3.connect('instance/holoo_cache.db')
        c = conn.cursor()

        # ابتدا از تنظیمات استفاده کن
        import json as _json, os
        config = {}
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                config = _json.load(f)

        default_erp = config.get('default_customer_erp', '')
        if default_erp:
            c.execute('SELECT erp_code, code, name FROM customers WHERE erp_code = ?', (default_erp,))
            row = c.fetchone()
            if row:
                conn.close()
                return jsonify({
                    "ErpCode": row[0],
                    "Code": row[1] or '',
                    "Name": row[2] or ''
                })

        # جستجوی مشتری با کد 00007
        c.execute('''
            SELECT erp_code, code, name FROM customers
            WHERE code = '00007' OR code LIKE '%00007%'
            LIMIT 1
        ''')
        row = c.fetchone()
        if row:
            conn.close()
            return jsonify({
                "ErpCode": row[0],
                "Code": row[1] or '',
                "Name": row[2] or ''
            })

        # اولین مشتری به عنوان fallback
        c.execute('SELECT erp_code, code, name FROM customers LIMIT 1')
        row = c.fetchone()
        conn.close()
        if row:
            return jsonify({
                "ErpCode": row[0],
                "Code": row[1] or '',
                "Name": row[2] or ''
            })
        return jsonify({"error": "No customer found"}), 404
    except Exception as e:
        print(f"❌ Error getting default customer: {e}")
        return jsonify({"error": str(e)}), 500


@pos_bp.route('/api/pos/bank-accounts')
def api_pos_bank_accounts():
    """دریافت حساب‌های بانکی دارای POS"""
    has_pos = request.args.get('has_pos')
    if has_pos is not None:
        has_pos = has_pos.lower() == 'true'
    return jsonify(get_bank_accounts(has_pos))


# ==================== ثبت فاکتور ====================

@pos_bp.route('/api/pos/register', methods=['POST'])
def api_pos_register():
    """ثبت نهایی فاکتور در هلو (هم فروش و هم خرید)"""
    data = request.json
    api = _get_api()
    if not api:
        return jsonify({"status": "error", "message": "ارتباط با API برقرار نشد"}), 500

    client_id = data.get('id')
    if not client_id:
        client_id = str(int(time.time() * 1000))

    # ساختار داده‌های فاکتور مطابق مستندات هلو
    invoice_info = {
        "id": client_id,
        "Type": data.get('type', 1),
        "customererpcode": data.get('customererpcode') or data.get('customerErpCode'),
        "date": data.get('date'),
        "time": data.get('time'),
        "comment": data.get('comment', ''),
        "detailinfo": data.get('detailinfo', [])
    }

    # اضافه کردن بخش‌های اختیاری
    if 'hazineinfo' in data and data['hazineinfo']:
        invoice_info["hazineinfo"] = data['hazineinfo']
    if 'incomeinfo' in data and data['incomeinfo']:
        invoice_info["incomeinfo"] = data['incomeinfo']
    if 'Cash' in data and data['Cash']:
        invoice_info["Cash"] = data['Cash']
        invoice_info["CashSarfasl"] = data.get('CashSarfasl', '10100010001')
    if 'Bank' in data and data['Bank']:
        invoice_info["Bank"] = data['Bank']
        invoice_info["BankSarfasl"] = data.get('BankSarfasl', '')
    if 'Nesiyeh' in data and data['Nesiyeh']:
        invoice_info["Nesiyeh"] = data['Nesiyeh']
    if 'Discount' in data and data['Discount']:
        invoice_info["Discount"] = data['Discount']
    if 'checkinfo' in data and data['checkinfo']:
        invoice_info["checkinfo"] = data['checkinfo']

    print(f"📤 Final Payload to Holoo: {json.dumps(invoice_info, ensure_ascii=False, indent=2)}")

    try:
        response = api.register_invoice(invoice_info)
        print(f"📥 Holoo Response: {json.dumps(response, ensure_ascii=False, indent=2)}")

        if response.get('Success'):
            success_data = response['Success']
            return jsonify({
                "status": "success",
                "erpCode": success_data.get('ErpCode'),
                "invoiceNumber": success_data.get('Code'),
                "documentNumber": success_data.get('SanadCode')
            })
        else:
            error_msg = response.get('Failure', {}).get('Error', 'خطای ناشناخته از سمت هلو')
            return jsonify({"status": "error", "message": error_msg}), 400
    except Exception as e:
        print(f"❌ Exception in register_invoice: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"خطا در ثبت فاکتور: {str(e)}"}), 500


# ==================== بروزرسانی موجودی پس از فاکتور ====================

@pos_bp.route('/api/update-product-stock', methods=['POST'])
def update_product_stock():
    """بروزرسانی موجودی کالاها بعد از ثبت فاکتور"""
    data = request.json
    product_erp_codes = data.get('product_erp_codes', [])
    if not product_erp_codes:
        return jsonify({"status": "error", "message": "کد کالا ارسال نشده است"}), 400

    api = _get_api()
    if not api:
        return jsonify({"status": "error", "message": "ارتباط با API برقرار نشد"}), 500

    updated_products = []
    failed_products = []

    for erp_code in product_erp_codes:
        try:
            code, name = get_product_code_and_name_by_erp(erp_code)
            product = None

            if code:
                product = api.get_product_by_code(code)
            if not product and name:
                product = api.get_product_by_name(name)

            if product:
                save_product_batch([product])
                updated_products.append({
                    "erp_code": erp_code,
                    "code": code,
                    "name": name,
                    "few": product.get('Few', 0)
                })
                print(f"✅ Product {erp_code} updated. New stock: {product.get('Few', 0)}")
            else:
                failed_products.append({
                    "erp_code": erp_code,
                    "error": "Product not found in Holoo"
                })
        except Exception as e:
            failed_products.append({
                "erp_code": erp_code,
                "error": str(e)
            })

    return jsonify({
        "status": "success",
        "updated": updated_products,
        "failed": failed_products
    })