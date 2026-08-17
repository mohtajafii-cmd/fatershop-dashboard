# db_manager.py - اضافه کردن و اصلاح توابع جستجو

import sqlite3
import json
import os
import unicodedata

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, 'data', 'holoo_cache.db')
def normalize_persian_text(text):
    """نرمال‌سازی ی و ک عربی به فارسی"""
    if not text:
        return text
    text = str(text)
    text = text.replace('\u064a', '\u06cc')  # ي -> ی
    text = text.replace('\u0643', '\u06a9')  # ك -> ک
    text = text.replace('ي', '\u06cc')  # ي -> ی
    text = text.replace('ك', '\u06a9')  # ك -> ک
    return text.strip()

def search_customers(query=None, limit=20):
    """جستجوی مشتریان با کلمه به کلمه و نرمال‌سازی"""
    if not query or len(query.strip()) < 1:
        return []
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    normalized_query = normalize_persian_text(query)
    words = normalized_query.split()
    
    if not words:
        conn.close()
        return []
    
    conditions = []
    params = []
    
    for word in words:
        normalized_word = normalize_persian_text(word)
        conditions.append("(REPLACE(REPLACE(name, '\u064a', '\u06cc'), '\u0643', '\u06a9') LIKE ? OR REPLACE(REPLACE(code, '\u064a', '\u06cc'), '\u0643', '\u06a9') LIKE ?)")
        params.extend([f"%{normalized_word}%", f"%{normalized_word}%"])
    
    sql = f"""
        SELECT erp_code, code, name FROM customers 
        WHERE {' AND '.join(conditions)}
        ORDER BY 
            CASE 
                WHEN REPLACE(REPLACE(name, '\u064a', '\u06cc'), '\u0643', '\u06a9') = ? THEN 0
                WHEN REPLACE(REPLACE(name, '\u064a', '\u06cc'), '\u0643', '\u06a9') LIKE ? THEN 1
                ELSE 2
            END,
            name
        LIMIT ?
    """
    
    # اضافه کردن پارامترهای مرتب‌سازی
    params.insert(0, normalized_query)
    params.insert(1, f"{normalized_query}%")
    params.append(limit)
    
    try:
        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            result.append({
                "ErpCode": row[0],
                "Code": row[1] or '',
                "Name": row[2] or ''
            })
        return result
    except Exception as e:
        print(f"❌ Error searching customers: {e}")
        conn.close()
        return []

# db_manager.py - بازنویسی کامل تابع search_suppliers

