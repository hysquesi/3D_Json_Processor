# src/config.py
from pathlib import Path

class Config:
    """프로젝트 전체에서 사용되는 설정 및 상수 정의"""
    
    # 프로젝트 루트 경로 계산 (이 파일의 위치 기준)
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    # 데이터 입출력 경로
    INPUT_DIR = BASE_DIR / "data" / "input"
    OUTPUT_DIR = BASE_DIR / "data" / "output"
    
    # 처리 대상 파일 패턴
    FILE_PATTERN = "*.json"
    
    # 인코딩 설정
    ENCODING = "utf-8"