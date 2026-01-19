import qrcode
from core.logging_config import get_logger

logger = get_logger(__name__)
import socket
from core.config import PORT, BASE_DIR

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

def generate_qr(output_name="join_game_qr.png"):
    ip = get_local_ip()
    url = f"http://{ip}:{PORT}"
    
    img = qrcode.make(url)
    save_path = BASE_DIR / output_name
    img.save(save_path)
    
    logger.info(f"QR code generated for {url}")
    logger.info(f"Saved to: {save_path}")
    return url

if __name__ == "__main__":
    generate_qr()
