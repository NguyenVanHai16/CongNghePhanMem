from app import app, db
from models import User, Shop, Service, Barber, Booking, Promotion, Review, Favorite
from datetime import datetime, timedelta, time
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_demo_data():
    with app.app_context():
        # Xóa dữ liệu hiện có
        logger.info("Xóa dữ liệu hiện có...")
        Favorite.query.delete()
        Booking.query.delete()
        Review.query.delete()
        Promotion.query.delete()
        Barber.query.delete()
        Service.query.delete()
        Shop.query.delete()
        # Không xóa User để giữ lại tài khoản admin
        User.query.filter(User.role != 'admin').delete()
        db.session.commit()
        
        logger.info("Bắt đầu tạo dữ liệu demo...")
        
        # Tạo 5 tài khoản chủ tiệm
        shop_owners = []
        for i in range(1, 6):
            user = User(
                username=f"shop{i}",
                email=f"shop{i}@example.com",
                phone=f"090123456{i}",
                full_name=f"Chủ Tiệm {i}",
                role="shop_owner"
            )
            user.set_password("shop123")
            db.session.add(user)
            shop_owners.append(user)
        
        db.session.commit()
        logger.info("Đã tạo 5 tài khoản chủ tiệm")
        
        # Tạo 3 tài khoản khách hàng
        customers = []
        for i in range(1, 4):
            user = User(
                username=f"customer{i}",
                email=f"customer{i}@example.com",
                phone=f"098765432{i}",
                full_name=f"Khách Hàng {i}",
                role="customer"
            )
            user.set_password("customer123")
            db.session.add(user)
            customers.append(user)
        
        db.session.commit()
        logger.info("Đã tạo 3 tài khoản khách hàng")
        
        # Tạo cửa hàng cho mỗi chủ tiệm
        shops = []
        shop_names = ["Barber Shop An", "Bình's Hair Salon", "Cúc Hair Salon", 
                      "Dũng Barber Shop", "Hoa Beauty Salon"]
        shop_addresses = ["123 Quang Trung, Thái Nguyên", "45 Lương Ngọc Quyến, Thái Nguyên",
                         "78 Hoàng Văn Thụ, Thái Nguyên", "25 Nha Trang, Thái Nguyên",
                         "56 Lê Hồng Phong, Thái Nguyên"]
        shop_descriptions = [
            "Tiệm cắt tóc nam cao cấp với không gian hiện đại, thợ tay nghề cao.",
            "Tiệm cắt tóc nam nữ với đội ngũ thợ chuyên nghiệp, nhiều năm kinh nghiệm.",
            "Tiệm cắt tóc chuyên phục vụ sinh viên với giá cả phải chăng.",
            "Tiệm cắt tóc nam phong cách Châu Âu, không gian sang trọng.",
            "Salon tóc chuyên phục vụ nữ giới với các dịch vụ làm đẹp toàn diện."
        ]
        
        for i, owner in enumerate(shop_owners):
            shop = Shop(
                name=shop_names[i],
                address=shop_addresses[i],
                phone=owner.phone,
                description=shop_descriptions[i],
                opening_time=time(8, 0),
                closing_time=time(20, 0),
                distance_from_university=(i+1)*0.5,
                latitude=21.5900 + i*0.001,
                longitude=105.8500 + i*0.001,
                is_approved=True,
                owner_id=owner.id  # Sửa từ user_id thành owner_id
            )
            db.session.add(shop)
            shops.append(shop)
        
        db.session.commit()
        logger.info("Đã tạo 5 cửa hàng")
        
        # Tạo dịch vụ cho mỗi cửa hàng
        services = []
        service_data = [
            [
                {"name": "Cắt tóc nam", "description": "Cắt tóc nam cơ bản", "price": 50000, "duration": 30},
                {"name": "Uốn tóc", "description": "Uốn tóc nam phong cách Hàn Quốc", "price": 200000, "duration": 120},
                {"name": "Nhuộm tóc", "description": "Nhuộm tóc màu thời trang", "price": 250000, "duration": 120}
            ],
            [
                {"name": "Cắt tóc nam", "description": "Cắt tóc nam theo yêu cầu", "price": 60000, "duration": 30},
                {"name": "Cắt tóc nữ", "description": "Cắt tóc nữ theo yêu cầu", "price": 80000, "duration": 45},
                {"name": "Gội đầu", "description": "Gội đầu massage", "price": 50000, "duration": 30}
            ],
            [
                {"name": "Cắt tóc sinh viên", "description": "Cắt tóc giá rẻ cho sinh viên", "price": 40000, "duration": 20},
                {"name": "Cạo râu", "description": "Cạo râu, tỉa râu", "price": 20000, "duration": 15},
                {"name": "Nhuộm tóc", "description": "Nhuộm tóc màu thời trang", "price": 200000, "duration": 90}
            ],
            [
                {"name": "Cắt tóc VIP", "description": "Cắt tóc kèm dịch vụ VIP", "price": 100000, "duration": 45},
                {"name": "Cạo râu", "description": "Cạo râu kiểu Ý", "price": 50000, "duration": 20},
                {"name": "Massage mặt", "description": "Massage mặt thư giãn", "price": 80000, "duration": 30}
            ],
            [
                {"name": "Cắt tóc nữ", "description": "Cắt tóc nữ theo yêu cầu", "price": 100000, "duration": 60},
                {"name": "Nhuộm tóc", "description": "Nhuộm tóc màu thời trang", "price": 300000, "duration": 120},
                {"name": "Uốn tóc", "description": "Uốn tóc theo yêu cầu", "price": 350000, "duration": 150}
            ]
        ]
        
        for i, shop in enumerate(shops):
            for service_info in service_data[i]:
                service = Service(
                    name=service_info["name"],
                    description=service_info["description"],
                    price=service_info["price"],
                    duration=service_info["duration"],
                    shop_id=shop.id
                )
                db.session.add(service)
                services.append(service)
        
        db.session.commit()
        logger.info("Đã tạo dịch vụ cho các cửa hàng")
        
        # Tạo thợ cắt tóc cho mỗi cửa hàng
        barbers = []
        barber_data = [
            [
                {"name": "Nguyễn Văn Tùng", "experience": "5 năm", "specialization": "Tóc nam", "phone": "0912345671"},
                {"name": "Trần Văn Hải", "experience": "3 năm", "specialization": "Uốn và nhuộm", "phone": "0912345672"}
            ],
            [
                {"name": "Lê Thị Hương", "experience": "7 năm", "specialization": "Tóc nữ", "phone": "0912345673"},
                {"name": "Nguyễn Văn Dũng", "experience": "4 năm", "specialization": "Tóc nam", "phone": "0912345674"}
            ],
            [
                {"name": "Phạm Văn Tuấn", "experience": "3 năm", "specialization": "Tóc sinh viên", "phone": "0912345675"},
                {"name": "Nguyễn Thị Lan", "experience": "5 năm", "specialization": "Nhuộm tóc", "phone": "0912345676"}
            ],
            [
                {"name": "Trần Văn Hùng", "experience": "8 năm", "specialization": "Cắt tóc VIP", "phone": "0912345677"},
                {"name": "Lê Văn Đức", "experience": "6 năm", "specialization": "Massage", "phone": "0912345678"}
            ],
            [
                {"name": "Nguyễn Thị Mai", "experience": "10 năm", "specialization": "Tóc nữ", "phone": "0912345679"},
                {"name": "Trần Thị Hương", "experience": "7 năm", "specialization": "Uốn và nhuộm", "phone": "0912345680"}
            ]
        ]
        
        for i, shop in enumerate(shops):
            for barber_info in barber_data[i]:
                barber = Barber(
                    name=barber_info["name"],
                    phone=barber_info["phone"],
                    shop_id=shop.id
                )
                db.session.add(barber)
                barbers.append(barber)
        
        db.session.commit()
        logger.info("Đã tạo thợ cắt tóc cho các cửa hàng")
        
        # Tạo khuyến mãi cho mỗi cửa hàng
        promotions = []
        promotion_data = [
            {"name": "Khuyến mãi sinh viên", "description": "Giảm 10% cho sinh viên", "discount_percent": 10},
            {"name": "Khuyến mãi đầu tuần", "description": "Giảm 15% vào thứ 2, thứ 3", "discount_percent": 15},
            {"name": "Khuyến mãi sinh nhật", "description": "Giảm 20% trong ngày sinh nhật", "discount_percent": 20},
            {"name": "Khuyến mãi đôi bạn", "description": "Giảm 10% khi đi cùng bạn", "discount_percent": 10},
            {"name": "Khuyến mãi làm đẹp", "description": "Giảm 15% cho dịch vụ trọn gói", "discount_percent": 15}
        ]
        
        for i, shop in enumerate(shops):
            promotion = Promotion(
                name=promotion_data[i]["name"],
                description=promotion_data[i]["description"],
                discount_percent=promotion_data[i]["discount_percent"],
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=30),
                shop_id=shop.id
            )
            
            db.session.add(promotion)
            promotions.append(promotion)
        
        db.session.commit()
        logger.info("Đã tạo khuyến mãi cho các cửa hàng")
        
        # Tạo đánh giá cho mỗi cửa hàng
        reviews = []
        review_comments = [
            "Dịch vụ rất tốt, thợ nhiệt tình. Sẽ quay lại lần sau!",
            "Cắt tóc đẹp, giá cả hợp lý. Rất hài lòng!",
            "Thợ tay nghề cao, không gian sạch sẽ, thoáng mát."
        ]
        
        for shop in shops:
            # Mỗi cửa hàng có ít nhất 2 đánh giá
            for i, customer in enumerate(customers):
                if i < 2:  # Chỉ 2 khách hàng đầu tiên đánh giá mỗi cửa hàng
                    rating = random.randint(4, 5)
                    review = Review(
                        comment=review_comments[i],
                        rating=rating,
                        created_at=datetime.now() - timedelta(days=random.randint(1, 30)),
                        customer_id=customer.id,
                        shop_id=shop.id
                    )
                    
                    db.session.add(review)
                    reviews.append(review)
        
        db.session.commit()
        logger.info("Đã tạo đánh giá cho các cửa hàng")
        
        # Tạo lịch đặt cho mỗi khách hàng
        bookings = []
        for customer in customers:
            # Mỗi khách hàng đặt lịch ở 2 cửa hàng
            for shop in random.sample(shops, 2):
                service = random.choice([s for s in services if s.shop_id == shop.id])
                barber = random.choice([b for b in barbers if b.shop_id == shop.id])
                
                # Đặt lịch trong quá khứ (đã hoàn thành)
                past_date = datetime.now() - timedelta(days=random.randint(1, 30))
                past_booking = Booking(
                    customer_id=customer.id,
                    shop_id=shop.id,
                    service_id=service.id,
                    barber_id=barber.id,
                    booking_date=past_date.date(),
                    booking_time=time(random.randint(9, 18), 0),
                    status="completed",
                    notes="Đặt lịch tự động từ dữ liệu demo",
                    created_at=past_date - timedelta(days=2)
                )
                
                # Đặt lịch trong tương lai
                future_date = datetime.now() + timedelta(days=random.randint(1, 7))
                future_booking = Booking(
                    customer_id=customer.id,
                    shop_id=shop.id,
                    service_id=service.id,
                    barber_id=barber.id,
                    booking_date=future_date.date(),
                    booking_time=time(random.randint(9, 18), 0),
                    status="confirmed",
                    notes="Đặt lịch tự động từ dữ liệu demo",
                    created_at=datetime.now() - timedelta(days=1)
                )
                
                db.session.add_all([past_booking, future_booking])
                bookings.extend([past_booking, future_booking])
        
        db.session.commit()
        logger.info("Đã tạo lịch đặt cho các khách hàng")
        
        # Tạo yêu thích
        favorites = []
        for customer in customers:
            # Mỗi khách hàng yêu thích 2 cửa hàng
            for shop in random.sample(shops, 2):
                favorite = Favorite(
                    customer_id=customer.id,
                    shop_id=shop.id
                )
                
                db.session.add(favorite)
                favorites.append(favorite)
        
        db.session.commit()
        logger.info("Đã tạo yêu thích cho các khách hàng")
        
        logger.info("Tạo dữ liệu demo hoàn tất!")

if __name__ == "__main__":
    try:
        create_demo_data()
    except Exception as e:
        logger.error(f"Lỗi khi tạo dữ liệu demo: {e}")
        import traceback
        logger.error(traceback.format_exc())




