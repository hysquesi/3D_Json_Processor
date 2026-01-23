import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from typing import Dict, Any, List, Tuple
from src.utils import Log
import math

class MeshVisualizer:
    """
    3D JSON 데이터를 로드하여 시각화합니다.
    [변경] Backface Culling 로직이 삭제되었습니다.
    Normal Vector는 로드 후 직접 계산하여 화살표로 시각화합니다.
    """
    
    RAINBOW_COLORS = ['red', 'orange', 'yellow', 'green', 'blue', 'indigo', 'violet']

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.faces = {}
        self.normals = {} 
        self.adjacency = {}
        self.colors = {}

    def process(self):
        Log.section("Visualization Started")
        
        # 1. Geometry 파싱
        self._parse_geometry()
        
        if not self.faces:
            Log.warning("No geometry found to visualize.")
            return
            
        # 2. Normal Vector 직접 계산 (화살표 시각화용)
        self._calculate_all_normals()
        Log.info(f"Calculated normals for {len(self.normals)} faces.")

        # 3. 그래프 생성 및 시각화
        self._build_adjacency_graph()
        self._assign_colors_greedy()
        self._plot_3d()

    def _parse_geometry(self):
        def extract_vertices_from_dict(d: Dict) -> List[Tuple[float, float, float]]:
            vertices = []
            sorted_keys = sorted([k for k in d.keys() if "vertex" in k.lower()])
            for k in sorted_keys:
                v = d[k]
                if isinstance(v, dict):
                    try:
                        vertices.append((float(v.get('x', 0)), float(v.get('y', 0)), float(v.get('z', 0))))
                    except: pass
            return vertices

        for key, value in self.data.items():
            if not isinstance(value, dict): continue

            def process_face(k, v):
                verts = extract_vertices_from_dict(v)
                if verts and len(verts) >= 3:
                    self.faces[k] = verts

            process_face(key, value)
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, dict):
                    process_face(sub_key, sub_value)

    def _calculate_all_normals(self):
        """모든 면에 대해 Normal Vector를 계산합니다."""
        for face_id, verts in self.faces.items():
            self.normals[face_id] = self._calculate_single_normal(verts)

    def _calculate_single_normal(self, verts: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
        """C# CalculateNormal 메서드 논리 구현"""
        n = len(verts)
        if n < 3:
            return (0.0, 1.0, 0.0)

        sum_x, sum_y, sum_z = 0.0, 0.0, 0.0

        for i in range(n):
            curr = verts[i]
            next_v = verts[(i + 1) % n]

            # C# Logic: (next - current) * (sum)
            sum_x += (next_v[1] - curr[1]) * (curr[2] + next_v[2])
            sum_y += (next_v[2] - curr[2]) * (curr[0] + next_v[0])
            sum_z += (next_v[0] - curr[0]) * (curr[1] + next_v[1])

        length = math.sqrt(sum_x**2 + sum_y**2 + sum_z**2)
        if length < 1e-9:
            return (0.0, 1.0, 0.0)

        return (sum_x / length, sum_y / length, sum_z / length)

    def _build_adjacency_graph(self):
        face_ids = list(self.faces.keys())
        n = len(face_ids)
        for fid in face_ids:
            self.adjacency[fid] = set()
        for i in range(n):
            for j in range(i + 1, n):
                id_a, id_b = face_ids[i], face_ids[j]
                if len(set(self.faces[id_a]).intersection(set(self.faces[id_b]))) >= 2:
                    self.adjacency[id_a].add(id_b)
                    self.adjacency[id_b].add(id_a)

    def _assign_colors_greedy(self):
        sorted_faces = sorted(self.faces.keys(), key=lambda k: len(self.adjacency[k]), reverse=True)
        for face_id in sorted_faces:
            neighbor_colors = {self.colors[n] for n in self.adjacency[face_id] if n in self.colors}
            found = next((c for c in self.RAINBOW_COLORS if c not in neighbor_colors), 'gray')
            self.colors[face_id] = found

    def _plot_3d(self):
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        polygons = []
        face_colors = []

        for face_id, verts in self.faces.items():
            # 1. Mesh Plot (Unity to Plot: x, z, y)
            visual_verts = [(v[0], v[2], v[1]) for v in verts]
            polygons.append(visual_verts)
            
            face_colors.append(self.colors.get(face_id, 'gray'))

            # 2. Normal Vector Plot (화살표 그리기)
            if face_id in self.normals:
                nx, ny, nz = self.normals[face_id]
                
                # 중심점 (Unity to Plot)
                orig_verts = np.array(verts)
                center = orig_verts.mean(axis=0)
                sx, sy, sz = center[0], center[2], center[1]
                
                # 방향 (Unity to Plot)
                dx, dy, dz = nx, nz, ny
                
                ax.quiver(sx, sy, sz, dx, dy, dz,
                          length=0.25, color='black', linewidth=1.0, arrow_length_ratio=0.3)

        # Poly3DCollection 생성
        poly_collection = Poly3DCollection(polygons, alpha=0.6, edgecolor='gray', linewidths=0.5)
        poly_collection.set_facecolor(face_colors)
        ax.add_collection3d(poly_collection)

        # 축 범위 설정
        all_visual_verts = [v for poly in polygons for v in poly]
        if all_visual_verts:
            arr = np.array(all_visual_verts)
            ax.set_xlim(arr[:,0].min(), arr[:,0].max())
            ax.set_ylim(arr[:,1].min(), arr[:,1].max())
            ax.set_zlim(arr[:,2].min(), arr[:,2].max())

        ax.set_xlabel('Unity X')
        ax.set_ylabel('Unity Z (Depth)')
        ax.set_zlabel('Unity Y (Height)')
        ax.set_title(f'3D Mesh Visualization ({len(self.faces)} faces)')

    

        plt.show()