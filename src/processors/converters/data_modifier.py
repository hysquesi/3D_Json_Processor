import re
from typing import Dict, Any
from src.utils import Log, log_lifecycle
from .geometry_merger import GeometryMerger

class DataModifier:
    """
    Encapsulates data transformation logic.
    - Coordinates conversion to Unity Space (-y, z, x).
    - Merges coplanar 'Plane' faces using GeometryMerger (controlled by enable_merge flag).
    """

    def __init__(self, enable_merge: bool = True, merge_tolerance: float = 0.01):
        self.longi_pattern = re.compile(r"Longi_Bot_(\d+)")
        self.surface_pattern = re.compile(r"Surface_(\d+)_")
        self.longi_sub_prefix = re.compile(r"^Longi_Bot_(\d+)_")
        self.suffix_number_pattern = re.compile(r"_(\d+)$")
        
        self.enable_merge = enable_merge
        
        # [수정] 전달받은 오차율로 GeometryMerger 초기화
        # Normal 허용오차(각도)와 Distance 허용오차(거리)에 동일하게 적용하거나,
        # 필요하다면 분리해서 관리할 수도 있습니다. 여기서는 동일하게 적용합니다.
        self.merger = GeometryMerger(
            norm_tol=merge_tolerance, 
            dist_tol=merge_tolerance
        )

    @log_lifecycle
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        processed_data = {}
        plane_candidates = {}
        longi_items = {}
        skipped_count = 0

        for key, value in data.items():
            if not value:
                skipped_count += 1
                continue

            transformed_val = self._transform_recursive(value)

            if key.startswith("Longi"):
                longi_items[key] = transformed_val
            else:
                plane_candidates[key] = transformed_val
        
        # 1. Longi 계열 처리
        for key, val in longi_items.items():
            self._process_longi_item(key, val, processed_data)

        # 2. Plane 계열 처리
        if plane_candidates:
            if self.enable_merge:
                # 설정된 오차율이 적용된 merger 사용
                Log.info(f"Merging enabled (Tol: {self.merger.norm_tol:.2f}): Processing plane groups...")
                merged_planes = self.merger.merge_planes(plane_candidates)
                processed_data.update(merged_planes)
            else:
                Log.info("Merging disabled: Skipping geometry merge.")
                for key, val in plane_candidates.items():
                    self._process_plane_item(key, val, processed_data)

        if skipped_count > 0:
            Log.warning(f"Total skipped items in this file: {skipped_count}")

        return processed_data

    def _process_longi_item(self, old_key: str, value: Dict[str, Any], output_dict: Dict[str, Any]):
        """Longi 항목의 키 이름을 표준화합니다."""
        match = self.longi_pattern.search(old_key)
        if match:
            raw_idx = match.group(1)
            idx_str = f"{int(raw_idx):03d}" 
            new_key = f"Longi_{idx_str}"
        else:
            output_dict[old_key] = value
            return

        new_value = {}
        if isinstance(value, dict):
            for sub_key, sub_content in value.items():
                new_sub_key = self._generate_longi_sub_key(sub_key, idx_str)
                new_value[new_sub_key] = sub_content
        else:
            new_value = value

        output_dict[new_key] = new_value

    def _process_plane_item(self, old_key: str, value: Any, output_dict: Dict[str, Any]):
        """
        병합 옵션이 꺼져있을 때 사용하는 Plane 항목 단순 키 변경 메서드.
        GeometryMerger를 사용하지 않을 경우 이 로직을 따릅니다.
        """
        match = self.surface_pattern.search(old_key)
        if match:
            raw_idx = match.group(1)
            idx_str = f"{int(raw_idx):03d}"
            new_key = f"Plane_{idx_str}"
        else:
            new_key = old_key
        
        output_dict[new_key] = value

    def _generate_longi_sub_key(self, old_sub_key: str, parent_idx_str: str) -> str:
        """Longi 하위 항목의 키 이름을 생성합니다."""
        match = self.longi_sub_prefix.search(old_sub_key)
        if match:
            remainder = old_sub_key[match.end():]
        else:
            remainder = old_sub_key

        parts = remainder.split('_')
        name_parts = []
        for part in parts:
            if '-' in part: break
            name_parts.append(part)
        
        core_name = "_".join(name_parts) if name_parts else remainder
        
        suffix_match = self.suffix_number_pattern.search(core_name)
        if suffix_match:
            num_part = suffix_match.group(1)
            base_name = core_name[:suffix_match.start()]
            final_suffix = f"{base_name}_{int(num_part):03d}"
        else:
            final_suffix = f"{core_name}_001"

        return f"Longi_{parent_idx_str}_{final_suffix}"

    def _transform_recursive(self, data: Any) -> Any:
        """
        데이터를 재귀적으로 순회하며 좌표를 Unity 좌표계로 변환합니다.
        Transformation: (x, y, z) -> (-y, z, x)
        """
        if isinstance(data, dict):
            new_data = {}
            for k, v in data.items():
                # 키에 'vertex'가 포함되어 있고, 값이 좌표 형태(dict)인 경우
                if "vertex" in k.lower() and isinstance(v, dict):
                    try:
                        x = float(v.get('x', 0))
                        y = float(v.get('y', 0))
                        z = float(v.get('z', 0))
                        
                        # Unity 좌표계 변환 적용 (-y, z, x)
                        new_data[k] = {
                            'x': -y, 
                            'y': z, 
                            'z': x
                        }
                    except (ValueError, TypeError):
                        new_data[k] = v
                else:
                    new_data[k] = self._transform_recursive(v)
            return new_data
            
        elif isinstance(data, list):
            return [self._transform_recursive(item) for item in data]
            
        return data