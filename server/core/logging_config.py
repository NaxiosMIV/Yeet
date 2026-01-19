import logging
import sys

# 로깅 형식 설정
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def get_logger(name: str):
    """
    모듈별 로거를 반환합니다.
    """
    return logging.getLogger(name)
