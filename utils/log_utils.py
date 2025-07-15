import logging

def get_logger(name: str) -> logging.Logger:
    """
    프로젝트 전역 로깅 설정 기반으로 name에 해당하는 Logger 반환
    (root logger의 핸들러/포맷을 그대로 따름)
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 이미 핸들러가 설정돼 있다면 중복 추가 방지
    if not logger.handlers:
        logger.propagate = True  # root logger 설정 재사용
    return logger