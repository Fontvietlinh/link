import os
import random
import string

1

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
# 1. Cấu hình kết nối Cơ sở dữ liệu đám mây
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local_test.db")
# Khắc phục tương thích đường dẫn PostgreSQL trên một số nền tảng đám mây
if DATABASE_URL.startswith("postgres://"):
DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
# 2. Định nghĩa cấu trúc bảng dữ liệu lưu trữ liên kết
class URLMapping(Base):
__tablename__ = "url_mappings"
id = Column(Integer, primary_key=True, index=True)
long_url = Column(String, nullable=False)
short_code = Column(String, unique=True, index=True, nullable=False)
# Tự động khởi tạo cấu trúc bảng trên Cloud Database khi ứng dụng chạy
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Cloud URL Shortener API")
# Cấu hình CORS để cho phép Frontend gọi API an toàn từ mọi tên miền công cộng
app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)
class ShortenRequest(BaseModel):
url: str
def get_db_session():
db = SessionLocal()
try:
yield db
finally:
db.close()

2

def generate_secure_code(length=6):
chars = string.ascii_letters + string.digits
return ''.join(random.choice(chars) for _ in range(length))
# API endpoint đảm nhận việc sinh mã ngắn và lưu trữ vào database
@app.post("/shorten")
async def shorten_url(request: ShortenRequest, db: Session = Depends(get_db_session)):
target_url = request.url.strip()
if not target_url.startswith("http://") and not target_url.startswith("https://"):
target_url = "https://" + target_url
# Kiểm tra xem liên kết này đã tồn tại trong hệ thống chưa
existing_record = db.query(URLMapping).filter(URLMapping.long_url ==
target_url).first()
if existing_record:
return {"short_code": existing_record.short_code, "status": "exists"}
# Sinh mã ngẫu nhiên và kiểm tra trùng lặp mã khóa
short_code = generate_secure_code()
while db.query(URLMapping).filter(URLMapping.short_code == short_code).first():
short_code = generate_secure_code()
# Ghi dữ liệu mới vào Cloud Database
new_mapping = URLMapping(long_url=target_url, short_code=short_code)
db.add(new_mapping)
db.commit()
db.refresh(new_mapping)
return {"short_code": short_code, "status": "created"}
# API endpoint xử lý tác vụ điều hướng (Redirect) khi truy cập link ngắn
@app.get("/{short_code}")
async def redirect_to_original(short_code: str, db: Session =
Depends(get_db_session)):
mapping = db.query(URLMapping).filter(URLMapping.short_code == short_code).first()
if mapping:
return RedirectResponse(url=mapping.long_url, status_code=302)
raise HTTPException(status_code=404, detail="Đường dẫn rút gọn không tồn tại trên
hệ thống.")
