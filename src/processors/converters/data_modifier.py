# src/processors/converters/data_modifier.py
import re
from typing import Dict, Any, Tuple
from collections import defaultdict
from src.utils import Log, log_lifecycle
from .geometry_merger import GeometryMerger

class DataModifier:
    """
    데이터 변환, 표준화, 검증 및 형상 최적화를 수행합니다.
    
    [Modification Fix]
    - 서브 키 파싱 로직 개선: Longi ID 이후의 문자열에서 파트 타입(Bot, Right 등)을 검색하여
      접두사(Prefix)로 인한 오분류 및 데이터 소실 방지.
    """

    def __init__(self, enable_merge: bool = True, merge_tolerance: float = 0.01):
        # Longi ID 추출 (Longi_Bot_001 -> 001)
        self.longi_id_pattern = re.compile(r"Longi_.*?(\d+)") 
        
        # 서브 파트 식별용 (Bot, Right, Left, BackSide, Flange 등)
        self.part_type_pattern = re.compile(r"_(Bot|Right|Left|BackSide|Flange)(?:_|$)", re.IGNORECASE)
        
        self.enable_merge = enable_merge
        self.merger = GeometryMerger(norm_tol=merge_tolerance, dist_tol=merge_tolerance)

    @log_lifecycle
    def process(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        데이터 처리 메인 파이프라인.
        Returns: (valid_data, deleted_data)
        """
        # [Step 1] 전처리: 좌표 변환 및 평탄화 그룹핑
        grouped_longis, plane_candidates = self._transform_and_aggregate(data)
        
        valid_data = {}
        deleted_data = {}

        # [Step 2] Longi 계열 후처리 (검증 및 최적화)
        for main_key, sub_items in grouped_longis.items():
            # 2-1. 검증 (Rule 1 & 2)
            is_valid, reason = self._validate_longi_group(main_key, sub_items)
            
            if is_valid:
                # 2-2. 최적화 (Rule 3: BackSide 병합)
                optimized_items = self._optimize_longi_geometry(main_key, sub_items)
                valid_data[main_key] = optimized_items
            else:
                Log.info(f"Filtered '{main_key}': {reason}")
                deleted_data[main_key] = sub_items

        # [Step 3] Plane 계열 처리
        if plane_candidates:
            if self.enable_merge:
                Log.info(f"Merging Plane group (Count: {len(plane_candidates)})...")
                merged_planes = self.merger.merge_planes(plane_candidates)
                valid_data.update(merged_planes)
            else:
                for key, val in plane_candidates.items():
                    self._process_plane_item(key, val, valid_data)

        return valid_data, deleted_data

    def _transform_and_aggregate(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        longi_groups = defaultdict(dict)
        plane_candidates = {}

        for key, value in data.items():
            if not value: continue
            
            transformed_val = self._transform_recursive(value)

            if key.startswith("Longi"):
                # ID 추출
                match = self.longi_id_pattern.search(key)
                if match:
                    raw_idx = match.group(1)
                    idx_str = f"{int(raw_idx):03d}"
                    main_key = f"Longi_{idx_str}"
                    
                    # [핵심] 구조 평탄화 (Flattening)
                    if self._is_container(transformed_val):
                        for sub_k, sub_v in transformed_val.items():
                            # 서브 키 표준화 (Right_... -> Longi_001_Right_001)
                            std_sub_key = self._generate_standard_sub_key(sub_k, idx_str)
                            longi_groups[main_key][std_sub_key] = sub_v
                    else:
                        std_sub_key = self._generate_standard_sub_key(key, idx_str)
                        longi_groups[main_key][std_sub_key] = transformed_val
                else:
                    plane_candidates[key] = transformed_val
            else:
                plane_candidates[key] = transformed_val
        
        return longi_groups, plane_candidates

    def _is_container(self, value: Any) -> bool:
        if not isinstance(value, dict): return False
        if any("Vertex" in k for k in value.keys()): return False
        return True

    def _generate_standard_sub_key(self, raw_key: str, parent_idx: str) -> str:
        """
        [수정됨] Longi ID 이후의 문자열에서 파트 타입을 검색하여 표준 키 생성.
        """
        # 1. ID 위치 찾기 (Longi_Bot_1... 에서 '1'의 위치)
        id_match = self.longi_id_pattern.search(raw_key)
        
        search_start_pos = 0
        if id_match:
            search_start_pos = id_match.end() # ID 숫자 뒤부터 검색 시작
            
        target_substring = raw_key[search_start_pos:]
        
        # 2. 파트 타입 식별 (ID 뒤쪽 문자열에서 검색)
        match = self.part_type_pattern.search(target_substring)
        part_type = match.group(1) if match else "Part"
        
        # BackSide_Flange 예외 처리
        if "Flange" in target_substring and "BackSide" in target_substring:
             part_type = "BackSide_Flange"

        # 3. 순번 추출 (타입 뒤에 나오는 숫자)
        sub_idx = "001"
        if match:
            post_part = target_substring[match.end():]
            num_match = re.search(r"^.*?(\d+)", post_part)
            if num_match:
                sub_idx = f"{int(num_match.group(1)):03d}"
        
        # 4. 이름 포맷팅
        formatted_type = part_type
        if part_type.lower() == "right": formatted_type = "Right"
        elif part_type.lower() == "left": formatted_type = "Left"
        elif part_type.lower() == "bot": formatted_type = "Bot"
        elif part_type.lower() == "backside": formatted_type = "BackSide"
        
        return f"Longi_{parent_idx}_{formatted_type}_{sub_idx}"

    def _validate_longi_group(self, key: str, sub_items: Dict[str, Any]) -> Tuple[bool, str]:
        sub_keys = sub_items.keys()
        
        right_count = sum(1 for k in sub_keys if "_Right_" in k)
        left_count = sum(1 for k in sub_keys if "_Left_" in k)
        
        if right_count >= 3 or left_count >= 3:
            return False, f"Complex Shape (Right: {right_count}, Left: {left_count})"

        has_bot = any("_Bot_" in k for k in sub_keys)
        has_backside = any("_BackSide_" in k for k in sub_keys)
        
        if not (has_bot and has_backside):
            missing = []
            if not has_bot: missing.append("Bot")
            if not has_backside: missing.append("BackSide")
            return False, f"Missing Components ({', '.join(missing)})"

        return True, ""

    def _optimize_longi_geometry(self, longi_key: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """BackSide 평면 병합 (Rule 3)"""
        if not self.enable_merge:
            return data

        backside_candidates = {}
        other_parts = {}
        
        # Flange가 아닌 순수 BackSide만 추출
        for k, v in data.items():
            if "_BackSide_" in k and "_Flange_" not in k:
                backside_candidates[k] = v
            else:
                other_parts[k] = v # Right, Left, Bot 등은 여기로 보존됨
        
        if len(backside_candidates) < 2:
            return data

        merged_results = self.merger.merge_planes(backside_candidates)
        
        final_data = other_parts.copy()
        
        idx_match = re.search(r"(\d+)$", longi_key)
        idx_str = idx_match.group(1) if idx_match else "000"
        
        sorted_merged_keys = sorted(merged_results.keys())
        for i, m_key in enumerate(sorted_merged_keys):
            new_sub_key = f"Longi_{idx_str}_BackSide_{i+1:03d}"
            final_data[new_sub_key] = merged_results[m_key]

        return final_data

    def _process_plane_item(self, old_key: str, value: Any, output_dict: Dict[str, Any]):
        surface_pattern = re.compile(r"Surface_(\d+)_")
        match = surface_pattern.search(old_key)
        if match:
            new_key = f"Plane_{int(match.group(1)):03d}"
        else:
            new_key = old_key
        output_dict[new_key] = value

    def _transform_recursive(self, data: Any) -> Any:
        if isinstance(data, dict):
            new_data = {}
            for k, v in data.items():
                if "vertex" in k.lower() and isinstance(v, dict):
                    try:
                        x = float(v.get('x', 0))
                        y = float(v.get('y', 0))
                        z = float(v.get('z', 0))
                        new_data[k] = {'x': -y, 'y': z, 'z': x}
                    except (ValueError, TypeError):
                        new_data[k] = v
                else:
                    new_data[k] = self._transform_recursive(v)
            return new_data
        elif isinstance(data, list):
            return [self._transform_recursive(item) for item in data]
        return data