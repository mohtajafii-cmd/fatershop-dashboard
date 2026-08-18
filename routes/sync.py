# routes/sync.py
import threading
import time
import requests
from flask import Blueprint, jsonify, request
from db_manager import (
    clear_db, save_product_batch, save_main_groups, save_side_groups, 
    save_units, save_customers, save_bank_accounts, get_all_customers,
    save_cost_headers, save_income_headers, save_cash_headers
)

sync_bp = Blueprint('sync', __name__)

# ==================== متغیرهای وضعیت سینک ====================
sync_status_parts = {
    "products": {"is_syncing": False, "total": 0, "processed": 0, "message": "", "current_stage": ""},
    "customers": {"is_syncing": False, "total": 0, "processed": 0, "message": "", "current_stage": ""},
    "banks": {"is_syncing": False, "total": 0, "processed": 0, "message": "", "current_stage": ""},
    "units": {"is_syncing": False, "total": 0, "processed": 0, "message": "", "current_stage": ""},
    "groups": {"is_syncing": False, "total": 0, "processed": 0, "message": "", "current_stage": ""},
    "suppliers": {"is_syncing": False, "total": 0, "processed": 0, "message": "", "current_stage": ""},
    "costs": {"is_syncing": False, "total": 0, "processed": 0, "message": "", "current_stage": ""},
    "incomes": {"is_syncing": False, "total": 0, "processed": 0, "message": "", "current_stage": ""},
    "cash": {"is_syncing": False, "total": 0, "processed": 0, "message": "", "current_stage": ""}
}

# وضعیت سینک پایه (قدیمی - برای سازگاری)
base_sync_status = {
    "is_syncing": False, "total": 0, "processed": 0, 
    "message": "", "current_stage": ""
}

# وضعیت سینک مشتریان پیشرفته
customer_sync_status = {
    "is_syncing": False, "total": 0, "processed": 0, "message": "",
    "stage": "idle", "progress_percent": 0
}

# وضعیت سینک فاکتور خرید
purchase_sync_status = {
    "is_syncing": False, "total": 0, "processed": 0, "message": "",
    "stage": "idle", "progress_percent": 0,
    "details": {
        "products": {"total": 0, "processed": 0},
        "suppliers": {"total": 0, "processed": 0},
        "banks": {"total": 0, "processed": 0},
        "costs": {"total": 0, "processed": 0},
        "incomes": {"total": 0, "processed": 0},
        "units": {"total": 0, "processed": 0}
    }
}

# ==================== توابع کمکی داخلی ====================
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
        print(f"❌ API Init Error in sync module: {e}")
        return None

def _run_in_thread(target_func):
    """اجرای تابع در ترد جداگانه"""
    thread = threading.Thread(target=target_func)
    thread.daemon = True
    thread.start()

# ==================== مسیرهای سینک جداگانه ====================

