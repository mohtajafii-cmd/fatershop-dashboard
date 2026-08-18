# routes/build.py
import json
import sqlite3
from flask import Blueprint, render_template, jsonify, request
from db_manager import search_products_unified, get_product_code_and_name_by_erp, save_product_batch

build_bp = Blueprint('build', __name__)

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
        print(f"❌ API Init Error in Build module: {e}")
        return None


# ==================== صفحات ====================

@build_bp.route('/build/product')
def build_product_page():
    """صفحه تولید کالا"""
    return render_template('build_product.html')


# ==================== APIهای جستجو ====================

@build_bp.route('/api/build/products')
def api_build_products():
    """جستجوی کالاها برای تولید با جستجوی یکسان"""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])
    try:
        products, _ = search_products_unified(
            query=query, page=1, per_page=30, include_price=False
        )
        result = []
        for product in products:
            result.append({
                "ErpCode": product.get('ErpCode'),
                "Name": product.get('Name'),
                "Code": product.get('Code'),
                "Few": product.get('Few', 0),
                "FewTak": product.get('FewTak', 0),
                "BuyPrice": product.get('BuyPrice', 0),
                "SellPrice": product.get('SellPrice', 0)
            })
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error searching build products: {e}")
        return jsonify([]), 500


@build_bp.route('/api/build/product-info')
def api_build_product_info():
    """دریافت اطلاعات کامل یک کالا برای تولید"""
    erp_code = request.args.get('erp', '').strip()
    if not erp_code:
        return jsonify({"error": "کد کالا وارد نشده است"}), 400
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT full_data FROM products WHERE erp_code = ?', (erp_code,))
        row = c.fetchone()
        conn.close()
        if row and row[0]:
            data = json.loads(row[0])
            return jsonify({
                "ErpCode": data.get('ErpCode', erp_code),
                "Name": data.get('Name', ''),
                "Code": data.get('Code', ''),
                "Few": data.get('Few', 0),
                "FewTak": data.get('FewTak', 0),
                "BuyPrice": data.get('BuyPrice', 0),
                "SellPrice": data.get('SellPrice', 0)
            })
        return jsonify({"error": "کالا یافت نشد"}), 404
    except Exception as e:
        print(f"❌ Error getting product info: {e}")
        return jsonify({"error": str(e)}), 500


@build_bp.route('/api/build/negative-stock')
def api_negative_stock():
    """دریافت کالاهای با موجودی منفی با صفحه‌بندی"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 200:
            per_page = 50
            
        offset = (page - 1) * per_page
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # شمارش کل
        c.execute('''
            SELECT COUNT(*)
            FROM products
            WHERE full_data LIKE '%"FewTak": -%'
               OR full_data LIKE '%"fewtak": -%'
        ''')
        total_count = c.fetchone()[0]
        
        # دریافت داده‌ها
        c.execute('''
            SELECT erp_code, name, code, full_data
            FROM products
            WHERE full_data LIKE '%"FewTak": -%'
               OR full_data LIKE '%"fewtak": -%'
            ORDER BY code
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        rows = c.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            full_data = json.loads(row[3]) if row[3] else {}
            fewtak = full_data.get('FewTak', 0) or full_data.get('fewtak', 0)
            code = row[2] or ''
            is_production = 'P' in code and len(code) > 10
            
            result.append({
                "ErpCode": row[0],
                "Name": row[1],
                "Code": code,
                "FewTak": fewtak,
                "type": "production" if is_production else "source"
            })
        
        total_pages = (total_count + per_page - 1) // per_page
        
        return jsonify({
            "items": result,
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        })
    except Exception as e:
        print(f"❌ Error getting negative stock: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@build_bp.route('/api/build/check-products', methods=['GET'])
def api_check_products():
    """بررسی وجود کالاها در هلو"""
    erp_codes = request.args.get('erps', '').split(',')
    if not erp_codes or erp_codes == ['']:
        return jsonify({"status": "error", "message": "کد کالا وارد نشده است"}), 400
    
    api = _get_api()
    if not api:
        return jsonify({"status": "error", "message": "ارتباط با API برقرار نشد"}), 500
    
    results = []
    for erp_code in erp_codes:
        erp_code = erp_code.strip()
        if not erp_code:
            continue
        try:
            import requests as req
            url = f"{api.base_url}/Product"
            params = {'erpcode': erp_code}
            response = req.get(url, headers=api.get_headers(), params=params)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('product', [])
                if products:
                    results.append({
                        "erp_code": erp_code,
                        "exists": True,
                        "code": products[0].get('Code'),
                        "name": products[0].get('Name'),
                        "few": products[0].get('Few'),
                        "fewtak": products[0].get('FewTak')
                    })
                else:
                    results.append({
                        "erp_code": erp_code,
                        "exists": False,
                        "error": "کالا یافت نشد"
                    })
            else:
                results.append({
                    "erp_code": erp_code,
                    "exists": False,
                    "error": f"خطا: {response.status_code}"
                })
        except Exception as e:
            results.append({
                "erp_code": erp_code,
                "exists": False,
                "error": str(e)
            })
    
    return jsonify({"status": "success", "results": results})


# ==================== ثبت تولید ====================

@build_bp.route('/api/build/product', methods=['POST'])
def api_build_product():
    """ثبت تولید کالا در هلو"""
    data = request.json
    api = _get_api()
    if not api:
        return jsonify({"status": "error", "message": "ارتباط با API برقرار نشد"}), 500
    
    try:
        payload = {
            "consumers": data.get('consumers', []),
            "production": data.get('production', {})
        }
        
        print(f"📤 Build Payload to Holoo: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        response = api.build_product(payload)
        print(f"📥 Holoo Build Response: {json.dumps(response, ensure_ascii=False, indent=2)}")
        
        # بررسی پاسخ موفق
        if response.get('status') == 'error':
            error_msg = response.get('message', 'خطای ناشناخته از سمت هلو')
            return jsonify({"status": "error", "message": error_msg}), 400
        
        if response.get('message') and 'موفق' in response.get('message', ''):
            return jsonify({
                "status": "success",
                "message": response.get('message', 'تولید با موفقیت انجام شد'),
                "clientId": response.get('clientId', ''),
                "documentCode": response.get('documentCode', '')
            })
        
        if response.get('Success'):
            return jsonify({
                "status": "success",
                "message": "تولید با موفقیت انجام شد",
                "clientId": response.get('Success', {}).get('Id', ''),
                "documentCode": response.get('Success', {}).get('ReturnParam1', '')
            })
        
        if response.get('Error'):
            return jsonify({"status": "error", "message": response.get('Error')}), 400
        
        return jsonify({"status": "error", "message": "پاسخ نامعتبر از سمت هلو"}), 400
        
    except Exception as e:
        print(f"❌ Exception in build_product: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500