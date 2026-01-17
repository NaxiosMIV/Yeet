import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
EXPIRE_MINUTES = os.getenv("EXPIRE_MINUTES")

def create_access_token(data: dict):
    """유저 정보를 담은 JWT 생성"""
    to_encode = data.copy()
    # 만료 시간 설정
    expire = datetime.utcnow() + timedelta(minutes=int(EXPIRE_MINUTES)) 
    to_encode.update({"exp": expire})
    
    # 암호화하여 토큰 생성
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    """토큰을 해독하여 유저 정보 추출"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # {"user_uuid": "...", "exp": ...}
    except jwt.ExpiredSignatureError:
        return "Expired" # 만료됨
    except jwt.InvalidTokenError:
        return "Invalid" # 유효하지 않음