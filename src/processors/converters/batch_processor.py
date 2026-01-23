from pathlib import Path
from src.config import Config
from src.utils import JsonHandler, measure_time, Log
from .data_modifier import DataModifier

class BatchProcessor:
    """Orchestrates the batch processing workflow."""

    def __init__(self):
        self.io = JsonHandler()
        self.modifier = DataModifier()
        
        # Ensure output directory exists
        Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def run(self):
        """Main execution loop."""
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
        print(f"\nProcessing: {filepath.name}...")
        
        # 1. Load
        data = self.io.read_json(filepath)
        if not data:
            return

        # 2. Modify
        new_data = self.modifier.process(data)

        # 3. Save
        new_filename = f"{filepath.stem}_Modified{filepath.suffix}"
        output_path = Config.OUTPUT_DIR / new_filename
        
        self.io.save_json(output_path, new_data)