@sync_bp.route('/sync/products', methods=['POST'])
def sync_products():
    """سینک کالاها"""
    if sync_status_parts["products"]["is_syncing"]:
        return jsonify({"status": "error", "message": "سینک کالاها در حال انجام است"})

    def run_sync():
        try:
            sync_status_parts["products"].update({
                "is_syncing": True, "message": "در حال اتصال به هلو...",
                "current_stage": "connecting", "processed": 0, "total": 0
            })
            
            api = _get_api()
            if not api:
                raise Exception("ارتباط با API برقرار نشد")

            # سینک گروه‌ها و واحدها
            sync_status_parts["products"]["message"] = "در حال دریافت گروه‌ها..."
            try:
                resp_main = requests.get(f"{api.base_url}/MainGroup", headers=api.get_headers())
                if resp_main.status_code == 200:
                    save_main_groups(resp_main.json().get('mainGroup', []))
                    
                resp_side = requests.get(f"{api.base_url}/SideGroup", headers=api.get_headers())
                if resp_side.status_code == 200:
                    save_side_groups(resp_side.json().get('sideGroup', []))
                    
                resp_unit = requests.get(f"{api.base_url}/Unit", headers=api.get_headers())
                if resp_unit.status_code == 200:
                    units = resp_unit.json().get('unit', [])
                    if isinstance(units, dict):
                        units = [units]
                    save_units(units)
            except Exception as e:
                print(f"Error syncing meta-data: {e}")

            # سینک کالاها
            sync_status_parts["products"].update({
                "message": "در حال دریافت کالاها...", "current_stage": "products"
            })
            
            page = 1
            items_per_page = 50
            total_fetched = 0
            
            while True:
                url = f"{api.base_url}/Product/{page}/{items_per_page}"
                response = requests.get(url, headers=api.get_headers(), timeout=30)
                
                if response.status_code != 200:
                    break
                    
                data = response.json()
                products = data.get('product', [])
                
                if not products:
                    break
                    
                save_product_batch(products)
                total_fetched += len(products)
                
                sync_status_parts["products"].update({
                    "processed": total_fetched,
                    "total": total_fetched + 50,
                    "message": f"دریافت کالاها... ({total_fetched} عدد)"
                })
                
                if len(products) < items_per_page:
                    break
                page += 1

            sync_status_parts["products"].update({
                "total": total_fetched, "processed": total_fetched,
                "message": f"✅ سینک کالاها کامل شد! ({total_fetched} عدد)",
                "current_stage": "done"
            })
            
        except Exception as e:
            sync_status_parts["products"].update({
                "message": f"❌ خطا: {str(e)}", "current_stage": "error"
            })
            print(f"❌ Error in sync_products: {e}")
        finally:
            sync_status_parts["products"]["is_syncing"] = False

    _run_in_thread(run_sync)
    return jsonify({"status": "started"})


@sync_bp.route('/sync/customers/start', methods=['POST'])
def sync_customers_start():
    """شروع فرآیند سینک مشتریان در پس‌زمینه"""
    global customer_sync_status
    
    if customer_sync_status["is_syncing"]:
        return jsonify({"status": "error", "message": "سینک مشتریان در حال انجام است"})

    # ریست وضعیت
    customer_sync_status.update({
        "is_syncing": True, "total": 0, "processed": 0,
        "message": "در حال آماده‌سازی...", "stage": "connecting", "progress_percent": 0
    })

    def run_sync_background():
        global customer_sync_status
        try:
            customer_sync_status.update({
                "message": "در حال اتصال به هلو...", "stage": "connecting", "progress_percent": 5
            })
            
            api = _get_api()
            if not api:
                raise Exception("ارتباط با API برقرار نشد")

            # دریافت مشتریان
            customer_sync_status.update({
                "message": "در حال دریافت مشتریان از هلو...", 
                "stage": "fetching", "progress_percent": 10
            })
            
            all_customers = api.get_all_customers()
            total = len(all_customers)
            
            if total == 0:
                customer_sync_status.update({
                    "message": "⚠️ هیچ مشتریای در هلو یافت نشد",
                    "stage": "done", "progress_percent": 100, "is_syncing": False
                })
                return

            customer_sync_status.update({
                "total": total, 
                "message": f"دریافت {total} مشتری، در حال ذخیره‌سازی...",
                "stage": "saving", "progress_percent": 20
            })

            # ذخیره تدریجی
            batch_size = 100
            total_batches = (total + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, total)
                batch = all_customers[start_idx:end_idx]
                
                save_customers(batch)
                
                progress = 20 + (end_idx / total) * 75
                customer_sync_status.update({
                    "processed": end_idx,
                    "progress_percent": min(95, progress),
                    "message": f"ذخیره مشتریان... ({end_idx:,}/{total:,})"
                })
                
                time.sleep(0.05)  # کاهش فشار

            customer_sync_status.update({
                "message": f"✅ سینک مشتریان کامل شد! ({total:,} نفر)",
                "stage": "done", "progress_percent": 100, "processed": total
            })
            
        except Exception as e:
            customer_sync_status.update({
                "message": f"❌ خطا: {str(e)}", "stage": "error", "progress_percent": 0
            })
            print(f"❌ Error in sync_customers: {e}")
            import traceback
            traceback.print_exc()
        finally:
            customer_sync_status["is_syncing"] = False

    _run_in_thread(run_sync_background)
    return jsonify({"status": "started"})


