import uuid
import random

def create_guest_user(guest_id: str = None):
    # guest_id가 없으면 새로 생성
    if not guest_id or guest_id == "null" or guest_id == "undefined":
        guest_id = str(uuid.uuid4())
    
    # 익명 이름 생성 (예: Guest_123456)
    guest_name = f"Guest_{random.randint(1000, 9999)}"
    
    return {
        "status": "success",
        "user": {
            "social_id": guest_id,
            "email": None,
            "name": guest_name,
            "picture": None,
            "provider": "guest"
        }
    }