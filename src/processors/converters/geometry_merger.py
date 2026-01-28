# src/processors/converters/geometry_merger.py
import math
import numpy as np
from scipy.spatial import ConvexHull
from typing import List, Dict, Tuple, Any, Set
from src.utils import Log

class GeometryMerger:
    """
    형상 병합 및 최적화 로직을 담당합니다.
    - 기존의 Plane Merge (인접 평면 병합)
    - [New] Convex Hull Merge (흩어진 조각을 하나의 볼록 다각형으로 통합)
    """

    def __init__(self, norm_tol: float = 0.01, dist_tol: float = 0.01, point_tol: float = 0.001):
        self.norm_tol = norm_tol
        self.dist_tol = dist_tol
        self.point_tol = point_tol

    def merge_by_convex_hull(self, plane_items: Dict[str, Any]) -> Dict[str, Any]:
        """
        여러 평면 조각들의 모든 Vertex를 수집하여, 
        이를 감싸는 하나의 볼록 다각형(Convex Hull)으로 병합합니다.
        Longi BackSide 최적화용으로 사용됩니다.
        """
        # 1. 모든 Vertex 수집
        all_verts = []
        for key, val in plane_items.items():
            verts = self._extract_vertices(val)
            for v in verts:
                all_verts.append([v['x'], v['y'], v['z']])
        
        if len(all_verts) < 3:
            return plane_items # 점이 너무 적으면 병합 불가

        points = np.array(all_verts)
        
        # 2. 최적 평면 도출 (PCA/SVD 이용)
        centroid = np.mean(points, axis=0)
        centered = points - centroid
        
        try:
            u, s, vh = np.linalg.svd(centered)
            normal = vh[2, :] 
        except np.linalg.LinAlgError:
            Log.warning("SVD failed during Convex Hull merge. Using default normal.")
            normal = np.array([0, 0, 1])

        # 3. 로컬 2D 좌표계 생성
        if abs(normal[0]) < 0.9:
            arb = np.array([1, 0, 0])
        else:
            arb = np.array([0, 1, 0])
            
        x_axis = np.cross(normal, arb)
        norm_x = np.linalg.norm(x_axis)
        if norm_x < 1e-6:
             x_axis = np.array([0, 1, 0]) if abs(normal[2]) < 0.9 else np.array([1, 0, 0])
        else:
             x_axis /= norm_x
             
        y_axis = np.cross(normal, x_axis)
        
        # 4. 3D 점들을 로컬 2D 평면으로 투영
        projected_x = np.dot(centered, x_axis)
        projected_y = np.dot(centered, y_axis)
        points_2d = np.column_stack((projected_x, projected_y))
        
        # 5. 2D Convex Hull 계산
        try:
            hull = ConvexHull(points_2d)
            hull_indices = hull.vertices
        except Exception as e:
            Log.warning(f"ConvexHull calculation failed: {e}. Reverting to original.")
            return plane_items

        # 6. 2D Hull 점들을 다시 3D로 복원
        hull_points_2d = points_2d[hull_indices]
        
        hull_points_3d = []
        for p2 in hull_points_2d:
            # P_3d = Centroid + x*X_axis + y*Y_axis
            p3 = centroid + p2[0] * x_axis + p2[1] * y_axis
            hull_points_3d.append({'x': p3[0], 'y': p3[1], 'z': p3[2]})
            
        # 7. 결과 반환
        result = {}
        result["Merged_BackSide"] = self._format_to_json(hull_points_3d)
        
        return result

    def merge_planes(self, plane_items: Dict[str, Any]) -> Dict[str, Any]:
        """기존의 인접 평면 병합 로직"""
        current_data = plane_items
        original_point_tol = self.point_tol
        
        for i in range(2):
            pass_num = i + 1
            input_count = len(current_data)
            
            Log.info(f"--- Merge Pass {pass_num} Started (Input: {input_count} faces) ---")
            
            if pass_num == 2:
                relaxed_tol = 0.05
                self.point_tol = relaxed_tol

            new_data = self._execute_single_pass(current_data, pass_num)
            
            output_count = len(new_data)
            Log.info(f"--- Merge Pass {pass_num} Completed (Output: {output_count} faces) ---")

            if pass_num == 2:
                 self.point_tol = original_point_tol

            if input_count == output_count and pass_num == 2:
                return new_data

            current_data = new_data

        return current_data

    def _execute_single_pass(self, plane_items: Dict[str, Any], pass_num: int) -> Dict[str, Any]:
        # (기존 로직 유지)
        all_input_keys = set(plane_items.keys())
        successfully_processed_keys = set()
        
        face_list = []
        for key, val in plane_items.items():
            verts = self._extract_vertices(val)
            if len(verts) < 3:
                continue
            
            normal = self._calculate_normal(verts)
            d = -(normal[0]*verts[0]['x'] + normal[1]*verts[0]['y'] + normal[2]*verts[0]['z'])
            
            face_list.append({
                'original_key': key,
                'verts': verts,
                'normal': normal,
                'd': d,
                'edges': self._extract_edges(verts)
            })

        plane_groups = self._group_by_plane(face_list)
        
        merged_results = {}
        idx_counter = 1

        for group in plane_groups:
            clusters = self._cluster_by_adjacency(group)
            
            for cluster in clusters:
                cluster_source_keys = [f['original_key'] for f in cluster]
                merged_polygons = self._merge_cluster_to_polygons(cluster)
                
                if not merged_polygons:
                    for face in cluster:
                        new_key = f"Plane_{idx_counter:03d}"
                        merged_results[new_key] = self._format_to_json(face['verts'])
                        successfully_processed_keys.add(face['original_key'])
                        idx_counter += 1
                else:
                    for poly_verts in merged_polygons:
                        new_key = f"Plane_{idx_counter:03d}"
                        merged_results[new_key] = self._format_to_json(poly_verts)
                        idx_counter += 1
                    
                    for k in cluster_source_keys:
                        successfully_processed_keys.add(k)

        return merged_results

    # ... Helper Methods ...
    def _merge_cluster_to_polygons(self, cluster: List[Dict]) -> List[List[Dict]]:
        # (기존 로직 유지)
        refined_cluster = self._resolve_t_junctions(cluster)
        edge_count = {}
        for face in refined_cluster:
            verts = face['verts']
            n = len(verts)
            for i in range(n):
                p1 = self._pt_to_tuple(verts[i])
                p2 = self._pt_to_tuple(verts[(i+1)%n])
                edge_key = tuple(sorted((p1, p2)))
                if edge_key not in edge_count: edge_count[edge_key] = 0
                edge_count[edge_key] += 1

        boundary_edges = []
        for face in refined_cluster:
            verts = face['verts']
            n = len(verts)
            for i in range(n):
                p1 = self._pt_to_tuple(verts[i])
                p2 = self._pt_to_tuple(verts[(i+1)%n])
                edge_key = tuple(sorted((p1, p2)))
                if edge_count[edge_key] == 1:
                    boundary_edges.append((p1, p2))

        if not boundary_edges: return None

        all_loops = self._chain_edges_all(boundary_edges)
        if not all_loops: return None

        result_polygons = []
        for loop_tuples in all_loops:
            merged_verts = [{'x': p[0], 'y': p[1], 'z': p[2]} for p in loop_tuples]
            merged_verts = self._clean_polygon_artifacts(merged_verts)
            
            if len(merged_verts) < 3: return None

            new_normal = self._calculate_normal(merged_verts)
            original_normal = cluster[0]['normal']
            dot = sum(a*b for a, b in zip(new_normal, original_normal))
            if dot < 0: merged_verts.reverse()
            
            result_polygons.append(merged_verts)

        return result_polygons

    def _clean_polygon_artifacts(self, verts: List[Dict]) -> List[Dict]:
        max_iterations = 10
        current_verts = verts[:]
        for _ in range(max_iterations):
            start_len = len(current_verts)
            if start_len < 3: break
            current_verts = self._remove_spikes(current_verts, self.point_tol)
            current_verts = self._remove_short_edges(current_verts, self.point_tol)
            current_verts = self._remove_collinear(current_verts)
            if len(current_verts) == start_len: break
        return current_verts

    def _remove_spikes(self, verts, tol):
        if len(verts) < 3: return verts
        n = len(verts)
        to_delete = [False] * n
        tol_sq = tol ** 2
        for i in range(n):
            p_prev = verts[(i - 1 + n) % n]
            p_next = verts[(i + 1) % n]
            dist_sq = (p_prev['x']-p_next['x'])**2 + (p_prev['y']-p_next['y'])**2 + (p_prev['z']-p_next['z'])**2
            if dist_sq < tol_sq: to_delete[i] = True
        return [verts[i] for i in range(n) if not to_delete[i]]

    def _remove_short_edges(self, verts, tol):
        if len(verts) < 3: return verts
        n = len(verts)
        result = []
        tol_sq = tol ** 2
        skip_next = False
        for i in range(n):
            if skip_next:
                skip_next = False
                continue
            p_curr = verts[i]
            p_next = verts[(i + 1) % n]
            dist_sq = (p_curr['x']-p_next['x'])**2 + (p_curr['y']-p_next['y'])**2 + (p_curr['z']-p_next['z'])**2
            if dist_sq < tol_sq:
                result.append(p_curr)
                if i < n - 1: skip_next = True
            else:
                result.append(p_curr)
        return result

    def _remove_collinear(self, verts):
        if len(verts) < 3: return verts
        n = len(verts)
        to_delete = [False] * n
        collinear_threshold = 0.9999 
        for i in range(n):
            p_prev = verts[(i - 1 + n) % n]
            p_curr = verts[i]
            p_next = verts[(i + 1) % n]
            v1 = (p_curr['x'] - p_prev['x'], p_curr['y'] - p_prev['y'], p_curr['z'] - p_prev['z'])
            len1 = math.sqrt(v1[0]**2 + v1[1]**2 + v1[2]**2)
            v2 = (p_next['x'] - p_curr['x'], p_next['y'] - p_curr['y'], p_next['z'] - p_curr['z'])
            len2 = math.sqrt(v2[0]**2 + v2[1]**2 + v2[2]**2)
            if len1 < 1e-9 or len2 < 1e-9:
                to_delete[i] = True
                continue
            u1 = (v1[0]/len1, v1[1]/len1, v1[2]/len1)
            u2 = (v2[0]/len2, v2[1]/len2, v2[2]/len2)
            dot = u1[0]*u2[0] + u1[1]*u2[1] + u1[2]*u2[2]
            if dot > collinear_threshold: to_delete[i] = True
        return [verts[i] for i in range(n) if not to_delete[i]]

    def _resolve_t_junctions(self, cluster):
        all_points = set()
        for face in cluster:
            for v in face['verts']:
                all_points.add(self._pt_to_tuple(v))
        refined_faces = []
        for face in cluster:
            original_verts = face['verts']
            new_verts_sequence = []
            n = len(original_verts)
            for i in range(n):
                p1 = original_verts[i]
                p2 = original_verts[(i+1)%n]
                new_verts_sequence.append(p1)
                points_on_segment = []
                p1_tuple = self._pt_to_tuple(p1)
                p2_tuple = self._pt_to_tuple(p2)
                vec = (p2['x']-p1['x'], p2['y']-p1['y'], p2['z']-p1['z'])
                seg_len_sq = vec[0]**2 + vec[1]**2 + vec[2]**2
                if seg_len_sq < 1e-9: continue
                for candidate_pt in all_points:
                    if candidate_pt == p1_tuple or candidate_pt == p2_tuple: continue
                    cp = {'x': candidate_pt[0], 'y': candidate_pt[1], 'z': candidate_pt[2]}
                    if self._is_point_on_segment(cp, p1, p2, vec, seg_len_sq):
                        points_on_segment.append(candidate_pt)
                if points_on_segment:
                    points_on_segment.sort(key=lambda pt: (pt[0]-p1['x'])**2 + (pt[1]-p1['y'])**2 + (pt[2]-p1['z'])**2)
                    for pt in points_on_segment:
                        new_verts_sequence.append({'x': pt[0], 'y': pt[1], 'z': pt[2]})
            refined_faces.append({'verts': new_verts_sequence})
        return refined_faces

    def _is_point_on_segment(self, pt, p1, p2, vec, len_sq):
        v_pt = (pt['x']-p1['x'], pt['y']-p1['y'], pt['z']-p1['z'])
        cx = v_pt[1]*vec[2] - v_pt[2]*vec[1]
        cy = v_pt[2]*vec[0] - v_pt[0]*vec[2]
        cz = v_pt[0]*vec[1] - v_pt[1]*vec[0]
        dist_sq = cx**2 + cy**2 + cz**2
        if dist_sq > (self.point_tol**2) * len_sq: return False
        dot = v_pt[0]*vec[0] + v_pt[1]*vec[1] + v_pt[2]*vec[2]
        if dot < self.point_tol or dot > len_sq - self.point_tol: return False
        return True

    def _chain_edges_all(self, edges):
        adj = {}
        for start, end in edges: adj[start] = end
        loops = []
        while adj:
            start_pt = list(adj.keys())[0]
            curr_pt = start_pt
            loop = []
            safe_count = 0
            max_iter = len(adj) * 2
            while safe_count < max_iter:
                loop.append(curr_pt)
                if curr_pt not in adj:
                    for p in loop:
                        if p in adj: del adj[p]
                    break 
                next_pt = adj[curr_pt]
                del adj[curr_pt]
                curr_pt = next_pt
                if curr_pt == start_pt:
                    loops.append(loop)
                    break
                safe_count += 1
        return loops

    def _extract_edges(self, verts):
        edges = []
        n = len(verts)
        for i in range(n):
            p1, p2 = verts[i], verts[(i+1)%n]
            vec = (p2['x']-p1['x'], p2['y']-p1['y'], p2['z']-p1['z'])
            length = math.sqrt(vec[0]**2 + vec[1]**2 + vec[2]**2)
            unit_vec = (0,0,0) if length < 1e-9 else (vec[0]/length, vec[1]/length, vec[2]/length)
            edges.append({'p1': p1, 'p2': p2, 'vec': unit_vec, 'length': length})
        return edges

    def _cluster_by_adjacency(self, group):
        n = len(group)
        parent = list(range(n))
        def find(i):
            if parent[i] == i: return i
            parent[i] = find(parent[i])
            return parent[i]
        def union(i, j):
            r1, r2 = find(i), find(j)
            if r1 != r2: parent[r2] = r1
        for i in range(n):
            for j in range(i+1, n):
                if self._are_faces_touching(group[i], group[j]): union(i, j)
        clusters = {}
        for i in range(n):
            r = find(i)
            if r not in clusters: clusters[r] = []
            clusters[r].append(group[i])
        return list(clusters.values())

    def _are_faces_touching(self, face_a, face_b):
        for ea in face_a['edges']:
            for eb in face_b['edges']:
                dot = abs(sum(a*b for a,b in zip(ea['vec'], eb['vec'])))
                if dot < (1.0 - self.norm_tol): continue
                if self._is_collinear(ea, eb) and self._is_overlapping(ea, eb): return True
        return False

    def _is_collinear(self, ea, eb):
        diff = (eb['p1']['x']-ea['p1']['x'], eb['p1']['y']-ea['p1']['y'], eb['p1']['z']-ea['p1']['z'])
        cx = diff[1]*ea['vec'][2] - diff[2]*ea['vec'][1]
        cy = diff[2]*ea['vec'][0] - diff[0]*ea['vec'][2]
        cz = diff[0]*ea['vec'][1] - diff[1]*ea['vec'][0]
        return (cx**2 + cy**2 + cz**2) < (self.point_tol**2)

    def _is_overlapping(self, ea, eb):
        def proj(p, o, v): return (p['x']-o['x'])*v[0] + (p['y']-o['y'])*v[1] + (p['z']-o['z'])*v[2]
        o, v = ea['p1'], ea['vec']
        b1, b2 = proj(eb['p1'], o, v), proj(eb['p2'], o, v)
        start, end = max(0.0, min(b1, b2)), min(ea['length'], max(b1, b2))
        return (end - start) > self.point_tol

    def _extract_vertices(self, data):
        verts = []
        sorted_keys = sorted([k for k in data.keys() if "vertex" in k.lower()])
        for k in sorted_keys:
            v = data[k]
            if isinstance(v, dict):
                verts.append({'x': float(v.get('x',0)), 'y': float(v.get('y',0)), 'z': float(v.get('z',0))})
        return verts

    def _calculate_normal(self, verts):
        sx, sy, sz = 0.0, 0.0, 0.0
        n = len(verts)
        for i in range(n):
            c, nxt = verts[i], verts[(i+1)%n]
            sx += (nxt['y']-c['y'])*(c['z']+nxt['z'])
            sy += (nxt['z']-c['z'])*(c['x']+nxt['x'])
            sz += (nxt['x']-c['x'])*(c['y']+nxt['y'])
        l = math.sqrt(sx**2 + sy**2 + sz**2)
        if l < 1e-9: return (0,1,0)
        return (sx/l, sy/l, sz/l)

    def _group_by_plane(self, faces):
        groups = []
        vis = [False]*len(faces)
        for i in range(len(faces)):
            if vis[i]: continue
            grp = [faces[i]]
            vis[i] = True
            for j in range(i+1, len(faces)):
                if vis[j]: continue
                dot = sum(a*b for a,b in zip(faces[i]['normal'], faces[j]['normal']))
                if dot > (1.0 - self.norm_tol) and abs(faces[i]['d'] - faces[j]['d']) < self.dist_tol:
                    grp.append(faces[j])
                    vis[j] = True
            groups.append(grp)
        return groups

    def _pt_to_tuple(self, pt):
        p = 3
        return (round(pt['x'], p), round(pt['y'], p), round(pt['z'], p))

    def _format_to_json(self, verts):
        res = {}
        for i, v in enumerate(verts):
            res[f"Vertex_{i+1:03d}"] = v
        return res