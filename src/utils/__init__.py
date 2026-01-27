# src/utils/__init__.py
"""
Utilities Package
=================
프로젝트 전반에서 사용되는 공통 보조 기능(Cross-cutting Concerns)을 제공하는 패키지입니다.
비즈니스 로직(DataModifier 등)과는 독립적으로 동작합니다.

포함된 모듈 (Modules):
----------------------
1. file_manager.py
   - JsonHandler: JSON 파일 읽기/쓰기, 파싱 에러 처리, 후행 쉼표(Trailing Comma) 자동 정제.

2. logger.py
   - Log: ANSI Escape Code를 활용한 컬러 콘솔 로깅 (Info, Success, Error, Warning, Trace 등).

3. decorators.py
   - measure_time: 함수 실행 시간 측정 및 성능 로깅.
   - log_lifecycle: 함수 호출의 시작과 끝을 추적(Trace)하여 로깅.
"""

# 패키지 레벨에서 바로 접근 가능하도록 주요 클래스/함수 노출 (Convenience Imports)
from .file_manager import JsonHandler
from .logger import Log
from .decorators import measure_time, log_lifecycle

# 'from src.utils import *' 사용 시 노출될 항목 정의
__all__ = [
    "JsonHandler",
    "Log", 
    "measure_time", 
    "log_lifecycle"
]