# src/utils/file_manager.py

import json
import re
from pathlib import Path
from typing import Dict, Any
from src.utils.logger import Log  

class JsonHandler:
    @staticmethod
    def read_json(filepath: Path) -> Dict[str, Any]:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            content = re.sub(r',\s*}', '}', content)
            content = re.sub(r',\s*]', ']', content)
            return json.loads(content)
        except json.JSONDecodeError as e:
            Log.error(f"JSON parsing failed ({filepath.name}): {e}")
            return {}
        except Exception as e:
            Log.error(f"Unexpected error reading ({filepath.name}): {e}")
            return {}

    @staticmethod
    def save_json(filepath: Path, data: Dict[str, Any]) -> None:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            Log.success(f"Saved: {filepath.name}")
        except Exception as e:
            Log.error(f"Failed to save ({filepath.name}): {e}")