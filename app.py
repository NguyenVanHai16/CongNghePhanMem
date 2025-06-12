import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or "dev-secret-key-thai-nguyen-barbershop"
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL") or "sqlite:///barbershop.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the database
db.init_app(app)

# Custom Jinja2 filters
@app.template_filter('format_currency')
def format_currency(value):
    """Format a number as Vietnamese currency (VND)"""
    if value is None:
        return "0 VNĐ"
    return "{:,}".format(int(value))

with app.app_context():
    # Import models to ensure tables are created
    import models  # noqa: F401
    db.create_all()
    logging.info("Database tables created successfully")

