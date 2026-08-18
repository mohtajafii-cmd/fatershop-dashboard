import requests
import base64
import json


class HolooAPI:
    def __init__(self, config):
        self.ip = config['ip']
        self.port = config['port']
        self.username = config['username']
        self.password = config['password']
        self.dbname = config['dbname']
        # آدرس پایه طبق مستندات و تصویر شما
        self.base_url = f"http://{self.ip}:{self.port}/TncHoloo/api"
        self.token = None

        # انجام لاگین هنگام ایجاد شیء
        if not self.login():
            raise Exception("Login Failed. Please check your credentials and Holoo Web Service status.")

    def login(self):
        url = f"{self.base_url}/Login"

        # تبدیل پسورد به Base64 همانطور که در Postman دیدیم
        pwd_bytes = self.password.encode('utf-8')
        encoded_pwd = base64.b64encode(pwd_bytes).decode('utf-8')

        payload = {
            "userinfo": {
                "username": self.username,
                "userpass": encoded_pwd,
                "dbname": self.dbname
            }
        }

        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            data = response.json()

            # بررسی پاسخ طبق مستندات
            if data.get('Login', {}).get('State') == True:
                self.token = data['Login']['Token']
                print("✅ Login Successful. Token received.")
                return True
            else:
                error_msg = data.get('Login', {}).get('Error')
                print(f"❌ Login Failed: {error_msg}")
                return False

        except Exception as e:
            print(f"❌ Connection Error: {e}")
            return False
# holoo_api.py - اضافه شده به کلاس HolooAPI
# holoo_api.py - اضافه کردن به کلاس HolooAPI

    # ----- دریافت سرفصل‌های هزینه -----
