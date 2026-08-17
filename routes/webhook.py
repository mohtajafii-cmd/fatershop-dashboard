# routes/webhook.py
import json
import sqlite3
import os
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from db_manager import save_product_batch, save_customers, DB_PATH

webhook_bp = Blueprint('webhook', __name__)

# مسیر فایل لاگ برای نمایش در UI
WEBHOOK_LOG_FILE = os.path.join(os.path.dirname(DB_PATH), 'webhook_logs.json')

def _log_webhook_event(table, operation, count, status, raw_data=None):
    """ذخیره لاگ رویدادهای وب‌هوک برای نمایش در داشبورد"""
    log_entry = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "table": table,
        "operation": operation,
        "items_count": count,
        "status": status,
        "details": str(raw_data)[:500] if raw_data else "" # ذخیره بخشی از دیتا برای دیباگ
    }
    
    logs = []
    if os.path.exists(WEBHOOK_LOG_FILE):
        try:
            with open(WEBHOOK_LOG_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except: pass
    
    logs.insert(0, log_entry)
    logs = logs[:100] # فقط ۱۰۰ لاگ آخر را نگه دار
    
    with open(WEBHOOK_LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


@webhook_bp.route('/webhook', methods=['GET'])
def webhook_dashboard():
    """صفحه نمایش لاگ‌های وب‌هوک"""
    return render_template('webhook.html')


@webhook_bp.route('/webhook/logs', methods=['GET'])
def get_webhook_logs():
    """API دریافت لاگ‌ها برای نمایش زنده"""
    if not os.path.exists(WEBHOOK_LOG_FILE):
        return jsonify([])
    try:
        with open(WEBHOOK_LOG_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except:
        return jsonify([])


@webhook_bp.route('/webhook/receive', methods=['POST'])
def receive_holoo_webhook():
    """
    اندپوینت دریافت داده‌های وب‌هوک از لیارا/هلو
    طبق مستندات: {Address}/webhook/receive
    """
    try:
        data = request.get_json(force=True)
        
        if not data:
            _log_webhook_event("Unknown", "ERROR", 0, "Empty Body")
            return jsonify({"error": "Empty body"}), 400

        table_name = data.get('Table', '').lower()
        operation = data.get('operation', 'UNKNOWN').upper()
        dbname = data.get('Dbname', '')
        
        # ✅ نکته مهم مستندات: changedfields ممکن است رشته JSON باشد
        changed_fields_raw = data.get('changedfields', [])
        if isinstance(changed_fields_raw, str):
            try:
                changed_items = json.loads(changed_fields_raw)
            except json.JSONDecodeError:
                changed_items = []
        else:
            changed_items = changed_fields_raw

        # اگر لیست نبود (مثلا دیکشنری تکی بود)، تبدیل به لیست کن
        if isinstance(changed_items, dict):
            changed_items = [changed_items]
            
        items_count = len(changed_items) if isinstance(changed_items, list) else 0
        
        print(f"🔔 WEBHOOK RECEIVED: Table={table_name}, Op={operation}, Count={items_count}")

        # ==================== پردازش بر اساس نوع جدول ====================
        
        # 1. کالاها (Product)
        if table_name == 'product':
            # برای محصولات، بهتر است ErpCode ها را بگیریم و از API هلو رفرش کنیم
            # یا اگر دیتای کامل آمده، مستقیم ذخیره کنیم.
            # اینجا فرض بر این است که دیتای کامل یا حداقل ErpCode آمده.
            erp_codes = [item.get('ErpCode') for item in changed_items if item.get('ErpCode')]
            
            # TODO: در نسخه پیشرفته‌تر، اینجا باید به API هلو درخواست بزنید تا دیتای تازه بگیرید
            # فعلاً فقط لاگ می‌کنیم که اطلاع داشته باشیم
            _log_webhook_event(table_name, operation, items_count, "Received", f"ERPs: {erp_codes[:5]}")
            
            # اگر دیتای کامل محصول در changedfields بود (مثل Few, Name و...)
            # می‌توانیم مستقیم آپدیت کنیم. اما چون هلو معمولا فقط فیلدهای تغییر یافته را می‌فرستد،
            # بهترین کار Trigger کردن یک Sync جزئی است.
            return jsonify({"status": "success", "message": f"Processed {items_count} product changes"})

        # 2. اشخاص / مشتریان (Customer)
        elif table_name == 'customer':
            # مشابه محصولات
            erp_codes = [item.get('ErpCode') for item in changed_items if item.get('ErpCode')]
            _log_webhook_event(table_name, operation, items_count, "Received", f"Customers updated: {len(erp_codes)}")
            return jsonify({"status": "success", "message": f"Processed {items_count} customer changes"})

        # 3. ویژگی‌ها (Poshak)
        elif table_name == 'poshak':
            _log_webhook_event(table_name, operation, items_count, "Received")
            return jsonify({"status": "success"})

        # 4. گروه اصلی (MainGroup)
        elif table_name == 'maingroup':
            _log_webhook_event(table_name, operation, items_count, "Received")
            return jsonify({"status": "success"})

        # 5. گروه فرعی (SideGroup)
        elif table_name == 'sidegroup':
            _log_webhook_event(table_name, operation, items_count, "Received")
            return jsonify({"status": "success"})

        # 6. فاکتور تک فروشی (ResInvoice)
        elif table_name == 'resinvoice':
            _log_webhook_event(table_name, operation, items_count, "Received")
            return jsonify({"status": "success"})

        # 7. سفارشات (OrderDetail)
        elif table_name == 'orderdetail':
            _log_webhook_event(table_name, operation, items_count, "Received")
            return jsonify({"status": "success"})

        # 8. فاکتورها (Invoice)
        elif table_name == 'invoice':
            _log_webhook_event(table_name, operation, items_count, "Received")
            return jsonify({"status": "success"})

        # 9. پیش فاکتورها (PreInvoiceDetail)
        elif table_name == 'preinvoicedetail':
            _log_webhook_event(table_name, operation, items_count, "Received")
            return jsonify({"status": "success"})

        # 10. تصاویر (Picture)
        elif table_name == 'picture':
            _log_webhook_event(table_name, operation, items_count, "Received")
            return jsonify({"status": "success"})

        else:
            _log_webhook_event(table_name, operation, items_count, "Unknown Table")
            return jsonify({"status": "ignored", "message": "Unknown table"}), 200

    except Exception as e:
        print(f"❌ WEBHOOK ERROR: {str(e)}")
        _log_webhook_event("SYSTEM", "EXCEPTION", 0, str(e))
        return jsonify({"error": str(e)}), 500