from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
import string

app = FastAPI()

# Cho phép Frontend gọi API mà không bị chặn lỗi CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database tạm thời lưu trong RAM (Khi chạy thực tế sẽ thay bằng file hoặc DB thực)
url_database = {}

class URLItem(BaseModel):
    url: str

def generate_short_code():
    """Tạo ngẫu nhiên một chuỗi 6 ký tự"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(6))

@app.post("/shorten")
async def shorten_url(item: URLItem):
    # Kiểm tra xem link có bắt đầu bằng http không
    if not item.url.startswith("http://") and not item.url.startswith("https://"):
        item.url = "https://" + item.url
        
    short_code = generate_short_code()
    
    # Đảm bảo mã không bị trùng
    while short_code in url_database:
        short_code = generate_short_code()
        
    url_database[short_code] = item.url
    return {"short_code": short_code, "long_url": item.url}

@app.get("/{short_code}")
async def redirect_to_url(short_code: str):
    long_url = url_database.get(short_code)
    if long_url:
        return RedirectResponse(url=long_url)
    raise HTTPException(status_code=404, detail="Link không tồn tại")