# routes/products.py
import math
from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from db_manager import (
    search_products, get_product_full_info, get_erp_by_barcode,
    get_all_main_groups, get_all_side_groups, get_all_units,
    save_product_batch, get_product_code_and_name_by_erp
)

products_bp = Blueprint('products', __name__)

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


def _get_api():
    """دریافت نمونه API با مدیریت خطا"""
    try:
        from holoo_api import HolooAPI
        import json, os
        
        config_file = 'config.json'
        if not os.path.exists(config_file):
            return None
            
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        api = HolooAPI(config)
        return api if api else None
    except Exception as e:
        print(f"❌ API Init Error in Products module: {e}")
        return None


def _refresh_product_from_holoo(erp_code):
    """به‌روزرسانی اطلاعات یک کالا مستقیماً از هلو"""
    try:
        api = _get_api()
        if not api:
            return False
        
        code, name = get_product_code_and_name_by_erp(erp_code)
        product = None
        
        if code:
            product = api.get_product_by_code(code)
        if not product and name:
            product = api.get_product_by_name(name)
            
        if product:
            save_product_batch([product])
            return True
        return False
    except Exception as e:
        print(f"❌ Error refreshing product {erp_code}: {e}")
        return False


# ==================== صفحات ====================

@products_bp.route('/products-list')
def products_list_page():
    """لیست کالاها با جستجو و صفحه‌بندی"""
    query = request.args.get('q', '').strip()
    barcode = request.args.get('barcode', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    products, total_count = search_products(
        query=query, barcode=barcode, page=page, per_page=per_page
    )
    total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
    
    return render_template(
        'products.html', products=products, page=page,
        total_pages=total_pages, total_products=total_count,
        search_query=query, search_barcode=barcode,
        FIELD_LABELS=FIELD_LABELS
    )


@products_bp.route('/product-details/<erp_code>')
def product_details(erp_code):
    """صفحه جزئیات کامل کالا"""
    product = get_product_full_info(erp_code)
    if not product:
        return "Not found", 404
    return render_template('product_details.html', product=product, FIELD_LABELS=FIELD_LABELS)


@products_bp.route('/edit-product/<erp_code>')
def edit_product(erp_code):
    """صفحه ویرایش کالا"""
    product = get_product_full_info(erp_code)
    if not product:
        return "محصول یافت نشد", 404
    return render_template('edit_product.html', product=product, FIELD_LABELS=FIELD_LABELS)


@products_bp.route('/single-edit', methods=['GET', 'POST'])
def single_edit():
    """صفحه اسکن بارکد برای ویرایش سریع"""
    if request.method == 'POST':
        barcode = request.form.get('barcode', '').strip()
        query = request.form.get('name', '').strip()
        
        if barcode:
            erp_code = get_erp_by_barcode(barcode)
            if erp_code:
                return redirect(url_for('products.edit_product', erp_code=erp_code))
            else:
                return render_template('single_edit.html', product=None, 
                                     error="بارکد یافت نشد.", search_barcode=barcode)
        
        if query:
            prods, _ = search_products(query=query, page=1, per_page=1)
            if prods:
                return redirect(url_for('products.edit_product', erp_code=prods[0]['ErpCode']))
            else:
                return render_template('single_edit.html', product=None, 
                                     error="کالایی با این نام یافت نشد.", search_name=query)
    
    return render_template('single_edit.html', product=None, error=None)


# ==================== APIهای متادیتا ====================

@products_bp.route('/api/meta/main-groups')
def api_main_groups():
    """دریافت لیست گروه‌های اصلی"""
    return jsonify(get_all_main_groups())


@products_bp.route('/api/meta/side-groups')
def api_side_groups():
    """دریافت لیست گروه‌های فرعی"""
    main_erp = request.args.get('main_erp')
    return jsonify(get_all_side_groups(main_erp))


@products_bp.route('/api/meta/units')
def api_units():
    """دریافت لیست واحدها"""
    return jsonify(get_all_units())


# ==================== بروزرسانی کالا ====================

@products_bp.route('/update-product', methods=['POST'])
def update_product_route():
    """بروزرسانی اطلاعات کالا در هلو"""
    data = request.json
    erp_code = data.get('ErpCode')
    
    if not erp_code:
        return jsonify({"status": "error", "message": "ErpCode missing"}), 400
    
    api = _get_api()
    if not api:
        return jsonify({"status": "error", "message": "API Connection Failed"}), 500
    
    try:
        current_product = get_product_full_info(erp_code)
        if not current_product:
            return jsonify({"status": "error", "message": "Product not found in DB"}), 404
        
        payload_data = {
            'erpcode': erp_code,
            'name': current_product.get('Name'),
            'service': current_product.get('Service', False)
        }
        
        allowed_fields = [
            'Code', 'Model', 'UnitErpCode', 'MainGroupErpCode', 'SideGroupErpCode',
            'SellPrice', 'SellPrice2', 'SellPrice3', 'SellPrice4', 'SellPrice5',
            'SellPrice6', 'SellPrice7', 'SellPrice8', 'SellPrice9', 'SellPrice10',
            'DiscountPrice', 'DiscountPercent',
            'Other1', 'Other2', 'Other3', 'Other4', 'Other5', 'Other6', 'Other7',
            'Other8', 'Other9', 'Other10', 'A_Country', 'Place'
        ]
        
        has_changes = False
        for key in allowed_fields:
            new_val = data.get(key)
            old_val = current_product.get(key)
            
            if str(new_val) != str(old_val) and new_val is not None and new_val != "":
                api_key = key.lower()
                if key.startswith(('Sell', 'Discount')):
                    try:
                        payload_data[api_key] = float(new_val)
                    except ValueError:
                        continue
                else:
                    payload_data[api_key] = new_val
                has_changes = True
        
        if not has_changes:
            return jsonify({"status": "error", "message": "هیچ تغییری اعمال نشده است."}), 400
        
        response = api.update_product(payload_data)
        
        if response.get('Success'):
            _refresh_product_from_holoo(erp_code)
            success_msg = response.get('Success', {}).get('Message', 'تغییرات با موفقیت ذخیره شد.')
            return jsonify({"status": "success", "message": success_msg})
        else:
            error_msg = response.get('Failure', {}).get('Error', 'خطای ناشناخته')
            return jsonify({"status": "error", "message": error_msg}), 400
            
    except Exception as e:
        print(f"❌ Exception in update_product: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500