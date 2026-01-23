import re
from typing import Dict, Any
from src.utils import Log, log_lifecycle

class DataModifier:
    """
    Encapsulates data transformation logic.
    """

    def __init__(self):
        self.longi_pattern = re.compile(r"Longi_Bot_(\d+)")
        self.surface_pattern = re.compile(r"Surface_(\d+)_")
        self.longi_sub_prefix = re.compile(r"^Longi_Bot_(\d+)_")
        self.suffix_number_pattern = re.compile(r"_(\d+)$")

    @log_lifecycle
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        processed_data = {}
        skipped_count = 0

        for key, value in data.items():
            if not value:
                # Log.info(f"Skipping empty item: {key}") 
                skipped_count += 1
                continue

            if key.startswith("Longi"):
                self._process_longi_item(key, value, processed_data)
            else:
                self._process_plane_item(key, value, processed_data)
        
        if skipped_count > 0:
            Log.warning(f"Total skipped items in this file: {skipped_count}")

        return processed_data

    def _process_longi_item(self, old_key: str, value: Dict[str, Any], output_dict: Dict[str, Any]):
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
        match = self.surface_pattern.search(old_key)
        if match:
            raw_idx = match.group(1)
            idx_str = f"{int(raw_idx):03d}"
            new_key = f"Plane_{idx_str}"
        else:
            new_key = old_key
        output_dict[new_key] = value

    def _generate_longi_sub_key(self, old_sub_key: str, parent_idx_str: str) -> str:
        match = self.longi_sub_prefix.search(old_sub_key)
        if match:
            remainder = old_sub_key[match.end():]
        else:
            remainder = old_sub_key

        parts = remainder.split('_')
        name_parts = []
        for part in parts:
            if '-' in part:
                break
            name_parts.append(part)
        
        if not name_parts:
            core_name = remainder
        else:
            core_name = "_".join(name_parts)

        suffix_match = self.suffix_number_pattern.search(core_name)
        if suffix_match:
            num_part = suffix_match.group(1)
            base_name = core_name[:suffix_match.start()]
            final_suffix = f"{base_name}_{int(num_part):03d}"
        else:
            final_suffix = f"{core_name}_001"

        return f"Longi_{parent_idx_str}_{final_suffix}"