@sync_bp.route('/sync/banks', methods=['POST'])
def sync_banks():
    """سینک حساب‌های بانکی"""
    if sync_status_parts["banks"]["is_syncing"]:
        return jsonify({"status": "error", "message": "سینک بانک‌ها در حال انجام است"})

    def run_sync():
        try:
            sync_status_parts["banks"].update({
                "is_syncing": True, "message": "در حال اتصال به هلو...",
                "current_stage": "connecting", "processed": 0, "total": 0
            })
            
            api = _get_api()
            if not api:
                raise Exception("ارتباط با API برقرار نشد")

            sync_status_parts["banks"].update({
                "message": "در حال دریافت حساب‌های بانکی...", "current_stage": "banks"
            })
            
            accounts = api.get_bank_accounts()
            save_bank_accounts(accounts)
            
            sync_status_parts["banks"].update({
                "total": len(accounts), "processed": len(accounts),
                "message": f"✅ سینک بانک‌ها کامل شد! ({len(accounts)} حساب)",
                "current_stage": "done"
            })
            
        except Exception as e:
            sync_status_parts["banks"].update({
                "message": f"❌ خطا: {str(e)}", "current_stage": "error"
            })
        finally:
            sync_status_parts["banks"]["is_syncing"] = False

    _run_in_thread(run_sync)
    return jsonify({"status": "started"})


@sync_bp.route('/sync/units', methods=['POST'])
def sync_units():
    """سینک واحدها و گروه‌ها"""
    if sync_status_parts["units"]["is_syncing"]:
        return jsonify({"status": "error", "message": "سینک واحدها در حال انجام است"})

    def run_sync():
        try:
            sync_status_parts["units"].update({
                "is_syncing": True, "message": "در حال اتصال به هلو...",
                "current_stage": "connecting", "processed": 0, "total": 0
            })
            
            api = _get_api()
            if not api:
                raise Exception("ارتباط با API برقرار نشد")

            main_groups = api.get_main_groups()
            save_main_groups(main_groups)
            
            side_groups = api.get_side_groups()
            save_side_groups(side_groups)
            
            units = api.get_units()
            save_units(units)
            
            total_items = len(main_groups) + len(side_groups) + len(units)
            
            sync_status_parts["units"].update({
                "total": total_items, "processed": total_items,
                "message": f"✅ سینک واحدها و گروه‌ها کامل شد!",
                "current_stage": "done"
            })
            
        except Exception as e:
            sync_status_parts["units"].update({
                "message": f"❌ خطا: {str(e)}", "current_stage": "error"
            })
        finally:
            sync_status_parts["units"]["is_syncing"] = False

    _run_in_thread(run_sync)
    return jsonify({"status": "started"})


@sync_bp.route('/sync/suppliers', methods=['POST'])
def sync_suppliers():
    """سینک تامین‌کنندگان (فروشندگان)"""
    if sync_status_parts.get("suppliers", {}).get("is_syncing", False):
        return jsonify({"status": "error", "message": "سینک تامین‌کنندگان در حال انجام است"})

    def run_sync():
        try:
            sync_status_parts["suppliers"].update({
                "is_syncing": True, "message": "در حال اتصال به هلو...",
                "current_stage": "connecting", "processed": 0, "total": 0
            })
            
            api = _get_api()
            if not api:
                raise Exception("ارتباط با API برقرار نشد")

            suppliers = api.get_all_suppliers()
            
            if suppliers:
                saved_count = save_customers(suppliers)
                sync_status_parts["suppliers"].update({
                    "total": len(suppliers), "processed": saved_count,
                    "message": f"✅ {saved_count} تامین‌کننده ذخیره شد",
                    "current_stage": "done"
                })
            else:
                sync_status_parts["suppliers"].update({
                    "message": "⚠️ هیچ تامین‌کننده‌ای یافت نشد",
                    "current_stage": "done", "processed": 0, "total": 0
                })
                
        except Exception as e:
            sync_status_parts["suppliers"].update({
                "message": f"❌ خطا: {str(e)}", "current_stage": "error"
            })
            print(f"❌ Error in sync_suppliers: {e}")
        finally:
            sync_status_parts["suppliers"]["is_syncing"] = False

    _run_in_thread(run_sync)
    return jsonify({"status": "started"})


