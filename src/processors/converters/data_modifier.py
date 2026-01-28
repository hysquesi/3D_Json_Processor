# src/processors/converters/data_modifier.py
import re
from typing import Dict, Any, Tuple
from collections import defaultdict
from src.utils import Log, log_lifecycle
from .geometry_merger import GeometryMerger

class DataModifier:
    """
    데이터 변환, 표준화, 검증 및 형상 최적화를 수행합니다.
    """

    def __init__(self, enable_merge: bool = True, merge_tolerance: float = 0.01):
        self.longi_id_pattern = re.compile(r"Longi_.*?(\d+)") 
        # [수정 1] FrontSide를 정규식에 추가하여 'Part'가 아닌 명시적 타입으로 인식하게 함
        self.part_type_pattern = re.compile(r"_(Bot|Right|Left|BackSide|Flange|FrontSide)(?:_|$)", re.IGNORECASE)
        
        self.enable_merge = enable_merge
        self.merger = GeometryMerger(norm_tol=merge_tolerance, dist_tol=merge_tolerance)

    @log_lifecycle
    def process(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        # [Step 1] 전처리
        grouped_longis, plane_candidates = self._transform_and_aggregate(data)
        
        valid_data = {}
        deleted_data = {}

        # [Step 2] Longi 계열 후처리
        for main_key, sub_items in grouped_longis.items():
            is_valid, reason = self._validate_longi_group(main_key, sub_items)
            
            if is_valid:
                # 2-2. 최적화 (BackSide/FrontSide 병합 로직 적용)
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

    # ... (중략: _transform_and_aggregate, _get_unique_key, _is_container 메소드는 기존과 동일) ...
    def _transform_and_aggregate(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        longi_groups = defaultdict(dict)
        plane_candidates = {}

        for key, value in data.items():
            if not value: continue
            
            transformed_val = self._transform_recursive(value)

            if key.startswith("Longi"):
                match = self.longi_id_pattern.search(key)
                if match:
                    raw_idx = match.group(1)
                    idx_str = f"{int(raw_idx):03d}"
                    main_key = f"Longi_{idx_str}"
                    
                    if self._is_container(transformed_val):
                        for sub_k, sub_v in transformed_val.items():
                            std_sub_key = self._generate_standard_sub_key(sub_k, idx_str)
                            unique_key = self._get_unique_key(longi_groups[main_key], std_sub_key)
                            longi_groups[main_key][unique_key] = sub_v
                    else:
                        std_sub_key = self._generate_standard_sub_key(key, idx_str)
                        unique_key = self._get_unique_key(longi_groups[main_key], std_sub_key)
                        longi_groups[main_key][unique_key] = transformed_val
                else:
                    plane_candidates[key] = transformed_val
            else:
                plane_candidates[key] = transformed_val
        
        return longi_groups, plane_candidates

    def _get_unique_key(self, container: Dict[str, Any], base_key: str) -> str:
        if base_key not in container:
            return base_key

        match = re.match(r"^(Longi_\d+_[A-Za-z]+_)(\d+)(.*)$", base_key)
        if match:
            prefix = match.group(1)
            current_num = int(match.group(2))
            suffix = match.group(3)
            while True:
                current_num += 1
                new_key = f"{prefix}{current_num:03d}{suffix}"
                if new_key not in container:
                    return new_key
        
        dup_count = 1
        new_key = f"{base_key}_dup_{dup_count}"
        while new_key in container:
            dup_count += 1
            new_key = f"{base_key}_dup_{dup_count}"
        return new_key

    def _is_container(self, value: Any) -> bool:
        if not isinstance(value, dict): return False
        if any("Vertex" in k for k in value.keys()): return False
        return True

    def _generate_standard_sub_key(self, raw_key: str, parent_idx: str) -> str:
        id_match = self.longi_id_pattern.search(raw_key)
        search_start_pos = 0
        if id_match:
            search_start_pos = id_match.end()
            
        target_substring = raw_key[search_start_pos:]
        
        # [수정 1의 효과] FrontSide가 포함되어 있으면 match가 성공함
        match = self.part_type_pattern.search(target_substring)
        part_type = match.group(1) if match else "Part"
        
        sub_idx = "001"
        if match:
            post_part = target_substring[match.end():]
            strict_num_match = re.match(r"^[:_]?(\d+)(?:_|$)", post_part)
            if strict_num_match:
                sub_idx = f"{int(strict_num_match.group(1)):03d}"
        
        # [수정 2] FrontSide 포맷팅 추가
        formatted_type = part_type
        if part_type.lower() == "right": formatted_type = "Right"
        elif part_type.lower() == "left": formatted_type = "Left"
        elif part_type.lower() == "bot": formatted_type = "Bot"
        elif part_type.lower() == "backside": formatted_type = "BackSide"
        elif part_type.lower() == "frontside": formatted_type = "FrontSide"
        
        base_key = f"Longi_{parent_idx}_{formatted_type}_{sub_idx}"

        # [기존 로직 유지] FrontSide_Flange_DownSide의 경우:
        # 1. part_type='FrontSide' -> base_key='Longi_XXX_FrontSide_XXX'
        # 2. "flange" in target -> base_key += '_Flange'
        # 3. "downside" in target -> base_key += '_DownSide'
        # 결과: Longi_XXX_FrontSide_XXX_Flange_DownSide (정보 보존 완료)
        target_lower = target_substring.lower()
        if "flange" in target_lower and formatted_type != "Flange":
            base_key += "_Flange"
        
        if "upside" in target_lower:
            base_key += "_UpSide"
        elif "downside" in target_lower:
            base_key += "_DownSide"
        
        return base_key

    def _validate_longi_group(self, key: str, sub_items: Dict[str, Any]) -> Tuple[bool, str]:
        sub_keys = sub_items.keys()
        
        right_count = sum(1 for k in sub_keys if "_Right_" in k and "_Flange" not in k)
        left_count = sum(1 for k in sub_keys if "_Left_" in k and "_Flange" not in k)
        
        if right_count >= 3 or left_count >= 3:
            return False, f"Complex Shape (Right: {right_count}, Left: {left_count})"

        has_bot = any("_Bot_" in k for k in sub_keys)
        has_backside = any("_BackSide_" in k for k in sub_keys)
        # [수정 3] FrontSide도 Web(수직 부재) 역할을 할 수 있으므로 유효성 검사 조건에 추가
        has_frontside = any("_FrontSide_" in k for k in sub_keys)
        
        # Bot은 필수, 수직 부재는 BackSide 혹은 FrontSide 중 하나만 있어도 통과
        if not (has_bot and (has_backside or has_frontside)):
            missing = []
            if not has_bot: missing.append("Bot")
            if not (has_backside or has_frontside): missing.append("BackSide/FrontSide")
            return False, f"Missing Components ({', '.join(missing)})"

        return True, ""

    def _optimize_longi_geometry(self, longi_key: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """BackSide 및 FrontSide 평면 병합 (Convex Hull 적용)"""
        # [수정 4] BackSide 뿐만 아니라 FrontSide도 병합 대상에 포함 (필요 시)
        merge_candidates = {}
        other_parts = {}
        
        # BackSide 또는 FrontSide를 병합 후보군으로 식별
        for k, v in data.items():
            is_back = ("_BackSide_" in k and "_Flange" not in k)
            is_front = ("_FrontSide_" in k and "_Flange" not in k)
            
            if is_back or is_front:
                merge_candidates[k] = v
            else:
                other_parts[k] = v 
        
        if len(merge_candidates) < 2:
            return data

        # Convex Hull 병합 수행 (BackSide와 FrontSide가 섞여 있으면 하나의 면으로 병합 시도됨)
        # 만약 BackSide와 FrontSide가 서로 다른 평면이라면 GeometryMerger 내부에서 SVD/Normal 체크 시
        # 이상적인 결과가 안 나올 수 있으나, 일반적으로는 하나의 큰 Web으로 간주하여 처리.
        merged_results = self.merger.merge_by_convex_hull(merge_candidates)
        
        final_data = other_parts.copy()
        idx_match = re.search(r"(\d+)$", longi_key)
        idx_str = idx_match.group(1) if idx_match else "000"
        
        sorted_merged_keys = sorted(merged_results.keys())
        for i, m_key in enumerate(sorted_merged_keys):
            # 병합된 결과는 대표적으로 'Web' 또는 'BackSide'로 명명
            new_sub_key = f"Longi_{idx_str}_BackSide_{i+1:03d}"
            final_data[new_sub_key] = merged_results[m_key]

        return final_data

    # ... (이하 메소드 기존 동일) ...
    def _process_plane_item(self, old_key: str, value: Any, output_dict: Dict[str, Any]):
        match = re.search(r"Standard_Surface_(\d+)", old_key, re.IGNORECASE)
        if match:
            new_key = f"Plane_Standard_{int(match.group(1)):03d}"
            output_dict[new_key] = value
            return

        match = re.search(r"Stiffener_Surface_(\d+)", old_key, re.IGNORECASE)
        if match:
            new_key = f"Plane_Stiffener_{int(match.group(1)):03d}"
            output_dict[new_key] = value
            return

        match = re.search(r"Surface_(\d+)", old_key, re.IGNORECASE)
        if match:
            new_key = f"Plane_{int(match.group(1)):03d}"
            output_dict[new_key] = value
            return

        output_dict[old_key] = value

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