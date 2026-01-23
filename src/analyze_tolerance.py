import sys
from pathlib import Path
import copy

# 프로젝트 루트 경로 설정
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.utils import JsonHandler, Log
from src.processors.converters.data_modifier import DataModifier
from src.processors.converters.geometry_merger import GeometryMerger

def analyze_tolerance_impact():
    """
    1% ~ 10% 오차율 변화에 따른 병합 효율성을 분석합니다.
    """
    Log.section("Tolerance Analysis Started")
    
    # 1. 입력 파일 로드 (첫 번째 파일만 샘플로 사용)
    input_files = list(Config.INPUT_DIR.glob(Config.FILE_PATTERN))
    if not input_files:
        Log.warning("No input files found.")
        return
    
    target_file = input_files[0] # 테스트용으로 첫 번째 파일 선택
    Log.info(f"Analyzing File: {target_file.name}")
    
    handler = JsonHandler()
    raw_data = handler.read_json(target_file)
    
    # 2. 데이터 전처리 (좌표 변환 등) - DataModifier 활용
    # 병합은 끄고 순수 변환된 데이터만 가져옴
    modifier = DataModifier(enable_merge=False)
    processed_data = modifier.process(raw_data)
    
    # Plane 계열 데이터만 추출 (병합 대상)
    plane_data = {k: v for k, v in processed_data.items() if k.startswith("Plane")}
    initial_count = len(plane_data)
    
    print(f"\n[Initial Status] Total Plane Faces: {initial_count}")
    print(f"{'-'*60}")
    print(f"{'Tolerance':<15} | {'Merged Faces':<15} | {'Reduction Rate':<15} | {'Status'}")
    print(f"{'-'*60}")

    # 3. 오차율 1% ~ 10% 루프 실행
    # 0.01 (1%) ~ 0.10 (10%)
    best_tolerance = 0.01
    min_faces = initial_count

    for i in range(1, 11):
        tol = i / 100.0  # 0.01, 0.02, ... 0.10
        
        # 해당 오차율로 Merger 생성
        merger = GeometryMerger(norm_tol=tol, dist_tol=tol)
        
        # 원본 데이터 보호를 위해 deepcopy 사용하거나 매번 새로 추출
        # 여기서는 merger가 원본을 훼손하지 않는다고 가정하고 전달
        merged_result = merger.merge_planes(plane_data)
        
        final_count = len(merged_result)
        reduction = ((initial_count - final_count) / initial_count) * 100
        
        print(f"{tol*100:>4.0f}% ({tol:.2f})    | {final_count:>13}   | {reduction:>13.1f}%   | Done")
        
        if final_count < min_faces:
            min_faces = final_count
            best_tolerance = tol

    print(f"{'-'*60}")
    Log.success(f"Analysis Complete. Recommended Tolerance: {best_tolerance*100:.0f}% ({min_faces} faces)")

if __name__ == "__main__":
    analyze_tolerance_impact()