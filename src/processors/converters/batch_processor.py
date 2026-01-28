# src/processors/converters/batch_processor.py
from pathlib import Path
from src.config import Config
from src.utils import JsonHandler, measure_time, Log
from .data_modifier import DataModifier

class BatchProcessor:
    """
    배치 처리 관리자
    """

    def __init__(self, enable_merge: bool = True, merge_tolerance: float = 0.01):
        self.io = JsonHandler()
        self.modifier = DataModifier(
            enable_merge=enable_merge, 
            merge_tolerance=merge_tolerance
        )
        Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def run(self):
        Log.section("Batch Processing Started")
        files = list(Config.INPUT_DIR.glob(Config.FILE_PATTERN))
        
        if not files:
            Log.warning("No JSON files found in input directory.")
            return

        for filepath in files:
            self._process_single_file(filepath)
            
        Log.section(f"Processing Complete. Total files: {len(files)}")

    @measure_time
    def _process_single_file(self, filepath: Path):
        print(f"\nProcessing: {filepath.name}...")
        
        data = self.io.read_json(filepath)
        if not data:
            return

        valid_data, deleted_data = self.modifier.process(data)

        # 1. 정상 데이터 저장
        new_filename = f"{filepath.stem}_Unity{filepath.suffix}"
        output_path = Config.OUTPUT_DIR / new_filename
        
        # [수정] 최상위 키 "result" 추가
        output_data = {"result": valid_data}
        self.io.save_json(output_path, output_data)
        
        # 2. 삭제된 데이터 저장
        if deleted_data:
            deleted_filename = f"{filepath.stem}_Unity_Deleted{filepath.suffix}"
            deleted_path = Config.OUTPUT_DIR / deleted_filename
            
            # [수정] 최상위 키 "result" 추가
            output_deleted_data = {"result": deleted_data}
            self.io.save_json(deleted_path, output_deleted_data)
            
            Log.info(f"-> Deleted items saved to: {deleted_filename} (Count: {len(deleted_data)})")
        
        Log.info(f"-> Valid items saved to: {new_filename} (Count: {len(valid_data)})")