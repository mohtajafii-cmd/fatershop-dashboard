# routes/__init__.py
from flask import Blueprint

def register_blueprints(app):
    """ثبت تمام بلوپرینت‌ها در اپلیکیشن فلَسک"""
    from .sync import sync_bp
    from .pos import pos_bp
    from .purchase import purchase_bp
    from .batch_edit import batch_edit_bp
    from .build import build_bp
    from .products import products_bp
    from .settings import settings_bp
    from .allocation import allocation_bp
    from .webhook import webhook_bp  # ✅ اضافه شد

    app.register_blueprint(sync_bp)
    app.register_blueprint(pos_bp)
    app.register_blueprint(purchase_bp)
    app.register_blueprint(batch_edit_bp)
    app.register_blueprint(build_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(allocation_bp)
    app.register_blueprint(webhook_bp)  # ✅ اضافه شد

    print("✅ تمامی بلوپرینت‌ها با موفقیت ثبت شدند.")