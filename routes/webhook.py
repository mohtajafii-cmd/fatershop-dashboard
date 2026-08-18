# routes/webhook.py - نسخه کامل و نهایی (جایگزین کامل فایل)
import json
import threading
import os
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from db_manager import save_product_batch, save_customers, DB_PATH

webhook_bp = Blueprint('webhook', __name__)
WEBHOOK_LOG_FILE = os.path.join(os.path.dirname(DB_PATH), 'webhook_logs.json')


def _log_webhook_event(table, operation, count, status, raw_data=None):
    """ذخیره لاگ رویدادهای وب‌هوک برای نمایش در داشبورد"""
    log_entry = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "table": table,
        "operation": operation,
        "items_count": count,
        "status": status,
        "details": str(raw_data)[:500] if raw_data else ""
    }
    
    logs = []
    if os.path.exists(WEBHOOK_LOG_FILE):
        try:
            with open(WEBHOOK_LOG_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except Exception:
            pass
    
    logs.insert(0, log_entry)
    logs = logs[:100]  # فقط ۱۰۰ لاگ آخر
    
    try:
        with open(WEBHOOK_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Error writing webhook log: {e}")


def _get_api_for_webhook():
    """دریافت نمونه API مخصوص وب‌هوک با مدیریت خطا"""
    try:
        from holoo_api import HolooAPI
        config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        if not os.path.exists(config_file):
            return None
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        api = HolooAPI(config)
        return api if api else None
    except Exception as e:
        print(f"❌ Webhook API Init Error: {e}")
        return None


def _refresh_entities_from_webhook(table_name, erp_codes):
    """
    ✅ بروزرسانی واقعی دیتابیس پس از دریافت وب‌هوک
    چون هلو فقط فیلدهای تغییر یافته را می‌فرستد، باید کل رکورد را دوباره از API بگیریم
    این تابع در ترد جداگانه اجرا می‌شود تا پاسخ وب‌هوک معطل نشود
    """
    if not erp_codes:
        return
    
    api = _get_api_for_webhook()
    if not api:
        print("⚠️ API not available for webhook refresh")
        _log_webhook_event(table_name, "REFRESH", 0, "API Unavailable")
        return
    
    refreshed = 0
    failed = 0
    
    for erp_code in erp_codes:
        try:
            if table_name == 'product':
                # مرحله ۱: پیدا کردن Code یا Name از کش محلی
                from db_manager import get_product_code_and_name_by_erp
                code, name = get_product_code_and_name_by_erp(erp_code)
                
                product = None
                # مرحله ۲: تلاش برای دریافت از API با Code
                if code:
                    product = api.get_product_by_code(code)
                
                # مرحله ۳: اگر با Code نشد، با Name تلاش کن
                if not product and name:
                    product = api.get_product_by_name(name)
                
                # مرحله ۴: ذخیره در دیتابیس
                if product:
                    save_product_batch([product])
                    refreshed += 1
                    print(f"✅ Product {erp_code} ({code}) refreshed via webhook")
                else:
                    failed += 1
                    print(f"⚠️ Could not find product {erp_code} in Holoo for refresh")
                    
            elif table_name == 'customer':
                # برای مشتریان: دریافت لیست و فیلتر
                customers = api.get_customers()
                matched = [c for c in customers if c.get('ErpCode') == erp_code]
                if matched:
                    save_customers(matched)
                    refreshed += 1
                    print(f"✅ Customer {erp_code} refreshed via webhook")
                else:
                    failed += 1
                    print(f"⚠️ Could not find customer {erp_code} in Holoo")
                    
        except Exception as e:
            failed += 1
            print(f"❌ Error refreshing {table_name} {erp_code}: {e}")
    
    status_msg = f"Refreshed: {refreshed}, Failed: {failed}"
    _log_webhook_event(table_name, "REFRESH", refreshed, status_msg)
    print(f"🔄 Webhook refresh complete: {status_msg}")


# ==================== اندپوینت‌های داشبورد ====================

@webhook_bp.route('/webhook', methods=['GET'])
def webhook_dashboard():
    """صفحه نمایش لاگ‌های وب‌هوک"""
    return render_template('webhook.html')


@webhook_bp.route('/webhook/logs', methods=['GET'])
def get_webhook_logs():
    """API دریافت لاگ‌ها برای نمایش زنده در داشبورد"""
    if not os.path.exists(WEBHOOK_LOG_FILE):
        return jsonify([])
    try:
        with open(WEBHOOK_LOG_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify([])


# ==================== اندپوینت دریافت وب‌هوک ====================

@webhook_bp.route('/webhook/receive', methods=['POST'])
def receive_holoo_webhook():
    """
    اندپوینت دریافت داده‌های وب‌هوک از لیارا/هلو
    پشتیبانی از:
    - ساختار لیستی n8n ([{body: {...}}])
    - ساختار مستقیم هلو ({Table: ..., changedfields: ...})
    - نام‌های مختلف فیلدها (tableName/Table, crudOperation/operation, changedFields/changedfields)
    - فرمت Stringified JSON در changedfields
    """
    try:
        raw_data = request.get_json(force=True)
        
        # ✅ مرحله ۱: استخراج داده اصلی از ساختارهای مختلف
        data = raw_data
        
        # اگر n8n داده را در آرایه پیچیده باشد: [{...}] یا [{"body": {...}}]
        if isinstance(data, list):
            if len(data) == 0:
                _log_webhook_event("Unknown", "ERROR", 0, "Empty List")
                return jsonify({"error": "Empty list received"}), 400
            data = data[0]
        
        # اگر هنوز لیست بود (nested list)
        if isinstance(data, list):
            data = data[0] if data else {}
        
        # اگر n8n داده را در کلید body پیچیده باشد: {"body": {...}}
        if isinstance(data, dict) and 'body' in data:
            body_data = data['body']
            if isinstance(body_data, list):
                data = body_data[0] if body_data else {}
            else:
                data = body_data
        
        # اعتبارسنجی نهایی
        if not isinstance(data, dict):
            _log_webhook_event("Unknown", "ERROR", 0, f"Invalid type: {type(data).__name__}")
            return jsonify({"error": f"Expected dict, got {type(data).__name__}"}), 400
        
        # ✅ مرحله ۲: استخراج فیلدها با پشتیبانی از تمام نام‌های ممکن
        table_name = (
            data.get('tableName') or 
            data.get('Table') or 
            data.get('table') or 
            ''
        ).strip().lower()
        
        operation = (
            data.get('crudOperation') or 
            data.get('operation') or 
            data.get('Operation') or 
            'UNKNOWN'
        ).strip().upper()
        
        dbname = data.get('dbname') or data.get('Dbname') or ''
        
        # ✅ مرحله ۳: استخراج changedFields با پشتیبانی از Stringified JSON
        changed_fields_raw = (
            data.get('changedFields') or 
            data.get('changedfields') or 
            data.get('ChangedFields') or 
            []
        )
        
        if isinstance(changed_fields_raw, str):
            try:
                changed_items = json.loads(changed_fields_raw)
            except json.JSONDecodeError:
                changed_items = []
        elif isinstance(changed_fields_raw, list):
            changed_items = changed_fields_raw
        elif isinstance(changed_fields_raw, dict):
            changed_items = [changed_fields_raw]
        else:
            changed_items = []
        
        items_count = len(changed_items) if isinstance(changed_items, list) else 0
        
        print(f"🔔 WEBHOOK RECEIVED: Table={table_name}, Op={operation}, Count={items_count}, DB={dbname}")
        
        # ✅ مرحله ۴: پردازش بر اساس نوع جدول
        erp_codes = []
        
        if table_name == 'product':
            erp_codes = [item.get('ErpCode') for item in changed_items if isinstance(item, dict) and item.get('ErpCode')]
            _log_webhook_event(table_name, operation, items_count, "Received", f"ERPs: {erp_codes[:5]}")
            
            # ✅ بروزرسانی خودکار از هلو در ترد جداگانه
            if erp_codes:
                threading.Thread(
                    target=_refresh_entities_from_webhook,
                    args=(table_name, erp_codes),
                    daemon=True
                ).start()
            
            return jsonify({"status": "success", "message": f"Processed {items_count} product changes"})

        elif table_name == 'customer':
            erp_codes = [item.get('ErpCode') for item in changed_items if isinstance(item, dict) and item.get('ErpCode')]
            _log_webhook_event(table_name, operation, items_count, "Received", f"Customers: {len(erp_codes)}")
            
            if erp_codes:
                threading.Thread(
                    target=_refresh_entities_from_webhook,
                    args=(table_name, erp_codes),
                    daemon=True
                ).start()
            
            return jsonify({"status": "success", "message": f"Processed {items_count} customer changes"})

        elif table_name in ('poshak', 'maingroup', 'sidegroup', 'resinvoice', 
                            'orderdetail', 'invoice', 'preinvoicedetail', 'picture'):
            _log_webhook_event(table_name, operation, items_count, "Received")
            return jsonify({"status": "success", "message": f"Processed {items_count} {table_name} changes"})

        else:
            _log_webhook_event(table_name or "unknown", operation, items_count, "Unknown Table")
            return jsonify({"status": "ignored", "message": f"Unknown table: {table_name}"}), 200

    except Exception as e:
        print(f"❌ WEBHOOK ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        _log_webhook_event("SYSTEM", "EXCEPTION", 0, str(e))
        return jsonify({"error": str(e)}), 500