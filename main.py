from app import app, db
import routes  # noqa: F401

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Tạo lại tất cả bảng trong database
    app.run(host="0.0.0.0", port=5000, debug=True)

