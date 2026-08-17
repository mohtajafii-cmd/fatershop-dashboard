# routes/batch_edit.py
import os
import pandas as pd
from flask import Blueprint, render_template, jsonify, request
from db_manager import get_erp_by_code_or_barcode, get_product_full_info
from excel_handler import ExcelHandler

batch_edit_bp = Blueprint('batch_edit', __name__)

# نمونه سراسری ExcelHandler برای این ماژول
excel_handler = ExcelHandler()


def _get_api():
    """دریافت نمونه API با مدیریت خطا"""
    try:
        from holoo_api import HolooAPI
        import json
        
        config_file = 'config.json'
        if not os.path.exists(config_file):
            return None
            
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        api = HolooAPI(config)
        return api if api else None
    except Exception as e:
        print(f"❌ API Init Error in BatchEdit module: {e}")
        return None


def _refresh_product_from_holoo(erp_code):
    """به‌روزرسانی اطلاعات یک کالا مستقیماً از هلو"""
    try:
        api = _get_api()
        if not api:
            print(f"❌ API not available for refresh")
            return False
        
        from db_manager import get_product_code_and_name_by_erp, save_product_batch
        
        code, name = get_product_code_and_name_by_erp(erp_code)
        product = None
        
        if code:
            product = api.get_product_by_code(code)
        if not product and name:
            product = api.get_product_by_name(name)
            
        if product:
            save_product_batch([product])
            print(f"✅ Product {erp_code} refreshed from Holoo")
            return True
        else:
            print(f"⚠️ Could not refresh product {erp_code} from Holoo")
            return False
    except Exception as e:
        print(f"❌ Error refreshing product {erp_code}: {e}")
        return False


# ==================== صفحات ====================

@batch_edit_bp.route('/batch-edit')
def batch_edit_page():
    """صفحه اصلی ویرایش دسته‌ای"""
    return render_template('batch_edit.html')


# ==================== مرحله ۱: آپلود فایل ====================

@batch_edit_bp.route('/batch-edit/upload', methods=['POST'])
def batch_edit_upload():
    """مرحله ۱: آپلود فایل و بازگرداندن نام ستون‌ها"""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "فایلی ارسال نشده"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "فایل خالی است"}), 400
    
    try:
        df = pd.read_excel(file)
        columns = df.columns.tolist()
        
        # ذخیره موقت فایل برای مراحل بعد
        temp_path = os.path.join('data', 'temp_upload.xlsx')
        os.makedirs('data', exist_ok=True)
        df.to_excel(temp_path, index=False)
        
        excel_handler.save_session({
            'file_path': temp_path,
            'columns': columns,
            'status': 'mapping'
        })
        
        print(f"✅ File uploaded. Columns: {columns}")
        return jsonify({"status": "success", "columns": columns})
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return jsonify({"status": "error", "message": f"خطا در خواندن فایل: {str(e)}"}), 500


# ==================== مرحله ۲: تحلیل فایل ====================

