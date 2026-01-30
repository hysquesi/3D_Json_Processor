# src/processors/converters/__init__.py
"""
Converters Sub-package
======================
Raw JSON 데이터를 입력받아 비즈니스 규칙에 따라 구조를 변환(Modify)하고,
형상 최적화(Optimization)를 거쳐 저장하는 로직을 담당합니다.

Modules:
--------
1. data_modifier.py (DataModifier)
   - JSON 데이터 구조 표준화 및 유효성 검사.
   - Longi 부재의 BackSide/FrontSide 형상 최적화 제어.

2. geometry_merger.py (GeometryMerger)
   - 인접 평면 병합 (Plane Merge).
   - [New] 흩어진 Vertex를 하나의 볼록 다각형으로 통합 (Convex Hull Merge).

3. batch_processor.py (BatchProcessor)
   - 입력 디렉토리 순회 및 파일 입출력(I/O) 관리.
   - 전체 변환 파이프라인(Modifier -> Saver) 실행 제어.
"""

from .data_modifier import DataModifier
from .batch_processor import BatchProcessor
from .geometry_merger import GeometryMerger

__all__ = [
    "DataModifier", 
    "BatchProcessor", 
    "GeometryMerger"
]