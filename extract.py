import os

# تنظیمات
ROOT_DIR = r'F:\HolooAutomation\fatershop-dashboard'  # مسیر ریشه پروژه خود را اینجا وارد کنید
OUTPUT_FILE = 'project_export.txt'
ALLOWED_EXTENSIONS = ('.py', '.html','.css','.json','.js','.txt')

def export_project_to_text(root_dir, output_file):
    with open(output_file, 'w', encoding='utf-8') as out:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # مرتب‌سازی برای نظم بهتر در خروجی
            dirnames.sort()
            filenames.sort()
            
            for filename in filenames:
                if filename.lower().endswith(ALLOWED_EXTENSIONS):
                    full_path = os.path.join(dirpath, filename)
                    
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # نوشتن هدر شامل نام و آدرس فایل
                        out.write(f"File: {filename}\n")
                        out.write(f"Path: {full_path}\n")
                        out.write("=" * 80 + "\n")
                        out.write(content)
                        out.write("\n\n" + "#" * 80 + "\n\n")
                        
                    except Exception as e:
                        out.write(f"File: {filename}\nPath: {full_path}\n")
                        out.write(f"Error reading file: {str(e)}\n\n")

if __name__ == "__main__":
    export_project_to_text(ROOT_DIR, OUTPUT_FILE)
    print(f"✅ Export completed successfully!")
    print(f"📄 Output saved to: {os.path.abspath(OUTPUT_FILE)}")