@batch_edit_bp.route('/batch-edit/analyze', methods=['POST'])
def batch_edit_analyze():
    """مرحله ۲: تحلیل فایل با نگاشت مشخص‌شده"""
    data = request.json
    barcode_col = data.get('barcode_col')
    price_col = data.get('price_col')
    discount_col = data.get('discount_col', '')
    currency = data.get('currency', 'rial')
    mode = data.get('mode', 'manual')
    
    session = excel_handler.load_session()
    if not session or 'file_path' not in session:
        return jsonify({"status": "error", "message": "Session منقضی شده. لطفاً دوباره فایل را آپلود کنید."}), 400
    
    try:
        df = pd.read_excel(session['file_path'])
        
        if barcode_col not in df.columns:
            return jsonify({"status": "error", "message": f"ستون '{barcode_col}' یافت نشد"}), 400
        if price_col not in df.columns:
            return jsonify({"status": "error", "message": f"ستون '{price_col}' یافت نشد"}), 400
        
        results = {
            'higher': [],
            'lower': [],
            'not_found': [],
            'equal': []
        }
        
        for idx, row in df.iterrows():
            barcode = str(row[barcode_col]).strip()
            if not barcode or barcode == 'nan':
                continue
            
            # جستجو هم در فیلد "کد کالا" و هم در "بارکدهای اضافی"
            erp_code = get_erp_by_code_or_barcode(barcode)
            
            if not erp_code:
                # بارکد/کد در DB نیست → ایجاد در آینده
                row_dict = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                item = {
                    'barcode': barcode,
                    'row_data': row_dict,
                    'reason': 'barcode_not_found'
                }
                results['not_found'].append(item)
                excel_handler.add_future(item)
                continue
            
            product = get_product_full_info(erp_code)
            if not product:
                continue
            
            holoo_price = float(product.get('SellPrice', 0) or 0)
            excel_price_raw = float(row.get(price_col, 0) or 0)
            
            # تبدیل تومان به ریال در صورت نیاز
            if currency == 'toman':
                excel_price = excel_price_raw * 10
            else:
                excel_price = excel_price_raw
            
            row_dict = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
            
            # تبدیل مبلغ تخفیف در صورت تومانی بودن
            if discount_col and discount_col in df.columns and currency == 'toman':
                disc_raw = row_dict.get(discount_col, 0) or 0
                try:
                    row_dict[discount_col + '_converted'] = float(disc_raw) * 10
                except:
                    row_dict[discount_col + '_converted'] = 0
            
            item = {
                'barcode': barcode,
                'erp_code': erp_code,
                'product_name': product.get('Name'),
                'holoo_price': holoo_price,
                'excel_price': excel_price,
                'excel_price_raw': excel_price_raw,
                'row_data': row_dict,
                'discount_col': discount_col,
                'currency': currency
            }
            
            # مقایسه قیمت‌ها و دسته‌بندی
            if excel_price > holoo_price:
                results['higher'].append(item)
            elif excel_price < holoo_price:
                results['lower'].append(item)
            else:
                results['equal'].append(item)
        
        # ذخیره نگاشت و نتایج در Session
        session['mapping'] = {
            'barcode_col': barcode_col,
            'price_col': price_col,
            'discount_col': discount_col,
            'currency': currency,
            'mode': mode
        }
        session['results'] = results
        excel_handler.save_session(session)
        
        print(f"✅ Analysis complete. Higher: {len(results['higher'])}, Not Found: {len(results['not_found'])}")
        
        return jsonify({
            "status": "success",
            "summary": {
                'higher': len(results['higher']),
                'lower': len(results['lower']),
                'not_found': len(results['not_found']),
                'equal': len(results['equal'])
            },
            "higher_items": results['higher'],
            "equal_items": results['equal'],
            "lower_items": results['lower']
        })
        
    except Exception as e:
        print(f"❌ Error in analysis: {e}")
        return jsonify({"status": "error", "message": f"خطا در تحلیل: {str(e)}"}), 500


# ==================== مرحله ۳: اعمال تغییرات ====================

