"""
Processors Package
==================
데이터 처리 파이프라인의 핵심 비즈니스 로직을 제공하는 패키지입니다.
크게 '데이터 변환(Converters)'과 '시각화(Visualizers)' 두 가지 서브 패키지로 구성됩니다.

Sub-packages:
-------------
1. converters
   - JSON 데이터를 읽어 구조를 변경하고 저장하는 배치 작업을 담당합니다.
   - 주요 모듈: batch_processor, data_modifier

2. visualizers
   - 처리된 결과 데이터를 3D Wireframe 형태로 시각화합니다.
   - 주요 모듈: batch_visualizer, mesh_visualizer
"""

# 하위 패키지에서 주요 클래스를 끌어올려(Re-export) 외부에서 접근하기 쉽게 만듭니다.
# 사용 예: from src.processors import BatchProcessor, BatchVisualizer

from .converters import BatchProcessor, DataModifier
from .visualizers import BatchVisualizer, MeshVisualizer

__all__ = [
    "BatchProcessor",
    "DataModifier",
    "BatchVisualizer",
    "MeshVisualizer"
]