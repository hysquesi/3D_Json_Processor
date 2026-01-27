# src/processors/converters/batch_processor.py
from pathlib import Path
from src.config import Config
from src.utils import JsonHandler, measure_time, Log
from .data_modifier import DataModifier

class BatchProcessor:
    """Orchestrates the batch processing workflow."""

    def __init__(self, enable_merge: bool = True, merge_tolerance: float = 0.01):
        self.io = JsonHandler()
        
        # [수정] 오차율(merge_tolerance)도 함께 전달
        self.modifier = DataModifier(
            enable_merge=enable_merge, 
            merge_tolerance=merge_tolerance
        )
        
        Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def run(self):
        # ... (기존 run 메서드 로직 동일) ...
        Log.section("Batch Processing Started")
        print(f"Input Directory: {Config.INPUT_DIR}")
        
        files = list(Config.INPUT_DIR.glob(Config.FILE_PATTERN))
        
        if not files:
            Log.warning("No JSON files found in input directory.")
            return

        for filepath in files:
            self._process_single_file(filepath)
            
        Log.section(f"Processing Complete. Total files: {len(files)}")

    @measure_time
    def _process_single_file(self, filepath: Path):
        # ... (기존 로직 동일) ...
        print(f"\nProcessing: {filepath.name}...")
        
        data = self.io.read_json(filepath)
        if not data:
            return

        new_data = self.modifier.process(data)

        new_filename = f"{filepath.stem}_Modified{filepath.suffix}"
        output_path = Config.OUTPUT_DIR / new_filename
        
        self.io.save_json(output_path, new_data)