@batch_edit_bp.route('/batch-edit/apply', methods=['POST'])
def batch_edit_apply():
    """اعمال تغییرات قیمت روی کالاهای انتخاب‌شده"""
    data = request.json
    selected_indices = data.get('selected_indices', [])
    mode = data.get('mode', 'manual')
    
    session = excel_handler.load_session()
    if not session or 'results' not in session:
        return jsonify({"status": "error", "message": "Session منقضی شده"}), 400
    
    results = session['results']
    mapping = session['mapping']
    
    api = _get_api()
    if not api:
        return jsonify({"status": "error", "message": "ارتباط با API برقرار نشد"}), 500
    
    applied = []
    failed = []
    items_to_process = results.get('higher', [])
    
    for idx, item in enumerate(items_to_process):
        if mode == 'manual' and idx not in selected_indices:
            continue
        
        erp_code = item['erp_code']
        excel_price = item['excel_price']
        
        payload = {
            'erpcode': erp_code,
            'name': item['product_name'],
            'sellprice': excel_price
        }
        
        # اضافه کردن تخفیف در صورت وجود
        discount_col = mapping.get('discount_col')
        if discount_col and discount_col in item['row_data']:
            if mapping.get('currency') == 'toman':
                disc_val = item['row_data'].get(discount_col + '_converted')
            else:
                disc_val = item['row_data'].get(discount_col)
            
            if disc_val is not None:
                try:
                    payload['discountprice'] = float(disc_val)
                except (ValueError, TypeError):
                    pass
        
        try:
            response = api.update_product(payload)
            
            if response.get('Success'):
                _refresh_product_from_holoo(erp_code)
                applied.append({
                    'barcode': item['barcode'],
                    'erp_code': erp_code,
                    'name': item['product_name'],
                    'message': response.get('Success', {}).get('Message', 'موفق')
                })
            else:
                error_msg = response.get('Failure', {}).get('Error', 'خطای ناشناخته')
                failed_item = {
                    'barcode': item['barcode'],
                    'erp_code': erp_code,
                    'name': item['product_name'],
                    'error': error_msg,
                    'payload': payload
                }
                failed.append(failed_item)
                excel_handler.add_problematic(failed_item)
                
        except Exception as e:
            failed_item = {
                'barcode': item['barcode'],
                'erp_code': erp_code,
                'name': item['product_name'],
                'error': str(e),
                'payload': payload
            }
            failed.append(failed_item)
            excel_handler.add_problematic(failed_item)
    
    return jsonify({
        "status": "success",
        "applied": len(applied),
        "failed": len(failed),
        "details": {"applied": applied, "failed": failed}
    })


# ==================== مدیریت آیتم‌های مشکل‌دار ====================

@batch_edit_bp.route('/batch-edit/problematic')
def batch_edit_problematic():
    """دریافت لیست آیتم‌های مشکل‌دار"""
    return jsonify(excel_handler.get_problematic())


@batch_edit_bp.route('/batch-edit/retry', methods=['POST'])
def batch_edit_retry():
    """تلاش مجدد برای آیتم‌های مشکل‌دار"""
    data = request.json
    indices = data.get('indices', [])
    items = excel_handler.get_problematic()
    
    api = _get_api()
    if not api:
        return jsonify({"status": "error", "message": "ارتباط با API برقرار نشد"}), 500
    
    retried = []
    still_failed = []
    
    for idx in sorted(indices, reverse=True):
        if 0 <= idx < len(items):
            item = items[idx]
            payload = item.get('payload', {})
            
            try:
                response = api.update_product(payload)
                
                if response.get('Success'):
                    _refresh_product_from_holoo(item['erp_code'])
                    retried.append(item['barcode'])
                    excel_handler.remove_problematic(idx)
                else:
                    error_msg = response.get('Failure', {}).get('Error', 'خطای ناشناخته')
                    still_failed.append({'barcode': item['barcode'], 'error': error_msg})
                    
            except Exception as e:
                still_failed.append({'barcode': item['barcode'], 'error': str(e)})
    
    return jsonify({
        "status": "success",
        "retried": len(retried),
        "still_failed": len(still_failed),
        "details": {"retried": retried, "still_failed": still_failed}
    })


@batch_edit_bp.route('/batch-edit/delete-problematic/<int:index>', methods=['DELETE'])
def delete_problematic(index):
    """حذف یک آیتم مشکل‌دار"""
    excel_handler.remove_problematic(index)
    return jsonify({"status": "success"})


# ==================== مدیریت آیتم‌های ایجاد در آینده ====================

@batch_edit_bp.route('/batch-edit/future')
def batch_edit_future():
    """دریافت لیست آیتم‌های ایجاد در آینده"""
    return jsonify(excel_handler.get_future())


@batch_edit_bp.route('/batch-edit/delete-future/<int:index>', methods=['DELETE'])
def delete_future(index):
    """حذف یک آیتم از لیست آینده"""
    excel_handler.remove_future(index)
    return jsonify({"status": "success"})


# ==================== بازنشانی Session ====================

@batch_edit_bp.route('/batch-edit/reset', methods=['POST'])
def batch_edit_reset():
    """پاک کردن Session فعلی و شروع مجدد"""
    excel_handler.clear_session()
    return jsonify({"status": "success"})