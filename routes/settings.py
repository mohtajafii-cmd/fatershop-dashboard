# routes/settings.py
import json
import sqlite3
from flask import Blueprint, render_template, jsonify, request, redirect, url_for
import os
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'holoo_cache.db')

settings_bp = Blueprint('settings', __name__)

CONFIG_FILE = 'config.json'


def _load_config():
    """بارگذاری تنظیمات از فایل JSON"""
    default = {
        "ip": "127.0.0.1", "port": "8080", "username": "admin",
        "password": "", "dbname": "Holoo1",
        "default_customer_erp": "", "default_bank_account": ""
    }
    try:
        import os
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if content:
                    config = json.loads(content)
                    # اطمینان از وجود فیلدهای جدید
                    for key in default:
                        if key not in config:
                            config[key] = default[key]
                    return config
    except Exception as e:
        print(f"Error loading config: {e}")
    return default


def _save_config(config):
    """ذخیره تنظیمات در فایل JSON"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


# ==================== صفحات ====================

@settings_bp.route('/settings', methods=['GET', 'POST'])
def settings_page():
    """صفحه تنظیمات اتصال به هلو"""
    if request.method == 'POST':
        config = _load_config()
        config['ip'] = request.form.get('ip', config['ip'])
        config['port'] = request.form.get('port', config['port'])
        config['username'] = request.form.get('username', config['username'])
        config['password'] = request.form.get('password', config['password'])
        config['dbname'] = request.form.get('dbname', config['dbname'])
        _save_config(config)
        return redirect(url_for('settings.settings_page'))
    
    return render_template('settings.html', config=_load_config())


# ==================== APIهای تنظیمات ====================

@settings_bp.route('/api/settings/defaults', methods=['GET'])
def get_default_settings():
    """دریافت تنظیمات پیش‌فرض (مشتری و کارتخوان)"""
    config = _load_config()
    return jsonify({
        "default_customer_erp": config.get('default_customer_erp', ''),
        "default_bank_account": config.get('default_bank_account', '')
    })


@settings_bp.route('/api/settings/defaults', methods=['POST'])
def save_default_settings():
    """ذخیره تنظیمات پیش‌فرض"""
    data = request.json
    config = _load_config()
    config['default_customer_erp'] = data.get('default_customer_erp', '')
    config['default_bank_account'] = data.get('default_bank_account', '')
    _save_config(config)
    return jsonify({"status": "success"})


@settings_bp.route('/api/customers/list')
def api_customers_list():
    """دریافت لیست همه مشتریان برای dropdown تنظیمات"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT erp_code, code, name FROM customers ORDER BY code')
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
        print(f"❌ Error fetching customers list: {e}")
        return jsonify([]), 500


@settings_bp.route('/api/bank-accounts/list')
def api_bank_accounts_list():
    """دریافت لیست همه حساب‌های بانکی برای dropdown تنظیمات"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            SELECT account_number, bank_name, account_owner, sarfasl_code,
                   bank_code, sheba, card_number, has_pos, is_current
            FROM bank_accounts ORDER BY bank_name
        ''')
        rows = c.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            display_parts = []
            if row[1]: display_parts.append(row[1])
            if row[2]: display_parts.append(row[2])
            if row[0]:
                acc_num = str(row[0])
                display_parts.append(f"****{acc_num[-4:]}" if len(acc_num) > 4 else acc_num)
            if row[4]: display_parts.append(f"کد:{row[4]}")
            if row[6]:
                card = str(row[6])
                display_parts.append(f"کارت:****{card[-4:]}" if len(card) > 4 else card)
            if row[7]: display_parts.append("🟢 POS")
            if row[5]:
                sheba = str(row[5])
                display_parts.append(f"شبا:****{sheba[-4:]}" if len(sheba) > 4 else sheba)
            
            result.append({
                "accountNumber": row[0],
                "bankName": row[1] or '',
                "accountOwner": row[2] or '',
                "sarfaslCode": row[3] or '',
                "bankCode": row[4] or '',
                "sheba": row[5] or '',
                "cardNumber": row[6] or '',
                "hasPos": row[7] or 0,
                "isCurrent": row[8] or 0,
                "DisplayName": " - ".join(display_parts)
            })
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error fetching bank accounts list: {e}")
        return jsonify([]), 500