@sync_bp.route('/sync/costs', methods=['POST'])
def sync_costs():
    """سینک سرفصل‌های هزینه"""
    if sync_status_parts["costs"]["is_syncing"]:
        return jsonify({"status": "error", "message": "سینک سرفصل‌های هزینه در حال انجام است"})

    def run_sync():
        try:
            sync_status_parts["costs"].update({
                "is_syncing": True, "message": "در حال اتصال به هلو...",
                "current_stage": "connecting", "processed": 0, "total": 0
            })
            
            api = _get_api()
            if not api:
                raise Exception("ارتباط با API برقرار نشد")

            costs = api.get_cost_headers()
            
            if costs:
                saved = save_cost_headers(costs)
                sync_status_parts["costs"].update({
                    "total": saved, "processed": saved,
                    "message": f"✅ {saved} سرفصل هزینه ذخیره شد",
                    "current_stage": "done"
                })
            else:
                sync_status_parts["costs"].update({
                    "message": "⚠️ هیچ سرفصل هزینه‌ای یافت نشد",
                    "current_stage": "done", "total": 0, "processed": 0
                })
                
        except Exception as e:
            sync_status_parts["costs"].update({
                "message": f"❌ خطا: {str(e)}", "current_stage": "error"
            })
        finally:
            sync_status_parts["costs"]["is_syncing"] = False

    _run_in_thread(run_sync)
    return jsonify({"status": "started"})


@sync_bp.route('/sync/incomes', methods=['POST'])
def sync_incomes():
    """سینک سرفصل‌های درآمد"""
    if sync_status_parts["incomes"]["is_syncing"]:
        return jsonify({"status": "error", "message": "سینک سرفصل‌های درآمد در حال انجام است"})

    def run_sync():
        try:
            sync_status_parts["incomes"].update({
                "is_syncing": True, "message": "در حال اتصال به هلو...",
                "current_stage": "connecting", "processed": 0, "total": 0
            })
            
            api = _get_api()
            if not api:
                raise Exception("ارتباط با API برقرار نشد")

            incomes = api.get_income_headers()
            
            if incomes:
                saved = save_income_headers(incomes)
                sync_status_parts["incomes"].update({
                    "total": saved, "processed": saved,
                    "message": f"✅ {saved} سرفصل درآمد ذخیره شد",
                    "current_stage": "done"
                })
            else:
                sync_status_parts["incomes"].update({
                    "message": "⚠️ هیچ سرفصل درآمدی یافت نشد",
                    "current_stage": "done", "total": 0, "processed": 0
                })
                
        except Exception as e:
            sync_status_parts["incomes"].update({
                "message": f"❌ خطا: {str(e)}", "current_stage": "error"
            })
        finally:
            sync_status_parts["incomes"]["is_syncing"] = False

    _run_in_thread(run_sync)
    return jsonify({"status": "started"})