def search_suppliers(query=None, limit=20):
    """جستجوی تامین‌کنندگان (فروشندگان) با کلمه به کلمه و نرمال‌سازی"""
    if not query or len(query.strip()) < 1:
        print("⚠️ Empty query for supplier search")
        return []
    
    print(f"🔍 Searching suppliers with query: '{query}'")
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # بررسی وجود جدول customers
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
        table_exists = c.fetchone()
        if not table_exists:
            print("❌ Table 'customers' does not exist")
            return []
        
        # بررسی وجود ستون is_seller و اضافه کردن اگر وجود ندارد
        try:
            c.execute("PRAGMA table_info(customers)")
            columns = [col[1] for col in c.fetchall()]
            if 'is_seller' not in columns:
                print("⚠️ Column 'is_seller' not found, adding it...")
                c.execute('ALTER TABLE customers ADD COLUMN is_seller INTEGER DEFAULT 0')
                conn.commit()
                print("✅ Added 'is_seller' column")
        except Exception as e:
            print(f"⚠️ Error checking/adding is_seller column: {e}")
        
        # نرمال‌سازی عبارت جستجو
        normalized_query = normalize_persian_text(query)
        words = normalized_query.split()
        
        if not words:
            conn.close()
            return []
        
        # ساخت کوئری جستجو
        conditions = []
        params = []
        
        for word in words:
            normalized_word = normalize_persian_text(word)
            # جستجو در name و code
            conditions.append("(name LIKE ? OR code LIKE ?)")
            params.append(f"%{normalized_word}%")
            params.append(f"%{normalized_word}%")
        
        # کوئری نهایی - بدون استفاده از REPLACE برای جلوگیری از خطا
        sql = f"""
            SELECT erp_code, code, name FROM customers 
            WHERE is_seller = 1 AND {' AND '.join(conditions)}
            ORDER BY name
            LIMIT ?
        """
        params.append(limit)
        
        print(f"📤 SQL Query: {sql}")
        print(f"📤 Params: {params}")
        
        c.execute(sql, params)
        rows = c.fetchall()
        
        print(f"✅ Found {len(rows)} suppliers")
        
        result = []
        for row in rows:
            result.append({
                "ErpCode": row[0],
                "Code": row[1] or '',
                "Name": row[2] or ''
            })
        
        # نمایش نتایج برای دیباگ
        for i, sup in enumerate(result[:5]):
            print(f"  {i+1}. Code: {sup['Code']}, Name: {sup['Name']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error in search_suppliers: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if conn:
            conn.close()


def init_db():
    os.makedirs('instance', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # جدول محصولات اصلی
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (
                     erp_code
                     TEXT
                     PRIMARY
                     KEY,
                     name
                     TEXT,
                     code
                     TEXT,
                     buy_price
                     REAL,
                     sell_price
                     REAL,
                     full_data
                     TEXT
                 )''')

    # جدول بارکدها
    c.execute('''CREATE TABLE IF NOT EXISTS barcodes
    (
        barcode
        TEXT
        PRIMARY
        KEY,
        erp_code
        TEXT,
        FOREIGN
        KEY
                 (
        erp_code
                 ) REFERENCES products
                 (
                     erp_code
                 ))''')

    # جدول ویژگی‌های کالا (Poshak)
    c.execute('''CREATE TABLE IF NOT EXISTS product_poshak
    (
        id
        INTEGER
        PRIMARY
        KEY
        AUTOINCREMENT,
        erp_code
        TEXT,
        poshak_id
        INTEGER,
        parent_id
        INTEGER,
        name
        TEXT,
        few
        REAL,
        min_price
        REAL,
        max_price
        REAL,
        FOREIGN
        KEY
                 (
        erp_code
                 ) REFERENCES products
                 (
                     erp_code
                 ))''')

    # --- جداول جدید برای کش کردن نام‌ها ---

    # جدول گروه‌های اصلی
    c.execute('''CREATE TABLE IF NOT EXISTS main_groups
                 (
                     erp_code
                     TEXT
                     PRIMARY
                     KEY,
                     name
                     TEXT
                 )''')

    # جدول گروه‌های فرعی
    c.execute('''CREATE TABLE IF NOT EXISTS side_groups
                 (
                     erp_code
                     TEXT
                     PRIMARY
                     KEY,
                     name
                     TEXT,
                     main_group_erp
                     TEXT
                 )''')

    # جدول واحدها
    c.execute('''CREATE TABLE IF NOT EXISTS units
                 (
                     erp_code
                     TEXT
                     PRIMARY
                     KEY,
                     name
                     TEXT
                 )''')

    conn.commit()
    conn.close()


def clear_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM products')
    c.execute('DELETE FROM barcodes')
    c.execute('DELETE FROM product_poshak')
    c.execute('DELETE FROM main_groups')
    c.execute('DELETE FROM side_groups')
    c.execute('DELETE FROM units')
    conn.commit()
    conn.close()


def save_main_groups(groups):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for g in groups:
        c.execute('INSERT OR REPLACE INTO main_groups (erp_code, name) VALUES (?, ?)', (g['ErpCode'], g['Name']))
    conn.commit()
    conn.close()


def save_side_groups(groups):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for g in groups:
        c.execute('INSERT OR REPLACE INTO side_groups (erp_code, name, main_group_erp) VALUES (?, ?, ?)',
                  (g['ErpCode'], g['Name'], g.get('MainErpCode')))
    conn.commit()
    conn.close()


def save_units(units_list):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # توجه: خروجی API واحد ممکن است یک آبجکت تکی یا لیست باشد، اینجا فرض بر لیست است
    if isinstance(units_list, dict):
        units_list = [units_list]

    for u in units_list:
        c.execute('INSERT OR REPLACE INTO units (erp_code, name) VALUES (?, ?)', (u['ErpCode'], u['Name']))
    conn.commit()
    conn.close()


def get_name_by_erp(table_name, erp_code):
    """تابع عمومی برای دریافت نام از روی ErpCode"""
    if not erp_code: return ""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(f'SELECT name FROM {table_name} WHERE erp_code = ?', (erp_code,))
        result = c.fetchone()
        return result[0] if result else erp_code
    except:
        return erp_code
    finally:
        conn.close()

# db_manager.py - اضافه شده به انتهای فایل برای مدیریت فرمول‌های سبد کالا (PJ)

def init_allocation_formulas_table():
    """ایجاد جدول برای ذخیره فرمول‌های ساخت سبد کالا (PJ)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS allocation_formulas
    (
        child_erp TEXT,       -- شناسه کالای تولیدی (سبد)
        mother_erp TEXT,      -- شناسه کالای مادر (ماده اولیه)
        multiplier REAL,      -- ضریب مصرف (تعداد مورد نیاز از این مادر برای یک سبد)
        PRIMARY KEY (child_erp, mother_erp)
    )''')
    conn.commit()
    conn.close()

def save_formula(child_erp, mother_erp, multiplier):
    """ذخیره یا بروزرسانی یک ردیف از فرمول ساخت"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO allocation_formulas (child_erp, mother_erp, multiplier) VALUES (?, ?, ?)',
              (child_erp, mother_erp, float(multiplier)))
    conn.commit()
    conn.close()

def get_formula(child_erp):
    """دریافت لیست تمام مواد اولیه و ضرایب برای یک کالای سبدی"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT mother_erp, multiplier FROM allocation_formulas WHERE child_erp = ?', (child_erp,))
    rows = c.fetchall()
    conn.close()
    return [{"mother_erp": r[0], "multiplier": r[1]} for r in rows]

def delete_formula(child_erp):
    """حذف فرمول قدیمی برای جایگزینی"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM allocation_formulas WHERE child_erp = ?', (child_erp,))
    conn.commit()
    conn.close()



def get_all_main_groups():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT erp_code, name FROM main_groups ORDER BY name')
    rows = c.fetchall()
    conn.close()
    return [{"ErpCode": r[0], "Name": r[1]} for r in rows]


def get_all_side_groups(main_group_erp=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if main_group_erp:
        c.execute('SELECT erp_code, name FROM side_groups WHERE main_group_erp = ? ORDER BY name', (main_group_erp,))
    else:
        c.execute('SELECT erp_code, name FROM side_groups ORDER BY name')
    rows = c.fetchall()
    conn.close()
    return [{"ErpCode": r[0], "Name": r[1]} for r in rows]


def get_all_units():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT erp_code, name FROM units ORDER BY name')
    rows = c.fetchall()
    conn.close()
    return [{"ErpCode": r[0], "Name": r[1]} for r in rows]




def get_erp_by_barcode(barcode):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT erp_code FROM barcodes WHERE barcode = ?', (str(barcode),))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


# ... (سایر توابع save_product_batch, get_erp_by_barcode و ...) ...

def save_product_batch(products):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    for prod in products:
        erp_code = prod.get('ErpCode')
        if not erp_code:
            continue
        
        # ✅ اطمینان از وجود FewTak در داده
        if 'FewTak' not in prod:
            prod['FewTak'] = prod.get('fewtak', 0)
        
        full_json = json.dumps(prod, ensure_ascii=False)
        
        c.execute(
            '''INSERT OR REPLACE INTO products 
               (erp_code, name, code, buy_price, sell_price, full_data) 
               VALUES (?, ?, ?, ?, ?, ?)''',
            (erp_code, 
             prod.get('Name'), 
             prod.get('Code'), 
             prod.get('BuyPrice'), 
             prod.get('SellPrice'), 
             full_json)
        )

        more_codes = prod.get('morecodes', [])
        if more_codes:
            for bc in more_codes:
                if bc:
                    c.execute('INSERT OR IGNORE INTO barcodes (barcode, erp_code) VALUES (?, ?)',
                             (str(bc), erp_code))

        poshak_list = prod.get('Poshak', [])
        if poshak_list:
            for p in poshak_list:
                c.execute('''INSERT OR IGNORE INTO product_poshak 
                             (erp_code, poshak_id, parent_id, name, few, min_price, max_price) 
                             VALUES (?, ?, ?, ?, ?, ?, ?)''',
                          (erp_code, 
                           p.get('Id'), 
                           p.get('ParentID'), 
                           p.get('NameTree') or p.get('Name'), 
                           p.get('Few'),
                           p.get('Min'), 
                           p.get('Max')))
    
    conn.commit()
    conn.close()

def get_erp_by_code_or_barcode(identifier):
    """جستجوی شناسه هم در فیلد کد کالا (Code) و هم در جدول بارکدهای اضافی (morecodes)"""
    if not identifier:
        return None
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        # 1. اول در جدول بارکدهای اضافی (morecodes) جستجو می‌کنیم
        c.execute('SELECT erp_code FROM barcodes WHERE barcode = ?', (str(identifier),))
        result = c.fetchone()
        if result:
            return result[0]
        
        # 2. اگر نبود، در فیلد کد اصلی کالا (Code) جستجو می‌کنیم
        c.execute('SELECT erp_code FROM products WHERE code = ?', (str(identifier),))
        result = c.fetchone()
        if result:
            return result[0]
        
        return None
    except Exception as e:
        print(f"Error in get_erp_by_code_or_barcode: {e}")
        return None
    finally:
        conn.close()



def get_product_code_and_name_by_erp(erp_code):
    """دریافت کد و نام کالا بر اساس ErpCode"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT code, name FROM products WHERE erp_code = ?', (erp_code,))
        result = c.fetchone()
        if result:
            return result[0], result[1]
        return None, None
    except Exception as e:
        print(f"Error in get_product_code_and_name_by_erp: {e}")
        return None, None
    finally:
        conn.close()
        

import unicodedata


# db_manager.py - اضافه کردن تابع نرمال‌سازی و جستجوی مشتریان

import unicodedata

def normalize_persian_text(text):
    """نرمال‌سازی متن فارسی برای جستجو"""
    if not text:
        return text
    
    text = str(text)
    
    # ✅ نرمال‌سازی ی و ک (فارسی و عربی)
    text = text.replace('\u064a', '\u06cc')  # ي عربی -> ی فارسی
    text = text.replace('\u0643', '\u06a9')  # ك عربی -> ک فارسی
    text = text.replace('ي', '\u06cc')       # ي -> ی
    text = text.replace('ك', '\u06a9')       # ك -> ک
    
    # ✅ حذف فاصله‌های اضافی
    text = ' '.join(text.split())
    
    return text.strip()

def normalize_search_query(query):
    """نرمال‌سازی عبارت جستجو"""
    if not query:
        return ""
    
    query = str(query).strip()
    
    # ✅ نرمال‌سازی ی و ک
    query = query.replace('\u064a', '\u06cc')
    query = query.replace('\u0643', '\u06a9')
    query = query.replace('ي', '\u06cc')
    query = query.replace('ك', '\u06a9')
    
    # ✅ حذف فاصله‌های اضافی
    query = ' '.join(query.split())
    
    return query

def search_products_advanced(query=None, barcode=None, page=1, per_page=50):
    """جستجوی پیشرفته کالاها"""
    offset = (page - 1) * per_page
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    conditions = []
    params = []
    
    # جستجوی بارکد
    if barcode:
        normalized_bc = normalize_text(str(barcode))
        conditions.append("(p.code = ? OR p.code LIKE ?)")
        params.extend([normalized_bc, f"%{normalized_bc}%"])
    
    # جستجوی نام (کلمه به کلمه، ترتیب مهم نیست)
    if query:
        normalized_query = normalize_text(query)
        words = normalized_query.split()
        if words:
            word_conditions, word_params = build_search_conditions(
                words, 
                search_fields=['p.name', 'p.code']
            )
            if word_conditions:
                conditions.append("(" + word_conditions + ")")
                params.extend(word_params)
    
    sql_filter = " AND ".join(conditions) if conditions else "1=1"
    
    # شمارش کل نتایج
    count_sql = f'''
        SELECT COUNT(DISTINCT p.erp_code) 
        FROM products p
        WHERE {sql_filter}
    '''
    c.execute(count_sql, params)
    total_count = c.fetchone()[0]
    
    # دریافت محصولات
    final_sql = f'''
        SELECT DISTINCT p.erp_code, p.name, p.code, p.buy_price, p.sell_price, p.full_data 
        FROM products p
        WHERE {sql_filter}
        ORDER BY p.name
        LIMIT ? OFFSET ?
    '''
    params.extend([per_page, offset])
    
    c.execute(final_sql, params)
    rows = c.fetchall()
    conn.close()
    
    products = []
    for row in rows:
        prod_data = json.loads(row[5]) if row[5] else {}
        products.append({
            "ErpCode": row[0],
            "Name": row[1],
            "Code": row[2],
            "BuyPrice": row[3],
            "SellPrice": row[4],
            "FullData": prod_data
        })
    
    return products, total_count



def search_customers_advanced(query=None, limit=20, is_seller=None, is_purchaser=None):
    """
    جستجوی پیشرفته مشتریان/تامین‌کنندگان
    - is_seller: 1 = فقط فروشندگان, 0 = فقط خریداران, None = همه
    """
    if not query or len(query.strip()) < 1:
        return []
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # اطمینان از وجود ستون‌ها
    c.execute("PRAGMA table_info(customers)")
    columns = [col[1] for col in c.fetchall()]
    if 'is_seller' not in columns:
        c.execute('ALTER TABLE customers ADD COLUMN is_seller INTEGER DEFAULT 0')
    if 'is_purchaser' not in columns:
        c.execute('ALTER TABLE customers ADD COLUMN is_purchaser INTEGER DEFAULT 0')
    conn.commit()
    
    normalized_query = normalize_text(query)
    words = normalized_query.split()
    
    if not words:
        conn.close()
        return []
    
    # شرط‌های جستجو
    conditions = ["1=1"]
    params = []
    
    # فیلتر فروشنده/خریدار
    if is_seller is not None:
        conditions.append("is_seller = ?")
        params.append(is_seller)
    if is_purchaser is not None:
        conditions.append("is_purchaser = ?")
        params.append(is_purchaser)
    
    # جستجوی کلمات
    word_conditions, word_params = build_search_conditions(
        words,
        search_fields=['name', 'code']
    )
    if word_conditions:
        conditions.append("(" + word_conditions + ")")
        params.extend(word_params)
    
    sql = f'''
        SELECT erp_code, code, name FROM customers 
        WHERE {' AND '.join(conditions)}
        ORDER BY name
        LIMIT ?
    '''
    params.append(limit)
    
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    
    return [{"ErpCode": r[0], "Code": r[1] or '', "Name": r[2] or ''} for r in rows]


# db_manager.py - تابع جستجوی یکسان برای همه بخش‌ها

def search_products_unified(query=None, barcode=None, page=1, per_page=50, include_price=False):
    """
    تابع جستجوی یکسان برای همه بخش‌ها
    - قابل استفاده در POS، فاکتور خرید، تولید و ...
    - پشتیبانی از جستجوی کلمه به کلمه با ترتیب دلخواه
    - نرمال‌سازی ی و ک
    """
    offset = (page - 1) * per_page
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    conditions = []
    params = []
    
    # جستجوی بارکد
    if barcode:
        normalized_bc = normalize_text(str(barcode))
        conditions.append("(p.code = ? OR p.code LIKE ?)")
        params.extend([normalized_bc, f"%{normalized_bc}%"])
    
    # جستجوی نام (کلمه به کلمه، ترتیب مهم نیست)
    if query:
        normalized_query = normalize_text(query)
        words = normalized_query.split()
        if words:
            word_conditions, word_params = build_search_conditions(
                words, 
                search_fields=['p.name', 'p.code']
            )
            if word_conditions:
                conditions.append("(" + word_conditions + ")")
                params.extend(word_params)
    
    sql_filter = " AND ".join(conditions) if conditions else "1=1"
    
    # شمارش کل نتایج
    count_sql = f'''
        SELECT COUNT(DISTINCT p.erp_code) 
        FROM products p
        WHERE {sql_filter}
    '''
    c.execute(count_sql, params)
    total_count = c.fetchone()[0]
    
    # دریافت محصولات
    final_sql = f'''
        SELECT DISTINCT p.erp_code, p.name, p.code, p.buy_price, p.sell_price, p.full_data 
        FROM products p
        WHERE {sql_filter}
        ORDER BY p.name
        LIMIT ? OFFSET ?
    '''
    params.extend([per_page, offset])
    
    c.execute(final_sql, params)
    rows = c.fetchall()
    conn.close()
    
    products = []
    for row in rows:
        prod_data = json.loads(row[5]) if row[5] else {}
        
        # استخراج قیمت‌ها
        buy_price = prod_data.get('BuyPrice') or prod_data.get('buyprice') or row[3] or 0
        sell_price = prod_data.get('SellPrice') or prod_data.get('sellprice') or row[4] or 0
        few = prod_data.get('Few') or prod_data.get('few') or 0
        few_tak = prod_data.get('FewTak') or prod_data.get('fewtak') or 0
        
        product = {
            "ErpCode": row[0],
            "Name": row[1],
            "Code": row[2],
            "BuyPrice": float(buy_price),
            "SellPrice": float(sell_price),
            "Few": float(few),
            "FewTak": float(few_tak),
            "FullData": prod_data
        }
        
        # اضافه کردن قیمت‌های اضافی در صورت نیاز
        if include_price:
            product["DiscountPrice"] = float(prod_data.get('DiscountPrice') or prod_data.get('discountprice') or 0)
            product["DiscountPercent"] = float(prod_data.get('DiscountPercent') or prod_data.get('discountpercent') or 0)
            product["morecodes"] = prod_data.get('morecodes') or prod_data.get('Morecodes') or []
        
        products.append(product)
    
    return products, total_count



def search_suppliers_advanced(query=None, limit=20):
    """
    جستجوی پیشرفته تامین‌کنندگان با قابلیت‌های:
    1. ترتیب کلمات مهم نیست
    2. جستجوی کلمه به کلمه
    3. نرمال‌سازی ی و ک فارسی/عربی
    """
    if not query or len(query.strip()) < 1:
        return []
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # اطمینان از وجود ستون is_seller
    c.execute("PRAGMA table_info(customers)")
    columns = [col[1] for col in c.fetchall()]
    if 'is_seller' not in columns:
        c.execute('ALTER TABLE customers ADD COLUMN is_seller INTEGER DEFAULT 0')
        conn.commit()
    
    normalized_query = normalize_search_query(query)
    words = normalized_query.split()
    
    if not words:
        conn.close()
        return []
    
    conditions = []
    params = []
    
    for word in words:
        normalized_word = normalize_search_query(word)
        conditions.append("""
            (REPLACE(REPLACE(name, '\u064a', '\u06cc'), '\u0643', '\u06a9') LIKE ? 
             OR REPLACE(REPLACE(code, '\u064a', '\u06cc'), '\u0643', '\u06a9') LIKE ?)
        """)
        params.extend([f"%{normalized_word}%", f"%{normalized_word}%"])
    
    sql = f'''
        SELECT erp_code, code, name FROM customers 
        WHERE is_seller = 1 AND {' AND '.join(conditions)}
        ORDER BY 
            CASE 
                WHEN REPLACE(REPLACE(name, '\u064a', '\u06cc'), '\u0643', '\u06a9') = ? THEN 0
                WHEN REPLACE(REPLACE(name, '\u064a', '\u06cc'), '\u0643', '\u06a9') LIKE ? THEN 1
                ELSE 2
            END,
            name
        LIMIT ?
    '''
    
    params.insert(0, normalized_query)
    params.insert(1, f"{normalized_query}%")
    params.append(limit)
    
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    
    return [{"ErpCode": r[0], "Code": r[1] or '', "Name": r[2] or ''} for r in rows]

def normalize_text(text):
    """
    نرمال‌سازی متن برای جستجو:
    - تبدیل ی عربی به ی فارسی
    - تبدیل ک عربی به ک فارسی
    - حذف فاصله‌های اضافی
    """
    if not text:
        return ""
    
    text = str(text)
    
    # نرمال‌سازی ی و ک
    text = text.replace('\u064a', '\u06cc')  # ي عربی -> ی فارسی
    text = text.replace('\u0643', '\u06a9')  # ك عربی -> ک فارسی
    text = text.replace('ي', '\u06cc')       # ي -> ی
    text = text.replace('ك', '\u06a9')       # ك -> ک
    
    # حذف فاصله‌های اضافی
    text = ' '.join(text.split())
    
    return text.strip()


def build_search_conditions(words, search_fields=['name', 'code']):
    """
    ساخت شرط‌های جستجو برای کلمات
    - ترتیب کلمات مهم نیست
    - جستجوی کلمه به کلمه
    - نرمال‌سازی ی و ک
    """
    if not words:
        return "", []
    
    conditions = []
    params = []
    
    for word in words:
        normalized_word = normalize_text(word)
        if not normalized_word:
            continue
        
        field_conditions = []
        for field in search_fields:
            # نرمال‌سازی فیلد در کوئری
            field_conditions.append(f"""
                REPLACE(REPLACE({field}, '\u064a', '\u06cc'), '\u0643', '\u06a9') 
                LIKE ?
            """)
            params.append(f"%{normalized_word}%")
        
        conditions.append("(" + " OR ".join(field_conditions) + ")")
    
    return " AND ".join(conditions), params







def search_customers(query=None, limit=20):
    """جستجوی مشتریان با کلمه به کلمه و نرمال‌سازی"""
    if not query or len(query.strip()) < 1:
        return []
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # نرمال‌سازی عبارت جستجو
    normalized_query = normalize_persian_text(query)
    words = normalized_query.split()
    
    if not words:
        conn.close()
        return []
    
    # ساخت شرط جستجو برای هر کلمه
    conditions = []
    params = []
    
    for word in words:
        # نرمال‌سازی هر کلمه
        normalized_word = normalize_persian_text(word)
        # جستجو در نام و کد مشتری
        conditions.append("(REPLACE(REPLACE(name, '\u064a', '\u06cc'), '\u0643', '\u06a9') LIKE ? OR REPLACE(REPLACE(code, '\u064a', '\u06cc'), '\u0643', '\u06a9') LIKE ?)")
        params.extend([f"%{normalized_word}%", f"%{normalized_word}%"])
    
    sql = f"""
        SELECT erp_code, code, name FROM customers 
        WHERE {' AND '.join(conditions)}
        ORDER BY 
            CASE 
                WHEN REPLACE(REPLACE(name, '\u064a', '\u06cc'), '\u0643', '\u06a9') = ? THEN 0
                WHEN REPLACE(REPLACE(name, '\u064a', '\u06cc'), '\u0643', '\u06a9') LIKE ? THEN 1
                ELSE 2
            END,
            name
        LIMIT ?
    """
    
    # اضافه کردن پارامترهای مرتب‌سازی
    params.insert(0, normalized_query)  # تطابق دقیق
    params.insert(1, f"{normalized_query}%")  # شروع با عبارت
    params.append(limit)
    
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    
    return [{"ErpCode": r[0], "Code": r[1], "Name": r[2]} for r in rows]


def search_products(query=None, barcode=None, page=1, per_page=50):
    offset = (page - 1) * per_page
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    conditions = []
    params = []

    # اگر هیچ فیلتری نبود، لیست کامل را برگردان
    if not query and not barcode:
        c.execute('SELECT COUNT(*) FROM products')
        total_count = c.fetchone()[0]
        c.execute('SELECT erp_code, name, code, buy_price, sell_price, full_data FROM products LIMIT ? OFFSET ?',
                  (per_page, offset))
        rows = c.fetchall()
        conn.close()
        products = []
        for row in rows:
            prod_data = json.loads(row[5]) if row[5] else {}
            products.append({
                "ErpCode": row[0], "Name": row[1], "Code": row[2],
                "BuyPrice": row[3], "SellPrice": row[4], "FullData": prod_data
            })
        return products, total_count

    # 1. شرط جستجوی بارکد (دقیقاً روی فیلد Code)
    if barcode:
        normalized_bc = normalize_persian_text(str(barcode))
        # استفاده از REPLACE در SQL برای تطبیق حتی اگر داده قدیمی عربی باشد
        conditions.append("REPLACE(REPLACE(p.code, '\u064a', '\u06cc'), '\u0643', '\u06a9') = ?")
        params.append(normalized_bc)

    # 2. شرط جستجوی نام کالا (کلمه به کلمه، بدون ترتیب)
    if query:
        words = query.strip().split()
        word_conditions = []
        for word in words:
            normalized_word = normalize_persian_text(word)
            word_conditions.append("REPLACE(REPLACE(p.name, '\u064a', '\u06cc'), '\u0643', '\u06a9') LIKE ?")
            params.append(f"%{normalized_word}%")

        if word_conditions:
            conditions.append("(" + " AND ".join(word_conditions) + ")")

    sql_filter = " AND ".join(conditions) if conditions else "1=1"

    # شمارش کل نتایج
    count_sql = f'''
        SELECT COUNT(DISTINCT p.erp_code) FROM products p
        LEFT JOIN barcodes b ON p.erp_code = b.erp_code
        WHERE {sql_filter}
    '''
    c.execute(count_sql, params)
    total_count = c.fetchone()[0]

    # دریافت محصولات
    final_sql = f'''
        SELECT DISTINCT p.erp_code, p.name, p.code, p.buy_price, p.sell_price, p.full_data 
        FROM products p
        LEFT JOIN barcodes b ON p.erp_code = b.erp_code
        WHERE {sql_filter}
        LIMIT ? OFFSET ?
    '''
    params.extend([per_page, offset])

    c.execute(final_sql, params)
    rows = c.fetchall()
    conn.close()

    products = []
    for row in rows:
        prod_data = json.loads(row[5]) if row[5] else {}
        products.append({
            "ErpCode": row[0], "Name": row[1], "Code": row[2],
            "BuyPrice": row[3], "SellPrice": row[4], "FullData": prod_data
        })
    return products, total_count





def get_products_list(page=1, per_page=50):
    return search_products("", page, per_page)


def get_products_count():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM products')
    count = c.fetchone()[0]
    conn.close()
    return count


def update_product_in_db(erp_code, update_fields):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT full_data FROM products WHERE erp_code = ?', (erp_code,))
    row = c.fetchone()
    if row and row[0]:
        current_data = json.loads(row[0])
        for key, value in update_fields.items():
            if key in current_data:
                current_data[key] = value
        new_json = json.dumps(current_data, ensure_ascii=False)
        c.execute('''UPDATE products
                     SET name       = ?,
                         code       = ?,
                         buy_price  = ?,
                         sell_price = ?,
                         full_data  = ?
                     WHERE erp_code = ?''',
                  (current_data.get('Name'), current_data.get('Code'), current_data.get('BuyPrice'),
                   current_data.get('SellPrice'), new_json, erp_code))
        conn.commit()
    conn.close()


def get_product_full_info(erp_code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT full_data FROM products WHERE erp_code = ?', (erp_code,))
    row = c.fetchone()
    product = {}
    if row and row[0]:
        product = json.loads(row[0])

        # جایگزینی نام‌ها به جای ErpCode
        product['MainGroupName_Display'] = get_name_by_erp('main_groups', product.get('MainGroupErpCode'))
        product['SideGroupName_Display'] = get_name_by_erp('side_groups', product.get('SideGroupErpCode'))
        product['UnitName_Display'] = get_name_by_erp('units', product.get('UnitErpCode'))

        c.execute('SELECT * FROM product_poshak WHERE erp_code = ?', (erp_code,))
        poshak_rows = c.fetchall()
        product['PoshakDetails'] = [{"Id": r[2], "ParentID": r[3], "Name": r[4], "Few": r[5], "Min": r[6], "Max": r[7]}
                                    for r in poshak_rows]
    conn.close()
    return product


def get_all_columns():
    return [
        "ErpCode", "SideGroupErpCode", "Code", "Name", "Few", "FewKarton",
        "BuyPrice", "SellPrice", "SellPrice2", "SellPrice3", "SellPrice4",
        "SellPrice5", "SellPrice6", "SellPrice7", "SellPrice8", "SellPrice9", "SellPrice10",
        "CountInKarton", "CountInBasteh",
        "Other1", "Other2", "Other3", "Other4", "Other5", "Other6", "Other7", "Other8", "Other9", "Other10",
        "A_Country", "Place", "Model", "Service", "UnitErpCode",
        "DiscountPrice", "DiscountPercent", "MinFew", "MaxFew"
    ]





# db_manager.py (اضافه شده به انتهای فایل)

# ==================== جداول جدید برای فاکتور تک فروشی ====================

# جدول اشخاص (مشتریان)
# db_manager.py - به‌روزرسانی تابع init_customer_table

def init_customer_table():
    """ایجاد جدول مشتریان در دیتابیس با فیلدهای کامل"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # ابتدا بررسی می‌کنیم که جدول وجود دارد یا نه
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
    table_exists = c.fetchone()
    
    if table_exists:
        # بررسی وجود ستون‌های جدید
        c.execute("PRAGMA table_info(customers)")
        columns = [col[1] for col in c.fetchall()]
        
        # اگر ستون is_seller وجود ندارد، اضافه کن
        if 'is_seller' not in columns:
            c.execute('ALTER TABLE customers ADD COLUMN is_seller INTEGER DEFAULT 0')
            print("✅ Added is_seller column to customers table")
        
        if 'is_purchaser' not in columns:
            c.execute('ALTER TABLE customers ADD COLUMN is_purchaser INTEGER DEFAULT 0')
            print("✅ Added is_purchaser column to customers table")
    else:
        # ایجاد جدول جدید
        c.execute('''CREATE TABLE IF NOT EXISTS customers
                     (erp_code TEXT PRIMARY KEY,
                      code TEXT,
                      name TEXT,
                      is_purchaser INTEGER DEFAULT 0,
                      is_seller INTEGER DEFAULT 0,
                      full_data TEXT)''')
        print("✅ Created customers table with all columns")
    
    conn.commit()
    conn.close()
    
# db_manager.py - به‌روزرسانی تابع save_customers
# جدول حساب‌های بانکی
def init_bank_accounts_table():
    """ایجاد جدول حساب‌های بانکی در دیتابیس"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bank_accounts
                 (account_number TEXT PRIMARY KEY,
                  bank_code TEXT,
                  bank_name TEXT,
                  account_owner TEXT,
                  sheba TEXT,
                  card_number TEXT,
                  sarfasl_code TEXT,
                  has_pos INTEGER,
                  is_current INTEGER,
                  full_data TEXT)''')
    conn.commit()
    conn.close()



# db_manager.py - اصلاح کامل تابع save_customers

def save_customers(customers):
    """ذخیره لیست مشتریان در دیتابیس با فیلدهای is_purchaser و is_seller"""
    if not customers:
        print("⚠️ No customers to save")
        return 0
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('PRAGMA synchronous = OFF')
        conn.execute('PRAGMA journal_mode = WAL')
        c = conn.cursor()
        
        # اطمینان از وجود ستون‌های مورد نیاز
        c.execute("PRAGMA table_info(customers)")
        columns = [col[1] for col in c.fetchall()]
        
        if 'is_seller' not in columns:
            c.execute('ALTER TABLE customers ADD COLUMN is_seller INTEGER DEFAULT 0')
        if 'is_purchaser' not in columns:
            c.execute('ALTER TABLE customers ADD COLUMN is_purchaser INTEGER DEFAULT 0')
        
        data_to_insert = []
        for cust in customers:
            erp_code = cust.get('ErpCode')
            if not erp_code:
                continue
            
            code = str(cust.get('Code', erp_code[:8])).strip()
            if not code or code == 'None':
                code = erp_code[:8]
                
            name = str(cust.get('Name', f"مشتری {code}")).strip()
            if not name or name == 'None':
                name = f"مشتری {code}"
            
            is_purchaser = 1 if cust.get('IsPurchaser') else 0
            is_seller = 1 if cust.get('IsSeller') else 0
            
            full_data = json.dumps(cust, ensure_ascii=False)
            
            data_to_insert.append((erp_code, code, name, is_purchaser, is_seller, full_data))
        
        if data_to_insert:
            c.executemany('''INSERT OR REPLACE INTO customers 
                             (erp_code, code, name, is_purchaser, is_seller, full_data) 
                             VALUES (?, ?, ?, ?, ?, ?)''', data_to_insert)
            conn.commit()
            print(f"✅ Saved {len(data_to_insert)} customers to database")
            return len(data_to_insert)
        
        return 0
        
    except Exception as e:
        print(f"❌ Error saving customers: {e}")
        if conn:
            conn.rollback()
        import traceback
        traceback.print_exc()
        return 0
    finally:
        if conn:
            conn.close()
# db_manager.py - اضافه کردن به انتهای فایل




# db_manager.py - اصلاح تابع search_suppliers

def search_suppliers(query=None, limit=20):
    """جستجوی تامین‌کنندگان (فروشندگان) با کلمه به کلمه و نرمال‌سازی"""
    if not query or len(query.strip()) < 1:
        return []
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # اطمینان از وجود ستون is_seller
    c.execute("PRAGMA table_info(customers)")
    columns = [col[1] for col in c.fetchall()]
    if 'is_seller' not in columns:
        c.execute('ALTER TABLE customers ADD COLUMN is_seller INTEGER DEFAULT 0')
        conn.commit()
    
    normalized_query = normalize_persian_text(query)
    words = normalized_query.split()
    
    if not words:
        conn.close()
        return []
    
    conditions = []
    params = []
    
    for word in words:
        normalized_word = normalize_persian_text(word)
        conditions.append("(REPLACE(REPLACE(name, '\u064a', '\u06cc'), '\u0643', '\u06a9') LIKE ? OR REPLACE(REPLACE(code, '\u064a', '\u06cc'), '\u0643', '\u06a9') LIKE ?)")
        params.extend([f"%{normalized_word}%", f"%{normalized_word}%"])
    
    sql = f"""
        SELECT erp_code, code, name FROM customers 
        WHERE is_seller = 1 AND {' AND '.join(conditions)}
        ORDER BY name
        LIMIT ?
    """
    params.append(limit)
    
    try:
        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            result.append({
                "ErpCode": row[0],
                "Code": row[1] or '',
                "Name": row[2] or ''
            })
        
        return result
    except Exception as e:
        print(f"❌ Error searching suppliers: {e}")
        conn.close()
        return []
    

# ==================== جداول سرفصل هزینه و درآمد ====================

# db_manager.py - اضافه کردن به انتهای فایل

# ==================== جداول سرفصل هزینه و درآمد ====================

def init_cost_income_tables():
    """ایجاد جداول سرفصل هزینه و درآمد"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # جدول سرفصل‌های هزینه
    c.execute('''CREATE TABLE IF NOT EXISTS cost_headers
                 (code TEXT PRIMARY KEY,
                  name TEXT,
                  full_data TEXT)''')
    
    # جدول سرفصل‌های درآمد
    c.execute('''CREATE TABLE IF NOT EXISTS income_headers
                 (code TEXT PRIMARY KEY,
                  name TEXT,
                  full_data TEXT)''')
    
    conn.commit()
    conn.close()
    print("✅ Cost and Income tables initialized")


def save_cost_headers(costs):
    """ذخیره لیست سرفصل‌های هزینه در دیتابیس"""
    if not costs:
        print("⚠️ No cost headers to save")
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    saved_count = 0
    for cost in costs:
        # پشتیبانی از دو فرمت مختلف
        code = cost.get('Code') or cost.get('code')
        name = cost.get('Name') or cost.get('name')
        
        if not code:
            print(f"⚠️ Skipping cost header without code: {cost}")
            continue
        
        if not name:
            name = f"سرفصل {code}"
        
        full_data = json.dumps(cost, ensure_ascii=False)
        
        try:
            c.execute('''INSERT OR REPLACE INTO cost_headers (code, name, full_data) 
                         VALUES (?, ?, ?)''', (code, name, full_data))
            saved_count += 1
        except Exception as e:
            print(f"❌ Error saving cost header {code}: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ {saved_count} cost headers saved")
    return saved_count


def save_income_headers(incomes):
    """ذخیره لیست سرفصل‌های درآمد در دیتابیس"""
    if not incomes:
        print("⚠️ No income headers to save")
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    saved_count = 0
    for income in incomes:
        code = income.get('Code') or income.get('code')
        name = income.get('Name') or income.get('name')
        
        if not code:
            print(f"⚠️ Skipping income header without code: {income}")
            continue
        
        if not name:
            name = f"سرفصل {code}"
        
        full_data = json.dumps(income, ensure_ascii=False)
        
        try:
            c.execute('''INSERT OR REPLACE INTO income_headers (code, name, full_data) 
                         VALUES (?, ?, ?)''', (code, name, full_data))
            saved_count += 1
        except Exception as e:
            print(f"❌ Error saving income header {code}: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ {saved_count} income headers saved")
    return saved_count


def get_cost_headers():
    """دریافت لیست سرفصل‌های هزینه از دیتابیس"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT code, name FROM cost_headers ORDER BY name')
        rows = c.fetchall()
        conn.close()
        return [{"Code": r[0], "Name": r[1]} for r in rows]
    except Exception as e:
        print(f"❌ Error getting cost headers: {e}")
        conn.close()
        return []


def get_income_headers():
    """دریافت لیست سرفصل‌های درآمد از دیتابیس"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT code, name FROM income_headers ORDER BY name')
        rows = c.fetchall()
        conn.close()
        return [{"Code": r[0], "Name": r[1]} for r in rows]
    except Exception as e:
        print(f"❌ Error getting income headers: {e}")
        conn.close()
        return []
    


# db_manager.py - به‌روزرسانی تابع init_all_tables

def init_all_tables():
    """مقداردهی اولیه همه جداول دیتابیس"""
    init_db()
    init_customer_table()
    init_bank_accounts_table()
    init_cost_income_tables()
    init_cash_table()
    init_allocation_formulas_table()  # <-- این خط حتما باید باشد
    print("✅ All tables initialized")

# db_manager.py - اضافه کردن تابع‌های مربوط به صندوق

def init_cash_table():
    """ایجاد جدول سرفصل‌های صندوق"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cash_headers
                 (code TEXT PRIMARY KEY,
                  name TEXT,
                  full_data TEXT)''')
    conn.commit()
    conn.close()
    print("✅ Cash headers table initialized")


def save_cash_headers(cash_items):
    """ذخیره لیست سرفصل‌های صندوق در دیتابیس"""
    if not cash_items:
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    saved_count = 0
    for item in cash_items:
        code = item.get('Code') or item.get('code')
        name = item.get('Name') or item.get('name')
        
        if not code:
            continue
        
        full_data = json.dumps(item, ensure_ascii=False)
        c.execute('''INSERT OR REPLACE INTO cash_headers (code, name, full_data) 
                     VALUES (?, ?, ?)''', (code, name, full_data))
        saved_count += 1
    
    conn.commit()
    conn.close()
    return saved_count


def get_cash_headers():
    """دریافت لیست سرفصل‌های صندوق از دیتابیس"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT code, name FROM cash_headers ORDER BY name')
        rows = c.fetchall()
        conn.close()
        return [{"Code": r[0], "Name": r[1]} for r in rows]
    except Exception as e:
        print(f"❌ Error getting cash headers: {e}")
        conn.close()
        return []



def get_all_customers():
    """دریافت لیست همه مشتریان برای نمایش در dropdown"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT erp_code, code, name FROM customers ORDER BY name')
    rows = c.fetchall()
    conn.close()
    return [{"ErpCode": r[0], "Code": r[1], "Name": r[2]} for r in rows]



# دریافت اطلاعات یک شخص با ErpCode
def get_customer_by_erp(erp_code):
    """دریافت اطلاعات کامل یک مشتری با ErpCode"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT full_data FROM customers WHERE erp_code = ?', (erp_code,))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return None

# ذخیره لیست حساب‌های بانکی
def save_bank_accounts(accounts):
    """ذخیره لیست حساب‌های بانکی در دیتابیس"""
    if not accounts:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for acc in accounts:
        account_number = acc.get('accountNumber')
        if not account_number:
            continue
        c.execute('''INSERT OR REPLACE INTO bank_accounts 
                     (account_number, bank_code, bank_name, account_owner, sheba, 
                      card_number, sarfasl_code, has_pos, is_current, full_data)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (account_number,
                   acc.get('bankCode'),
                   acc.get('bankName'),
                   acc.get('accOwnerName'),
                   acc.get('sheba'),
                   acc.get('cardNumber'),
                   acc.get('sarfaslCode'),
                   1 if acc.get('hasPOS') else 0,
                   1 if acc.get('isCurrent') else 0,
                   json.dumps(acc, ensure_ascii=False)))
    conn.commit()
    conn.close()





# دریافت حساب‌های بانکی (با فیلتر POS)
def get_bank_accounts(has_pos=None):
    """دریافت لیست حساب‌های بانکی با فیلتر اختیاری"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if has_pos is not None:
        c.execute('''SELECT account_number, bank_name, account_owner, sarfasl_code 
                     FROM bank_accounts WHERE has_pos = ?''', (1 if has_pos else 0,))
    else:
        c.execute('SELECT account_number, bank_name, account_owner, sarfasl_code FROM bank_accounts')
    rows = c.fetchall()
    conn.close()
    return [{"accountNumber": r[0], "bankName": r[1], "accountOwner": r[2], "sarfaslCode": r[3]} for r in rows]

def get_bank_account_by_number(account_number):
    """دریافت اطلاعات کامل یک حساب بانکی با شماره حساب"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT full_data FROM bank_accounts WHERE account_number = ?', (account_number,))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return None

# db_manager.py - اضافه کردن به انتهای فایل

import unicodedata

def normalize_persian_text(text):
    """نرمال‌سازی ی و ک عربی به فارسی"""
    if not text:
        return text
    text = text.replace('\u064a', '\u06cc')  # ي -> ی
    text = text.replace('\u0643', '\u06a9')  # ك -> ک
    return text.strip()

def search_customers(query=None, limit=20):
    """جستجوی مشتریان با کلمه به کلمه و نرمال‌سازی"""
    if not query or len(query.strip()) < 1:
        return []
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    normalized_query = normalize_persian_text(query)
    words = normalized_query.split()
    
    if not words:
        conn.close()
        return []
    
    conditions = []
    params = []
    
    for word in words:
        normalized_word = normalize_persian_text(word)
        conditions.append("(REPLACE(REPLACE(name, '\u064a', '\u06cc'), '\u0643', '\u06a9') LIKE ? OR REPLACE(REPLACE(code, '\u064a', '\u06cc'), '\u0643', '\u06a9') LIKE ?)")
        params.extend([f"%{normalized_word}%", f"%{normalized_word}%"])
    
    sql = f"""
        SELECT erp_code, code, name FROM customers 
        WHERE {' AND '.join(conditions)}
        ORDER BY name
        LIMIT ?
    """
    params.append(limit)
    
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    
    return [{"ErpCode": r[0], "Code": r[1], "Name": r[2]} for r in rows]

