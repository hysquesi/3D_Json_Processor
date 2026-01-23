import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from typing import Dict, Any, List, Tuple
from src.utils import Log

class MeshVisualizer:
    """
    3D JSON 데이터를 로드하여 Wireframe으로 시각화하고
    Greedy 알고리즘으로 인접한 면의 색상을 구분합니다.
    """
    
    # 빨주노초파남보 색상 정의 (Matplotlib 색상 코드)
    RAINBOW_COLORS = ['red', 'orange', 'yellow', 'green', 'blue', 'indigo', 'violet']

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.faces = {}  # { 'Plane_001': [ (x,y,z), (x,y,z), ... ] }
        self.adjacency = {} # { 'Plane_001': set(['Plane_002', ...]) }
        self.colors = {}    # { 'Plane_001': 'red' }

    def process(self):
        """데이터 파싱, 인접 계산, 색상 할당, 시각화를 순차적으로 실행"""
        Log.section("Visualization Started")
        
        # 1. 데이터 파싱 (Vertex 추출)
        self._parse_geometry()
        Log.info(f"Loaded {len(self.faces)} faces.")

        if not self.faces:
            Log.warning("No geometry found to visualize.")
            return

        # 2. 인접 그래프 생성
        self._build_adjacency_graph()
        
        # 3. Greedy 색상 할당
        self._assign_colors_greedy()
        
        # 4. 3D 플로팅
        self._plot_3d()

    def _parse_geometry(self):
        """
        JSON 구조에서 vertex 좌표를 추출하여 면(Face) 정보를 구축합니다.
        Longi 계열과 같이 중첩된 구조도 처리할 수 있도록 개선되었습니다.
        """
        def extract_vertices_from_dict(d: Dict) -> List[Tuple[float, float, float]]:
            """딕셔너리에서 vertex 정보를 찾아 좌표 리스트로 반환"""
            vertices = []
            # 'vertex'가 포함된 키들을 정렬하여 순서대로 추출 (대소문자 무시)
            sorted_keys = sorted([k for k in d.keys() if "vertex" in k.lower()])
            
            for k in sorted_keys:
                v = d[k]
                # 리스트 형태: [x, y, z]
                if isinstance(v, (list, tuple)) and len(v) >= 3:
                    vertices.append(tuple(v[:3]))
                # 딕셔너리 형태: {"x": ..., "y": ..., "z": ...}
                elif isinstance(v, dict):
                    try:
                        x = float(v.get('x', 0))
                        y = float(v.get('y', 0))
                        z = float(v.get('z', 0))
                        vertices.append((x, y, z))
                    except (ValueError, TypeError):
                        pass
            return vertices

        for key, value in self.data.items():
            if not isinstance(value, dict):
                continue

            # 1. 현재 레벨에서 바로 Vertex 확인 (예: Plane 계열)
            # Plane_001 -> { Vertex_001: ... }
            verts = extract_vertices_from_dict(value)
            if verts and len(verts) >= 3:
                self.faces[key] = verts
                continue

            # 2. 하위 레벨 탐색 (예: Longi 계열)
            # Longi_001 -> { Longi_001_Bot_001: {Vertex...}, Longi_001_Left_001: {Vertex...} }
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, dict):
                    sub_verts = extract_vertices_from_dict(sub_value)
                    if sub_verts and len(sub_verts) >= 3:
                        # 하위 키(예: Longi_001_Bot_001)를 face 이름으로 사용
                        self.faces[sub_key] = sub_verts

    def _build_adjacency_graph(self):
        """
        면들 간의 인접 관계(공유하는 점이 있는지)를 파악하여 그래프 생성
        단순화를 위해 '2개 이상의 점을 공유'하면 인접으로 간주
        """
        face_ids = list(self.faces.keys())
        n = len(face_ids)
        
        # 초기화
        for fid in face_ids:
            self.adjacency[fid] = set()

        # O(N^2) 비교 (면 개수가 많으면 최적화 필요)
        for i in range(n):
            id_a = face_ids[i]
            verts_a = set(self.faces[id_a]) # 비교를 위해 set으로 변환
            
            for j in range(i + 1, n):
                id_b = face_ids[j]
                verts_b = set(self.faces[id_b])
                
                # 공유하는 vertex 개수 계산
                common_verts = verts_a.intersection(verts_b)
                
                # 2개 이상 공유 시 인접 (Edge 공유)
                if len(common_verts) >= 2:
                    self.adjacency[id_a].add(id_b)
                    self.adjacency[id_b].add(id_a)

    def _assign_colors_greedy(self):
        """Greedy Graph Coloring Algorithm"""
        # 차수(Degree)가 높은 순서대로 정렬하면 색상 사용을 최적화하는 데 도움됨
        sorted_faces = sorted(self.faces.keys(), 
                              key=lambda k: len(self.adjacency[k]), 
                              reverse=True)
        
        for face_id in sorted_faces:
            # 인접한 면들이 사용 중인 색상 집합 구하기
            neighbor_colors = set()
            for neighbor in self.adjacency[face_id]:
                if neighbor in self.colors:
                    neighbor_colors.add(self.colors[neighbor])
            
            # 사용 가능한 첫 번째 색상 찾기
            found_color = None
            for color in self.RAINBOW_COLORS:
                if color not in neighbor_colors:
                    found_color = color
                    break
            
            # 7가지 색으로 부족할 경우, 회색(gray)을 기본값으로 사용
            if found_color is None:
                found_color = 'gray' 
            
            self.colors[face_id] = found_color

    def _plot_3d(self):
        """Matplotlib을 이용한 3D 시각화"""
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        polygons = []
        face_colors = []

        for face_id, verts in self.faces.items():
            polygons.append(verts)
            face_colors.append(self.colors.get(face_id, 'gray'))

        # Poly3DCollection 생성
        # alpha: 투명도, edgecolor: 테두리 색상
        poly_collection = Poly3DCollection(polygons, alpha=0.6, edgecolor='k')
        poly_collection.set_facecolor(face_colors)
        
        ax.add_collection3d(poly_collection)

        # 축 범위 자동 설정
        all_verts = [v for verts in self.faces.values() for v in verts]
        if all_verts:
            all_verts = np.array(all_verts)
            x_min, y_min, z_min = all_verts.min(axis=0)
            x_max, y_max, z_max = all_verts.max(axis=0)
            
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)
            ax.set_zlim(z_min, z_max)

        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title(f'3D Mesh Visualization ({len(self.faces)} faces)')

        plt.show()