@sync_bp.route('/sync/cash', methods=['POST'])
def sync_cash():
    """سینک سرفصل‌های صندوق"""
    if sync_status_parts["cash"]["is_syncing"]:
        return jsonify({"status": "error", "message": "سینک سرفصل‌های صندوق در حال انجام است"})

    def run_sync():
        try:
            sync_status_parts["cash"].update({
                "is_syncing": True, "message": "در حال اتصال به هلو...",
                "current_stage": "connecting", "processed": 0, "total": 0
            })
            
            api = _get_api()
            if not api:
                raise Exception("ارتباط با API برقرار نشد")

            cash_items = api.get_cash_headers()
            
            if cash_items:
                saved = save_cash_headers(cash_items)
                sync_status_parts["cash"].update({
                    "total": saved, "processed": saved,
                    "message": f"✅ {saved} سرفصل صندوق ذخیره شد",
                    "current_stage": "done"
                })
            else:
                # سرفصل‌های پیش‌فرض
                default_cash = [
                    {"Code": "10100010001", "Name": "صندوق اصلی"},
                    {"Code": "10100010002", "Name": "صندوق فرعی"},
                ]
                save_cash_headers(default_cash)
                sync_status_parts["cash"].update({
                    "total": len(default_cash), "processed": len(default_cash),
                    "message": f"⚠️ {len(default_cash)} سرفصل صندوق پیش‌فرض ذخیره شد",
                    "current_stage": "done"
                })
                
        except Exception as e:
            sync_status_parts["cash"].update({
                "message": f"❌ خطا: {str(e)}", "current_stage": "error"
            })
        finally:
            sync_status_parts["cash"]["is_syncing"] = False

    _run_in_thread(run_sync)
    return jsonify({"status": "started"})


# ==================== سینک ترکیبی ====================

@sync_bp.route('/sync/all', methods=['POST'])
def sync_all():
    """سینک همه اطلاعات (کالاها، مشتریان، بانک‌ها)"""
    busy_parts = [k for k, v in sync_status_parts.items() if v["is_syncing"]]
    
    if busy_parts:
        return jsonify({
            "status": "error", 
            "message": f"بخش‌های {', '.join(busy_parts)} در حال سینک هستند"
        })

    def run_sync_all():
        try:
            # سینک ترتیبی با استفاده از درخواست‌های داخلی
            base_url = request.host_url.rstrip('/')
            
            for part in ['products', 'customers', 'banks']:
                requests.post(f"{base_url}/sync/{part}" if part != 'customers' 
                            else f"{base_url}/sync/customers/start")
                
                # انتظار برای اتمام
                status_key = part
                while True:
                    time.sleep(1)
                    if part == 'customers':
                        if not customer_sync_status["is_syncing"]:
                            break
                    else:
                        if not sync_status_parts[status_key]["is_syncing"]:
                            break
                            
        except Exception as e:
            print(f"Error in sync all: {e}")

    _run_in_thread(run_sync_all)
    return jsonify({"status": "started"})


@sync_bp.route('/sync/purchase/start', methods=['POST'])
def sync_purchase_start():
    """شروع سینک کامل اطلاعات مورد نیاز فاکتور خرید"""
    global purchase_sync_status
    
    if purchase_sync_status["is_syncing"]:
        return jsonify({"status": "error", "message": "سینک در حال انجام است"})

    purchase_sync_status.update({
        "is_syncing": True, "total": 0, "processed": 0,
        "message": "در حال آماده‌سازی...", "stage": "connecting", "progress_percent": 0,
        "details": {k: {"total": 0, "processed": 0} for k in 
                   ['products', 'suppliers', 'banks', 'costs', 'incomes', 'units']}
    })

    def run_sync_background():
        global purchase_sync_status
        try:
            purchase_sync_status.update({
                "message": "در حال اتصال به هلو...", "stage": "connecting", "progress_percent": 2
            })
            
            api = _get_api()
            if not api:
                raise Exception("ارتباط با API برقرار نشد")

            # مراحل سینک به ترتیب
            steps = [
                ("fetching_products", "products", lambda: _sync_products_only(api)),
                ("fetching_suppliers", "suppliers", lambda: _sync_suppliers_only(api)),
                ("fetching_banks", "banks", lambda: _sync_banks_only(api)),
                ("fetching_costs", "costs", lambda: _sync_cost_headers_only(api)),
                ("fetching_incomes", "incomes", lambda: _sync_income_headers_only(api)),
                ("fetching_units", "units", lambda: _sync_units_only(api)),
            ]
            
            progress_map = {
                "fetching_products": 25, "fetching_suppliers": 50,
                "fetching_banks": 70, "fetching_costs": 85,
                "fetching_incomes": 95, "fetching_units": 100
            }

            for stage, key, func in steps:
                purchase_sync_status.update({
                    "stage": stage, 
                    "progress_percent": progress_map.get(stage, 50)
                })
                
                count = func()
                purchase_sync_status["details"][key].update({
                    "total": count, "processed": count
                })
                purchase_sync_status["processed"] += count
                purchase_sync_status["total"] += count

            purchase_sync_status.update({
                "message": f"✅ سینک اطلاعات فاکتور خرید کامل شد! ({purchase_sync_status['total']} آیتم)",
                "stage": "done", "progress_percent": 100
            })
            
        except Exception as e:
            purchase_sync_status.update({
                "message": f"❌ خطا: {str(e)}", "stage": "error", "progress_percent": 0
            })
            print(f"❌ Error in sync_purchase: {e}")
            import traceback
            traceback.print_exc()
        finally:
            purchase_sync_status["is_syncing"] = False

    _run_in_thread(run_sync_background)
    return jsonify({"status": "started"})


