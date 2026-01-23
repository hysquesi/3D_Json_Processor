"""
Converters Sub-package
======================
Raw JSON 데이터를 입력받아 비즈니스 규칙에 따라 구조를 변환(Modify)하고
저장하는 로직을 담당합니다.

Modules:
--------
- data_modifier.py: 개별 JSON 데이터의 키/구조 변경 로직 (DataModifier)
- batch_processor.py: 디렉토리 순회 및 전체 변환 공정 제어 (BatchProcessor)
"""

# 파일명 변경 반영: modifier -> data_modifier, batch_runner -> batch_processor
from .data_modifier import DataModifier
from .batch_processor import BatchProcessor

__all__ = ["DataModifier", "BatchProcessor"]