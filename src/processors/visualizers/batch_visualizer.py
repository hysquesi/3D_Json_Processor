from src.config import Config
from src.utils import JsonHandler, Log
from .mesh_visualizer import MeshVisualizer

class BatchVisualizer:
    """
    Output 디렉토리의 결과물들을 일괄적으로 로드하여 3D 그래프로 시각화합니다.
    """

    def run(self):
        Log.section("Result Visualization Phase")
        
        # 출력 디렉토리 파일 조회
        output_files = list(Config.OUTPUT_DIR.glob(Config.FILE_PATTERN))
        
        if not output_files:
            Log.warning("시각화할 결과 파일이 없습니다.")
            return

        print(f"총 {len(output_files)}개의 결과 파일을 순차적으로 시각화합니다.")
        print("그래프 창을 닫으면 다음 파일이 표시됩니다.\n")

        for filepath in output_files:
            Log.info(f"Visualizing: {filepath.name}")
            
            data = JsonHandler.read_json(filepath)
            if not data:
                continue
                
            try:
                # MeshVisualizer 실행 (창을 닫을 때까지 대기)
                viz = MeshVisualizer(data)
                viz.process()
            except Exception as e:
                Log.error(f"시각화 중 오류 발생 ({filepath.name}): {e}")