# ==================== توابع کمکی سینک فاکتور خرید ====================

def _sync_products_only(api):
    try:
        # سینک متادیتا
        try:
            resp_main = requests.get(f"{api.base_url}/MainGroup", headers=api.get_headers())
            if resp_main.status_code == 200:
                save_main_groups(resp_main.json().get('mainGroup', []))
            resp_side = requests.get(f"{api.base_url}/SideGroup", headers=api.get_headers())
            if resp_side.status_code == 200:
                save_side_groups(resp_side.json().get('sideGroup', []))
        except: pass

        page = 1
        total_fetched = 0
        while True:
            url = f"{api.base_url}/Product/{page}/50"
            response = requests.get(url, headers=api.get_headers(), timeout=30)
            if response.status_code != 200: break
            products = response.json().get('product', [])
            if not products: break
            save_product_batch(products)
            total_fetched += len(products)
            if len(products) < 50: break
            page += 1
        return total_fetched
    except Exception as e:
        print(f"❌ Error syncing products: {e}")
        return 0

def _sync_suppliers_only(api):
    try:
        suppliers = api.get_all_suppliers()
        if suppliers: save_customers(suppliers)
        return len(suppliers) if suppliers else 0
    except: return 0

def _sync_banks_only(api):
    try:
        accounts = api.get_bank_accounts()
        if accounts: save_bank_accounts(accounts)
        return len(accounts) if accounts else 0
    except: return 0

def _sync_cost_headers_only(api):
    try:
        costs = api.get_cost_headers()
        if costs: return save_cost_headers(costs)
        return 0
    except: return 0

def _sync_income_headers_only(api):
    try:
        incomes = api.get_income_headers()
        if incomes: return save_income_headers(incomes)
        return 0
    except: return 0

def _sync_units_only(api):
    try:
        units = api.get_units()
        if units: save_units(units)
        return len(units) if units else 0
    except: return 0


# ==================== مسیرهای وضعیت سینک ====================

@sync_bp.route('/sync-status/<part>')
def get_sync_status(part):
    """دریافت وضعیت سینک برای یک بخش خاص"""
    if part == 'customers':
        return jsonify({
            "is_syncing": customer_sync_status["is_syncing"],
            "total": customer_sync_status["total"],
            "processed": customer_sync_status["processed"],
            "message": customer_sync_status["message"],
            "current_stage": customer_sync_status["stage"],
            "progress_percent": customer_sync_status["progress_percent"]
        })
    elif part in sync_status_parts:
        return jsonify(sync_status_parts[part])
    return jsonify({"error": "بخش نامعتبر"}), 404


@sync_bp.route('/sync-status/all')
def get_all_sync_status():
    """دریافت وضعیت همه بخش‌ها"""
    result = {}
    for key, value in sync_status_parts.items():
        result[key] = dict(value)
    
    # اضافه کردن وضعیت مشتریان پیشرفته
    result['customers'] = {
        "is_syncing": customer_sync_status["is_syncing"],
        "total": customer_sync_status["total"],
        "processed": customer_sync_status["processed"],
        "message": customer_sync_status["message"],
        "current_stage": customer_sync_status["stage"],
        "progress_percent": customer_sync_status["progress_percent"]
    }
    return jsonify(result)


