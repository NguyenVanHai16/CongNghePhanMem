from app import app, db
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database():
    # Lấy đường dẫn database từ cấu hình Flask
    db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    
    # Trích xuất đường dẫn file từ URI
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '')
        logger.info(f"Đường dẫn database: {db_path}")
        
        # Xóa file database cũ nếu tồn tại
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                logger.info(f"Đã xóa file database cũ: {db_path}")
            except Exception as e:
                logger.error(f"Không thể xóa file database cũ: {e}")
    
    # Tạo database và các bảng mới
    with app.app_context():
        logger.info("Tạo database và các bảng mới...")
        db.create_all()
        logger.info("Đã tạo database và các bảng thành công")

if __name__ == "__main__":
    try:
        reset_database()
    except Exception as e:
        logger.error(f"Lỗi khi reset database: {e}")