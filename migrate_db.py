from app import app, db
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_average_rating_column():
    # Đường dẫn đến file database
    db_path = "barbershop.db"  # Điều chỉnh nếu cần
    
    # Kiểm tra xem file database có tồn tại không
    if not os.path.exists(db_path):
        logger.info(f"Database file {db_path} không tồn tại. Tạo database mới...")
        # Tạo database và các bảng bằng Flask-SQLAlchemy
        with app.app_context():
            db.create_all()
            logger.info("Đã tạo database và các bảng")
    
    # Kết nối đến database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Kiểm tra xem bảng shop có tồn tại không
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shop'")
    if not cursor.fetchone():
        logger.error("Bảng 'shop' không tồn tại trong database")
        logger.info("Tạo bảng 'shop'...")
        with app.app_context():
            db.create_all()
        logger.info("Đã tạo bảng 'shop'")
    
    # Kiểm tra xem cột đã tồn tại chưa
    cursor.execute("PRAGMA table_info(shop)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Nếu cột chưa tồn tại, thêm vào
    if "average_rating" not in columns:
        cursor.execute("ALTER TABLE shop ADD COLUMN average_rating FLOAT DEFAULT 0.0")
        logger.info("Đã thêm cột average_rating vào bảng shop")
    else:
        logger.info("Cột average_rating đã tồn tại")
    
    # Lưu thay đổi và đóng kết nối
    conn.commit()
    conn.close()

if __name__ == "__main__":
    try:
        add_average_rating_column()
        logger.info("Migration hoàn tất")
    except Exception as e:
        logger.error(f"Lỗi khi thực hiện migration: {e}")