@sync_bp.route('/sync/purchase/status')
def sync_purchase_status():
    return jsonify(purchase_sync_status)

@sync_bp.route('/sync/purchase/check')
def sync_purchase_check():
    return jsonify({
        "is_syncing": purchase_sync_status["is_syncing"],
        "stage": purchase_sync_status["stage"],
        "progress_percent": purchase_sync_status["progress_percent"],
        "message": purchase_sync_status["message"],
        "total": purchase_sync_status["total"],
        "processed": purchase_sync_status["processed"]
    })

@sync_bp.route('/sync/customers/status')
def sync_customers_status():
    return jsonify(customer_sync_status)

@sync_bp.route('/sync/customers/cancel', methods=['POST'])
def sync_customers_cancel():
    global customer_sync_status
    if customer_sync_status["is_syncing"]:
        customer_sync_status.update({
            "is_syncing": False, "message": "⛔ سینک لغو شد", "stage": "idle"
        })
        return jsonify({"status": "cancelled"})
    return jsonify({"status": "not_syncing"})

@sync_bp.route('/sync/purchase/cancel', methods=['POST'])
def sync_purchase_cancel():
    global purchase_sync_status
    if purchase_sync_status["is_syncing"]:
        purchase_sync_status.update({
            "is_syncing": False, "message": "⛔ سینک لغو شد", "stage": "idle"
        })
        return jsonify({"status": "cancelled"})
    return jsonify({"status": "not_syncing"})


# ==================== سینک پایه (قدیمی - برای سازگاری) ====================

@sync_bp.route('/sync-base-data', methods=['POST'])
def sync_base_data():
    if base_sync_status["is_syncing"]:
        return jsonify({"status": "error", "message": "سینک در حال انجام است"})

    def run_sync_base():
        global base_sync_status
        try:
            base_sync_status.update({
                "is_syncing": True, "message": "در حال اتصال به هلو...",
                "current_stage": "connecting", "processed": 0, "total": 0
            })
            
            api = _get_api()
            if not api:
                raise Exception("ارتباط با API برقرار نشد")

            # کالاها
            base_sync_status.update({"message": "در حال دریافت کالاها...", "current_stage": "products"})
            page = 1
            total_fetched = 0
            while True:
                url = f"{api.base_url}/Product/{page}/50"
                response = requests.get(url, headers=api.get_headers(), timeout=30)
                if response.status_code != 200: break
                products = response.json().get('product', [])
                if not products: break
                save_product_batch(products)
                total_fetched += len(products)
                base_sync_status.update({"processed": total_fetched, "message": f"دریافت کالاها... ({total_fetched})"})
                if len(products) < 50: break
                page += 1

            # مشتریان
            base_sync_status.update({"message": "در حال دریافت اشخاص...", "current_stage": "customers", "processed": 0})
            customers = api.get_customers(purchaser=True)
            save_customers(customers)
            base_sync_status.update({"processed": len(customers), "total": len(customers)})

            # بانک‌ها
            base_sync_status.update({"message": "در حال دریافت حساب‌های بانکی...", "current_stage": "banks", "processed": 0})
            accounts = api.get_bank_accounts()
            save_bank_accounts(accounts)
            base_sync_status.update({"processed": len(accounts), "total": len(accounts)})

            base_sync_status.update({
                "message": "✅ سینک اطلاعات پایه با موفقیت انجام شد", "current_stage": "done"
            })
        except Exception as e:
            base_sync_status.update({"message": f"❌ خطا: {str(e)}", "current_stage": "error"})
        finally:
            base_sync_status["is_syncing"] = False

    _run_in_thread(run_sync_base)
    return jsonify({"status": "started"})

@sync_bp.route('/base-sync-status')
def get_base_sync_status():
    return jsonify(base_sync_status)