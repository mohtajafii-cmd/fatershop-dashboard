# routes/allocation.py
import re, json, math, os
from flask import Blueprint, render_template, jsonify, request
from db_manager import get_product_full_info, save_product_batch, search_products_unified, save_formula, get_formula, delete_formula

allocation_bp = Blueprint('allocation', __name__)

def _get_api():
    try:
        from holoo_api import HolooAPI
        import json as _json
        config_file = 'config.json'
        if not os.path.exists(config_file): return None
        with open(config_file, 'r', encoding='utf-8') as f:
            config = _json.load(f)
        api = HolooAPI(config)
        return api if api else None
    except Exception as e:
        print(f"❌ Allocation API Error: {e}")
        return None

def parse_pack_barcode(barcode):
    """
    تجزیه هوشمند بارکد طبق استاندارد v2.0
    """
    if not barcode:
        return None, None, None, None
        
    barcode = str(barcode).strip().upper()
    
    # الگوی دقیق: ۱۳ رقم + (P یا PJ) + عدد + (اختیاری: GTx یا Gx)
    regex = r'^(\d{13})(P|PJ)(\d+)(GT\d|G\d)?$'
    match = re.match(regex, barcode)
    
    if not match:
        return None, None, None, None
        
    mother_code = match.group(1)
    prefix = match.group(2)      # 'P' or 'PJ'
    size = int(match.group(3))   # Pack Size
    price_type = match.group(4)  # e.g., 'GT1' or 'G2' or None
    
    pack_type = 'COMBO' if prefix == 'PJ' else 'SIMPLE'
    
    return mother_code, size, pack_type, price_type

@allocation_bp.route('/allocation')
def allocation_page():
    return render_template('allocation.html')


@allocation_bp.route('/api/allocation/mothers', methods=['GET'])
def get_mothers_list():
    """
    دریافت لیست تمام کالاهای مادر که حداقل یک فرزند (ساده یا ترکیبی) دارند.
    پشتیبانی از جستجو و صفحه‌بندی.
    """
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # دریافت همه کالاها برای تحلیل رابطه مادر-فرزندی
    # افزایش limit به 50000 برای پوشش بیشتر مادران در لیست اصلی
    all_products, total_all = search_products_unified(query=None, page=1, per_page=50000)
    
    mother_map = {} # code -> product_data
    children_map = {} # mother_code -> [list of children]
    
    for p in all_products:
        code = p.get('Code') or ''
        if not code: continue
        
        m_code, size, p_type, _ = parse_pack_barcode(code)
        
        if m_code:
            # این یک فرزند است (چه ساده چه ترکیبی)
            if m_code not in children_map:
                children_map[m_code] = []
            
            children_map[m_code].append({
                "ErpCode": p['ErpCode'],
                "Name": p.get('Name'),
                "Code": code,
                "Stock": float(p.get('FewTak', 0) or p.get('Few', 0)),
                "PackSize": size,
                "PackType": p_type # SIMPLE or COMBO
            })
            
            # اگر مادر هنوز در لیست مادران نیست، آن را پیدا کن
            if m_code not in mother_map:
                # جستجوی دقیق مادر بر اساس کد ۱۳ رقمی
                mom = next((x for x in all_products if (x.get('Code') or '').replace('-','').replace('.','') == m_code), None)
                if mom:
                    mother_map[m_code] = mom

    # تبدیل به لیست برای پاسخ
    mothers_list = []
    for m_code, mom_data in mother_map.items():
        if query:
            q_lower = query.lower()
            if q_lower not in (mom_data.get('Name') or '').lower() and q_lower not in (m_code or '').lower():
                continue
                
        mothers_list.append({
            "ErpCode": mom_data['ErpCode'],
            "Name": mom_data.get('Name', ''),
            "Code": m_code,
            "Stock": float(mom_data.get('FewTak', 0) or mom_data.get('Few', 0)),
            "ChildrenCount": len(children_map.get(m_code, []))
        })

    # صفحه‌بندی دستی
    total_items = len(mothers_list)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = mothers_list[start:end]
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1

    return jsonify({
        "items": paginated_items,
        "total": total_items,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    })

