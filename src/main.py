# src/main.py
import sys
import traceback
from pathlib import Path

# src 폴더 경로 설정 (프로젝트 루트 기준)
sys.path.append(str(Path(__file__).resolve().parent.parent))

# 패키지 레벨(__init__.py)에서 노출된 클래스 임포트
from src.processors import BatchProcessor, BatchVisualizer
from src.utils import Log

# ==========================================
# 1. 글로벌 예외 핸들러 정의
# ==========================================
def global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    프로그램 내에서 잡히지 않은(Uncaught) 모든 예외를 여기서 처리합니다.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        Log.warning("사용자에 의해 작업이 중단되었습니다. (KeyboardInterrupt)")
        sys.exit(0)

    error_msg = f"{exc_type.__name__}: {exc_value}"
    Log.error(f"예기치 못한 오류로 프로그램이 종료됩니다.\n{'-'*60}")
    
    traceback_details = "".join(traceback.format_tb(exc_traceback))
    print(f"{Log.FAIL}{traceback_details}{error_msg}{Log.RESET}")
    print(f"{'-'*60}")

# 예외 훅 등록
sys.excepthook = global_exception_handler

# ==========================================
# 2. Main 실행
# ==========================================
def main():
    # ==========================================
    # [설정] 사용자 파라미터
    # ==========================================
    
    # 1. 면 병합 기능 사용 여부 (True/False) 
    # !!!!!!!!!!!!!!!!!!!!! 기본 False로 반드시 사용. True 조건 관련 개발은 되지 않음 !!!!!!!!!!!!!!!!!!!!!
    ENABLE_MERGE = False
    # 2. 병합 오차율 설정 (0.01 = 1%)
    # 분석 결과 추천값: 0.03 (3%)
    MERGE_TOLERANCE = 0.03

    # ==========================================
    
    # 설정값을 Processor에 전달
    processor = BatchProcessor(
        enable_merge=ENABLE_MERGE, 
        merge_tolerance=MERGE_TOLERANCE
    )
    processor.run()
    
    # 시각화 실행 (필요시 주석 해제)
    # visualizer = BatchVisualizer()
    # visualizer.run()

if __name__ == "__main__":
    main()
