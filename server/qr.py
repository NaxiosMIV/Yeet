import qrcode
import socket

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

ip = get_local_ip()
url = f"http://{ip}:5500"

img = qrcode.make(url)
img.save("join_game_qr.png")

print("Scan this QR to join:", url)