# holoo_api.py - داخل کلاس HolooAPI

    def get_cost_headers(self):
        """دریافت لیست سرفصل‌های هزینه از هلو"""
        url = f"{self.base_url}/Payment/Cost"
        try:
            print(f"📤 Fetching cost headers from: {url}")
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Cost headers received: {len(data) if isinstance(data, list) else 'not a list'}")
                # اگر داده لیست نبود، تبدیل کن
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    # ممکن است کلید 'cost' یا 'result' داشته باشد
                    if 'cost' in data:
                        return data['cost']
                    elif 'result' in data:
                        return data['result']
                    return [data]
                return []
            else:
                print(f"❌ Failed to fetch cost headers. Status: {response.status_code}")
                print(f"❌ Response: {response.text[:200]}")
                return []
        except Exception as e:
            print(f"❌ Error fetching cost headers: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_income_headers(self):
        """دریافت لیست سرفصل‌های درآمد از هلو"""
        url = f"{self.base_url}/Payment/Income"
        try:
            print(f"📤 Fetching income headers from: {url}")
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Income headers received: {len(data) if isinstance(data, list) else 'not a list'}")
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    if 'income' in data:
                        return data['income']
                    elif 'result' in data:
                        return data['result']
                    return [data]
                return []
            else:
                print(f"❌ Failed to fetch income headers. Status: {response.status_code}")
                print(f"❌ Response: {response.text[:200]}")
                return []
        except Exception as e:
            print(f"❌ Error fetching income headers: {e}")
            import traceback
            traceback.print_exc()
            return []
    # holoo_api.py - اصلاح کامل متد get_all_suppliers

    def get_all_suppliers(self):
        """دریافت همه تامین‌کنندگان (افرادی که IsSeller=True هستند)"""
        url = f"{self.base_url}/Customer"
        params = {'seller': 'true'}
        try:
            print(f"📤 Fetching suppliers from: {url}")
            print(f"📤 Params: {params}")
            response = requests.get(url, headers=self.get_headers(), params=params, timeout=60)
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Failed to fetch suppliers. Status: {response.status_code}")
                print(f"❌ Response: {response.text[:200]}")
                return []
            
            data = response.json()
            # کلید پاسخ می‌تواند 'customer' یا 'Customer' باشد
            suppliers = data.get('customer', [])
            if not suppliers:
                suppliers = data.get('Customer', [])
            
            print(f"✅ Total suppliers fetched: {len(suppliers)}")
            
            # نمایش ۵ تامین‌کننده اول برای دیباگ
            for i, sup in enumerate(suppliers[:5]):
                code = sup.get('Code', 'N/A')
                name = sup.get('Name', 'N/A')
                is_seller = sup.get('IsSeller', False)
                print(f"  {i+1}. Code: {code}, Name: {name}, IsSeller: {is_seller}")
            
            return suppliers
            
        except Exception as e:
            print(f"❌ Error fetching suppliers: {e}")
            import traceback
            traceback.print_exc()
            return []
    # ----- دریافت سرفصل‌های هزینه -----
# holoo_api.py - داخل کلاس HolooAPI

# holoo_api.py - جایگزین متدهای get_cost_headers و get_income_headers

    def get_cost_headers(self):
        """دریافت لیست سرفصل‌های هزینه از هلو - تست چند آدرس"""
        # لیست آدرس‌های احتمالی
        possible_urls = [
            f"{self.base_url}/Payment/Cost",
            f"{self.base_url}/Payment/GetCostHeaders",
            f"{self.base_url}/CostHeaders",
            f"{self.base_url}/Cost",
            f"{self.base_url}/GetCostHeaders",
            f"{self.base_url}/Payment/CostHeader",
        ]
        
        for url in possible_urls:
            try:
                print(f"📤 Trying: {url}")
                response = requests.get(url, headers=self.get_headers(), timeout=10)
                print(f"📥 Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"✅ Found cost headers at: {url}")
                    data = response.json()
                    
                    # اگر داده لیست نبود، سعی کن استخراج کنی
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        # کلیدهای احتمالی
                        for key in ['cost', 'result', 'data', 'items']:
                            if key in data:
                                return data[key]
                        return [data]
                    return []
                    
            except Exception as e:
                print(f"⚠️ Error with {url}: {e}")
                continue
        
        print("❌ No valid URL found for cost headers")
        return []

    def get_income_headers(self):
        """دریافت لیست سرفصل‌های درآمد از هلو - تست چند آدرس"""
        possible_urls = [
            f"{self.base_url}/Payment/Income",
            f"{self.base_url}/Payment/GetIncomeHeaders",
            f"{self.base_url}/IncomeHeaders",
            f"{self.base_url}/Income",
            f"{self.base_url}/GetIncomeHeaders",
            f"{self.base_url}/Payment/IncomeHeader",
        ]
        
        for url in possible_urls:
            try:
                print(f"📤 Trying: {url}")
                response = requests.get(url, headers=self.get_headers(), timeout=10)
                print(f"📥 Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"✅ Found income headers at: {url}")
                    data = response.json()
                    
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        for key in ['income', 'result', 'data', 'items']:
                            if key in data:
                                return data[key]
                        return [data]
                    return []
                    
            except Exception as e:
                print(f"⚠️ Error with {url}: {e}")
                continue
        
        print("❌ No valid URL found for income headers")
        return []
    

    def get_headers(self):
        """هدرهای لازم برای تمام درخواست‌های بعد از لاگین"""
        if not self.token:
            raise Exception("Not logged in.")
        return {
            'Authorization': self.token,  # توکن دریافتی در لاگین
            'Content-Type': 'application/json'
        }

    def get_products(self, code=None):
        """دریافت لیست محصولات یا جستجو بر اساس کد"""
        url = f"{self.base_url}/Product"
        params = {}
        if code:
            params['code'] = code

        try:
            response = requests.get(url, headers=self.get_headers(), params=params)
            if response.status_code == 200:
                return response.json().get('product', [])
            else:
                print(f"Failed to fetch products. Status: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error fetching products: {e}")
            return []

        # در فایل holoo_api.py متد زیر را اضافه کنید:
    def get_product_by_code(self, code):
        """دریافت اطلاعات یک کالا بر اساس کد کالا"""
        url = f"{self.base_url}/Product"
        params = {'code': code}
        try:
            response = requests.get(url, headers=self.get_headers(), params=params, timeout=10)
            if response.status_code == 200:
                products = response.json().get('product', [])
                if products:
                    return products[0]
            return None
        except Exception as e:
            print(f"❌ Error fetching product by code {code}: {e}")
            return None

    def get_product_by_name(self, name):
        """دریافت اطلاعات یک کالا بر اساس نام دقیق"""
        url = f"{self.base_url}/Product"
        params = {'name': f'"{name}"'}  # جستجوی دقیق با نقل قول
        try:
            response = requests.get(url, headers=self.get_headers(), params=params, timeout=10)
            if response.status_code == 200:
                products = response.json().get('product', [])
                # پیدا کردن کالایی که نامش دقیقاً مطابقت دارد
                for p in products:
                    if p.get('Name') == name:
                        return p
            return None
        except Exception as e:
            print(f"❌ Error fetching product by name {name}: {e}")
            return None
    def sync_all_products(self):
        """دریافت تمام محصولات از هلو"""
        url = f"{self.base_url}/Product"
        all_products = []
        page = 1
        items_per_page = 100  # تعداد آیتم در هر صفحه

        while True:
            # استفاده از صفحه‌بندی طبق مستندات: /Product/{page}/{items_per_page}
            response = requests.get(f"{url}/{page}/{items_per_page}", headers=self.get_headers())
            if response.status_code != 200:
                break

            data = response.json()
            products = data.get('product', [])

            if not products:
                break

            all_products.extend(products)

            # اگر تعداد محصولات کمتر از سایز صفحه بود، یعنی صفحه آخر است
            if len(products) < items_per_page:
                break

            page += 1

        return all_products
    def update_product(self, product_data):
        """ویرایش محصول با متد PUT"""
        url = f"{self.base_url}/Product"

        # ساختار بدنه درخواست برای ویرایش طبق مستندات
        # توجه: product_data باید شامل erpcode باشد
        payload = {
            "productinfo": [product_data]
        }

        try:
            response = requests.put(url, headers=self.get_headers(), json=payload)
            return response.json()
        except Exception as e:
            return {"Error": str(e)}




# holoo_api.py (اضافه شده به انتهای کلاس)

    # ----- دریافت اشخاص -----
    def get_customers(self, code_from=None, code_to=None, purchaser=None, seller=None, vaseteh=None):
        """دریافت لیست اشخاص از هلو با گزینه‌های فیلتر"""
        url = f"{self.base_url}/Customer"
        params = {}
        if code_from:
            params['code.from'] = code_from
        if code_to:
            params['code.to'] = code_to
        if purchaser is not None:
            params['purchaser'] = str(purchaser).lower()
        if seller is not None:
            params['seller'] = str(seller).lower()
        if vaseteh is not None:
            params['vaseteh'] = str(vaseteh).lower()
        
        try:
            print(f"📤 Fetching customers from: {url}")
            print(f"📤 Params: {params}")
            response = requests.get(url, headers=self.get_headers(), params=params, timeout=30)
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                customers = data.get('customer', [])
                print(f"✅ Found {len(customers)} customers")
                return customers
            else:
                print(f"❌ Failed to fetch customers. Status: {response.status_code}")
                print(f"❌ Response: {response.text[:200]}")
                return []
        except Exception as e:
            print(f"❌ Error fetching customers: {e}")
            return []




# holoo_api.py - اضافه کردن متد جدید برای دریافت همه مشتریان با صفحه‌بندی

# holoo_api.py - اصلاح متد get_all_customers

# holoo_api.py - متد دریافت همه مشتریان

# holoo_api.py - متد دریافت همه مشتریان (بدون فیلتر)

    def get_all_customers(self):
        """دریافت همه مشتریان از هلو (بدون فیلتر)"""
        url = f"{self.base_url}/Customer"
        
        try:
            print(f"📤 Fetching all customers from: {url}")
            response = requests.get(url, headers=self.get_headers(), timeout=60)
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Failed to fetch customers. Status: {response.status_code}")
                return []
            
            data = response.json()
            
            # کلید پاسخ می‌تواند 'Customer' یا 'customer' باشد
            customers = data.get('Customer', [])
            if not customers:
                customers = data.get('customer', [])
            
            print(f"✅ Total customers fetched: {len(customers)}")
            
            # نمایش ۵ مشتری اول برای دیباگ
            for i, cust in enumerate(customers[:5]):
                code = cust.get('Code', 'N/A')
                name = cust.get('Name', 'N/A')
                print(f"  {i+1}. Code: {code}, Name: {name}")
            
            return customers
            
        except Exception as e:
            print(f"❌ Error fetching customers: {e}")
            import traceback
            traceback.print_exc()
            return []

# متد قبلی get_customers را هم به‌روزرسانی می‌کنیم
    def get_customers(self, code_from=None, code_to=None, purchaser=None, seller=None, vaseteh=None):
        """دریافت لیست اشخاص از هلو با گزینه‌های فیلتر (بدون صفحه‌بندی)"""
        url = f"{self.base_url}/Customer"
        params = {}
        if code_from:
            params['code.from'] = code_from
        if code_to:
            params['code.to'] = code_to
        if purchaser is not None:
            params['purchaser'] = str(purchaser).lower()
        if seller is not None:
            params['seller'] = str(seller).lower()
        if vaseteh is not None:
            params['vaseteh'] = str(vaseteh).lower()
        
        try:
            print(f"📤 Fetching customers from: {url}")
            print(f"📤 Params: {params}")
            response = requests.get(url, headers=self.get_headers(), params=params, timeout=30)
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                customers = data.get('customer', [])
                print(f"✅ Found {len(customers)} customers")
                return customers
            else:
                print(f"❌ Failed to fetch customers. Status: {response.status_code}")
                print(f"❌ Response: {response.text[:200]}")
                return []
        except Exception as e:
            print(f"❌ Error fetching customers: {e}")
            return []
        






    # ----- دریافت واحدها -----
    def get_units(self):
        """دریافت لیست واحدها از هلو"""
        url = f"{self.base_url}/Unit"
        try:
            print(f"📤 Fetching units from: {url}")
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                # بررسی ساختار پاسخ
                units = data.get('unit', [])
                # اگر واحدها به صورت دیکشنری برگشت داده شد، تبدیل به لیست
                if isinstance(units, dict):
                    units = [units]
                print(f"✅ Found {len(units)} units")
                return units
            else:
                print(f"❌ Failed to fetch units. Status: {response.status_code}")
                print(f"❌ Response: {response.text[:200]}")
                return []
        except Exception as e:
            print(f"❌ Error fetching units: {e}")
            return []











    def get_main_groups(self):
        """دریافت لیست گروه‌های اصلی از هلو"""
        url = f"{self.base_url}/MainGroup"
        try:
            print(f"📤 Fetching main groups from: {url}")
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            if response.status_code == 200:
                data = response.json()
                groups = data.get('mainGroup', [])
                print(f"✅ Found {len(groups)} main groups")
                return groups
            else:
                print(f"❌ Failed to fetch main groups. Status: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error fetching main groups: {e}")
            return []

    # ----- دریافت گروه‌های فرعی -----
    def get_side_groups(self, main_group_erp=None):
        """دریافت لیست گروه‌های فرعی از هلو"""
        url = f"{self.base_url}/SideGroup"
        params = {}
        if main_group_erp:
            params['maingrouperpcode'] = main_group_erp
        
        try:
            print(f"📤 Fetching side groups from: {url}")
            response = requests.get(url, headers=self.get_headers(), params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                groups = data.get('sideGroup', [])
                print(f"✅ Found {len(groups)} side groups")
                return groups
            else:
                print(f"❌ Failed to fetch side groups. Status: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error fetching side groups: {e}")
            return []





    # db_manager.py - اصلاح تابع save_units

    def save_units(units_list):
        """ذخیره لیست واحدها در دیتابیس"""
        if not units_list:
            print("⚠️ No units to save")
            return
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # اگر واحدها به صورت دیکشنری تکی بود، تبدیل به لیست
        if isinstance(units_list, dict):
            units_list = [units_list]
        
        saved_count = 0
        for u in units_list:
            erp_code = u.get('ErpCode')
            name = u.get('Name')
            if erp_code and name:
                c.execute('INSERT OR REPLACE INTO units (erp_code, name) VALUES (?, ?)', (erp_code, name))
                saved_count += 1
        
        conn.commit()
        conn.close()
        print(f"✅ {saved_count} units saved to database")



    def get_bank_accounts(self, is_current=None, has_pos=None):
        """دریافت لیست حساب‌های بانکی از هلو"""
        url = f"{self.base_url}/Payment/Account"
        params = {}
        if is_current is not None: 
            params['isCurrent'] = str(is_current).lower()
        if has_pos is not None: 
            params['hasPos'] = str(has_pos).lower()
        
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch bank accounts. Status: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error fetching bank accounts: {e}")
            return []
        

    def register_invoice(self, invoice_data):
        """
        ثبت فاکتور در هلو
        invoice_data: دیکشنری حاوی اطلاعات فاکتور
        """
        url = f"{self.base_url}/Invoice/Invoice"
        
        # ✅ اطمینان از وجود detailinfo
        if not invoice_data.get('detailinfo') or len(invoice_data.get('detailinfo', [])) == 0:
            return {"Failure": {"Error": "کالاهای فاکتور مشخص نشده اند", "ErrorCode": 126}}
        
        payload = {
            "invoiceinfo": [invoice_data]
        }
        
        print(f"📤 Registering invoice to: {url}")
        print(f"📤 Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        try:
            response = requests.post(url, headers=self.get_headers(), json=payload, timeout=30)
            print(f"📥 Status: {response.status_code}")
            print(f"📥 Response: {response.text[:500]}")
            return response.json()
        except Exception as e:
            print(f"❌ Error registering invoice: {e}")
            return {"Failure": {"Error": str(e)}}
    
    # ----- دریافت اشخاص (مشتریان) -----
    def get_customers(self, code_from=None, code_to=None, purchaser=None, seller=None):
        """دریافت لیست اشخاص از هلو"""
        url = f"{self.base_url}/Customer"
        params = {}
        if code_from:
            params['code.from'] = code_from
        if code_to:
            params['code.to'] = code_to
        if purchaser is not None:
            params['purchaser'] = str(purchaser).lower()
        if seller is not None:
            params['seller'] = str(seller).lower()
        
        try:
            response = requests.get(url, headers=self.get_headers(), params=params, timeout=30)
            if response.status_code == 200:
                return response.json().get('customer', [])
            else:
                print(f"❌ Failed to fetch customers. Status: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error fetching customers: {e}")
            return []

    # ----- دریافت حساب‌های بانکی -----
    def get_bank_accounts(self, is_current=None, has_pos=None):
        """دریافت لیست حساب‌های بانکی از هلو"""
        url = f"{self.base_url}/Payment/Account"
        params = {}
        if is_current is not None:
            params['isCurrent'] = str(is_current).lower()
        if has_pos is not None:
            params['hasPos'] = str(has_pos).lower()
        
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to fetch bank accounts. Status: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error fetching bank accounts: {e}")
            return []

    # ----- ثبت فاکتور فروش -----
    def register_invoice(self, invoice_data):
        """ثبت فاکتور فروش در هلو"""
        url = f"{self.base_url}/Invoice/Invoice"
        payload = {
            "invoiceinfo": [invoice_data]
        }
        try:
            response = requests.post(url, headers=self.get_headers(), json=payload, timeout=30)
            return response.json()
        except Exception as e:
            return {"Failure": {"Error": str(e)}}
        



# holoo_api.py - اصلاح کامل متد build_product با لاگ‌گیری دقیق

    def build_product(self, build_data):
        """
        تولید کالا (Build) در هلو با لاگ‌گیری کامل
        """
        import json
        import datetime
        
        # ✅ ثبت زمان شروع
        start_time = datetime.datetime.now()
        print(f"\n{'='*60}")
        print(f"🕐 START BUILD at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        # ✅ آدرس‌های احتمالی برای تست
        urls_to_try = [
            f"{self.base_url}/Product/build",
            f"{self.base_url}/Product/Build",
            f"{self.base_url}/Build",
            f"{self.base_url}/Build/Product",
            f"{self.base_url}/Product/Formula",
        ]
        
        # ✅ ساخت payload
        consumers = []
        for item in build_data.get('consumers', []):
            consumer = {
                "aCode": item.get('aCode', item.get('ErpCode', '')),
                "few": int(item.get('few', 0)),
                "comment": item.get('comment', '')
            }
            # ✅ فقط در صورت وجود carton اضافه کن
            if item.get('carton', 0) > 0:
                consumer["carton"] = int(item.get('carton', 0))
            consumers.append(consumer)
        
        production = {
            "aCode": build_data.get('production', {}).get('aCode', build_data.get('production', {}).get('ErpCode', '')),
            "few": int(build_data.get('production', {}).get('few', 0)),
            "comment": build_data.get('production', {}).get('comment', '')
        }
        if build_data.get('production', {}).get('carton', 0) > 0:
            production["carton"] = int(build_data.get('production', {}).get('carton', 0))
        
        payload = {
            "consumers": consumers,
            "production": production
        }
        
        # ✅ حذف فیلدهای خالی
        for consumer in payload['consumers']:
            if not consumer.get('comment'):
                del consumer['comment']
        if not production.get('comment'):
            del production['comment']
        
        print(f"\n📤 PAYLOAD TO HOLOO:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"\n📤 CONSUMERS COUNT: {len(payload['consumers'])}")
        print(f"📤 PRODUCTION FEW: {payload['production']['few']}")
        
        # ✅ تست هر آدرس
        for url in urls_to_try:
            print(f"\n{'='*60}")
            print(f"🔍 TRYING URL: {url}")
            print(f"{'='*60}")
            
            try:
                response = requests.post(url, headers=self.get_headers(), json=payload, timeout=30)
                
                print(f"\n📥 STATUS CODE: {response.status_code}")
                print(f"📥 HEADERS: {dict(response.headers)}")
                
                try:
                    response_data = response.json()
                    print(f"📥 RESPONSE BODY:")
                    print(json.dumps(response_data, ensure_ascii=False, indent=2))
                except:
                    print(f"📥 RESPONSE TEXT: {response.text[:500]}")
                
                if response.status_code == 200:
                    end_time = datetime.datetime.now()
                    print(f"\n✅ SUCCESS at: {url}")
                    print(f"⏱️  TIME: {(end_time - start_time).total_seconds()} seconds")
                    return response_data
                else:
                    print(f"\n❌ FAILED with status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"\n⏰ TIMEOUT for: {url}")
            except requests.exceptions.ConnectionError as e:
                print(f"\n🔌 CONNECTION ERROR for: {url}")
                print(f"   {e}")
            except Exception as e:
                print(f"\n❌ UNKNOWN ERROR for: {url}")
                print(f"   {e}")
        
        end_time = datetime.datetime.now()
        print(f"\n{'='*60}")
        print(f"❌ ALL URLS FAILED")
        print(f"⏱️  TOTAL TIME: {(end_time - start_time).total_seconds()} seconds")
        print(f"{'='*60}\n")
        
        return {
            "status": "error",
            "message": "هیچ آدرسی برای تولید کالا پاسخ نداد",
            "urls_tried": urls_to_try
        }

    def get_cash_headers(self):
        """دریافت لیست سرفصل‌های صندوق از هلو"""
        url = f"{self.base_url}/Payment/Cash"
        try:
            print(f"📤 Fetching cash headers from: {url}")
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Cash headers received: {data}")
                return data
            else:
                print(f"❌ Failed to fetch cash headers. Status: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error fetching cash headers: {e}")
            return []








    # ----- دریافت شماره فاکتور از پیش‌فاکتور/سفارش (در صورت نیاز) -----
    def convert_pre_invoice(self, erp_code):
        url = f"{self.base_url}/Invoice/PreInvoiceConvert"
        params = {'erpcode': erp_code}
        try:
            response = requests.get(url, headers=self.get_headers(), params=params)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error converting pre-invoice: {e}")
            return None