@allocation_bp.route('/api/allocation/details/<erp_code>', methods=['GET'])
def get_allocation_details(erp_code):
    """
    دریافت جزئیات کامل یک مادر و تمام فرزندانش برای مودال.
    ✅ اصلاح شده: استفاده مستقیم از API هلو برای اطمینان از یافتن تمام فرزندان
    """
    mother = get_product_full_info(erp_code)
    if not mother:
        return jsonify({"error": "Mother not found"}), 404
    
    mother_code = mother.get('Code', '')
    clean_mother_code = re.sub(r'[^0-9]', '', mother_code)
    
    api = _get_api()
    children = []
    
    if api:
        try:
            # دریافت تمام محصولات از هلو (یا جستجوی هوشمند)
            # نکته: چون هلو API جستجوی Regex ندارد، ما باید لیست را بگیریم و فیلتر کنیم
            # برای بهینه‌سازی، ابتدا سعی می‌کنیم از کش لوکال استفاده کنیم، اگر نبود از API
            all_products, _ = search_products_unified(query=None, page=1, per_page=50000)
            
            for p in all_products:
                child_code = p.get('Code') or ''
                m_code, size, p_type, price_type = parse_pack_barcode(child_code)
                
                # اگر بارکد فرزند با کد مادر مطابقت داشت
                if m_code and m_code == clean_mother_code:
                    children.append({
                        "ErpCode": p['ErpCode'],
                        "Name": p.get('Name', ''),
                        "Code": child_code,
                        "Stock": float(p.get('FewTak', 0) or p.get('Few', 0)),
                        "PackSize": size,
                        "PackType": p_type, # SIMPLE or COMBO
                        "PriceType": price_type
                    })
        except Exception as e:
            print(f"❌ Error fetching details from cache/API: {e}")
    else:
        # Fallback to local DB only if API is down
        all_products, _ = search_products_unified(query=None, page=1, per_page=5000)
        for p in all_products:
            child_code = p.get('Code') or ''
            m_code, size, p_type, price_type = parse_pack_barcode(child_code)
            if m_code and m_code == clean_mother_code:
                children.append({
                    "ErpCode": p['ErpCode'],
                    "Name": p.get('Name', ''),
                    "Code": child_code,
                    "Stock": float(p.get('FewTak', 0) or p.get('Few', 0)),
                    "PackSize": size,
                    "PackType": p_type,
                    "PriceType": price_type
                })

    # مرتب‌سازی: اول آنهایی که موجودی منفی دارند
    children.sort(key=lambda x: x['Stock'])

    return jsonify({
        "mother": {
            "ErpCode": erp_code,
            "Name": mother.get('Name', ''),
            "Code": mother_code,
            "Stock": float(mother.get('FewTak', 0) or mother.get('Few', 0))
        },
        "children": children
    })

@allocation_bp.route('/api/allocation/execute', methods=['POST'])
def execute_allocation():
    """
    اجرای عملیات ترکیبی:
    1. تولید از مادر به فرزند (Normal Build)
    2. بازگشت از فرزند به مادر (Reverse Build)
    """
    data = request.json
    operations = data.get('operations', []) 
    mother_erp = data.get('mother_erp')
    
    api = _get_api()
    if not api:
        return jsonify({"status": "error", "message": "API unavailable"}), 500

    results = []
    
    for op in operations:
        try:
            payload = {}
            desc = ""
            child_erp = op.get('child_erp')
            
            if op['type'] == 'PRODUCE_CHILD':
                # مصرف از مادر -> تولید فرزند
                if 'consumers' in op and isinstance(op['consumers'], list):
                     payload = {
                        "consumers": op['consumers'],
                        "production": {"aCode": child_erp, "few": op['produce_child']}
                    }
                else:
                    # حالت ساده تک مادری
                    payload = {
                        "consumers": [{"aCode": mother_erp, "few": op['consume_mother']}],
                        "production": {"aCode": child_erp, "few": op['produce_child']}
                    }
                desc = f"تولید {op['produce_child']} عدد {op.get('child_name', '')}"
                
            elif op['type'] == 'RETURN_TO_MOTHER':
                # مصرف از فرزند -> تولید مادر
                payload = {
                    "consumers": [{"aCode": child_erp, "few": op['consume_child']}],
                    "production": {"aCode": mother_erp, "few": op['produce_mother']}
                }
                desc = f"بازگشت {op['consume_child']} عدد {op.get('child_name', '')} به مادر"

            if payload:
                resp = api.build_product(payload)
                # ✅ بهبود تشخیص موفقیت: هم کلید Success و هم پیام فارسی را چک کن
                success = (resp.get('Success') is not None) or \
                          (resp.get('status') != 'error' and 'موفق' in str(resp.get('message', '')))
                
                if success:
                    # 🔄 بروزرسانی اجباری موجودی مادر و فرزند از هلو
                    erps_to_refresh = set([mother_erp])
                    if child_erp:
                        erps_to_refresh.add(child_erp)
                    
                    for erp in erps_to_refresh:
                        if erp:
                            try:
                                prod_info = get_product_full_info(erp)
                                if prod_info and prod_info.get('Code'):
                                    fresh_prod = api.get_product_by_code(prod_info['Code'])
                                    if fresh_prod:
                                        save_product_batch([fresh_prod])
                            except Exception as refresh_err:
                                print(f"❌ Error refreshing {erp}: {refresh_err}")

                results.append({
                    "description": desc,
                    "success": success,
                    "response": resp
                })
                
        except Exception as e:
            results.append({"description": op.get('desc', 'Unknown'), "success": False, "error": str(e)})

    return jsonify({"results": results})

@allocation_bp.route('/api/allocation/save-formula', methods=['POST'])
def save_allocation_formula():
    """ذخیره فرمول ساخت برای یک کالای سبدی (PJ)"""
    data = request.json
    child_erp = data.get('child_erp')
    ingredients = data.get('ingredients', []) # [{mother_erp, multiplier}]
    
    if not child_erp or not ingredients:
        return jsonify({"status": "error", "message": "اطلاعات ناقص"}), 400
    
    try:
        delete_formula(child_erp) # پاک کردن فرمول قبلی
        for ing in ingredients:
            save_formula(child_erp, ing['mother_erp'], ing['multiplier'])
        
        return jsonify({"status": "success", "message": "فرمول با موفقیت ذخیره شد"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@allocation_bp.route('/api/allocation/get-formula/<child_erp>', methods=['GET'])
def get_allocation_formula(child_erp):
    """دریافت فرمول ذخیره شده"""
    formula = get_formula(child_erp)
    return jsonify(formula)