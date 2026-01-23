import json
import math
from typing import List, Dict, Tuple

# 설정: 검사할 유격 거리 범위 (예: 10cm 이내의 후보 탐색)
SEARCH_RADIUS = 0.15  # 15cm (넉넉하게 설정하여 5cm가 포함되는지 확인)
NORM_TOL = 0.05       # 법선 허용 오차 (약 18도)

def calculate_normal(verts):
    sx, sy, sz = 0.0, 0.0, 0.0
    n = len(verts)
    for i in range(n):
        c, nxt = verts[i], verts[(i+1)%n]
        sx += (nxt['y']-c['y'])*(c['z']+nxt['z'])
        sy += (nxt['z']-c['z'])*(c['x']+nxt['x'])
        sz += (nxt['x']-c['x'])*(c['y']+nxt['y'])
    l = math.sqrt(sx**2 + sy**2 + sz**2)
    if l < 1e-9: return (0,0,1)
    return (sx/l, sy/l, sz/l)

def get_edge_vectors(verts):
    edges = []
    n = len(verts)
    for i in range(n):
        p1, p2 = verts[i], verts[(i+1)%n]
        vec = (p2['x']-p1['x'], p2['y']-p1['y'], p2['z']-p1['z'])
        length = math.sqrt(sum(c**2 for c in vec))
        if length > 1e-6:
            unit = (vec[0]/length, vec[1]/length, vec[2]/length)
            edges.append({'p1': p1, 'p2': p2, 'vec': unit, 'len': length})
    return edges

def dist_sq(p1, p2):
    return (p1['x']-p2['x'])**2 + (p1['y']-p2['y'])**2 + (p1['z']-p2['z'])**2

def point_to_segment_dist(pt, edge):
    p1, p2 = edge['p1'], edge['p2']
    dx, dy, dz = p2['x']-p1['x'], p2['y']-p1['y'], p2['z']-p1['z']
    if dx==0 and dy==0 and dz==0: return math.sqrt(dist_sq(pt, p1))
    
    t = ((pt['x']-p1['x'])*dx + (pt['y']-p1['y'])*dy + (pt['z']-p1['z'])*dz) / (dx*dx + dy*dy + dz*dz)
    t = max(0, min(1, t))
    closest = {
        'x': p1['x'] + t*dx,
        'y': p1['y'] + t*dy,
        'z': p1['z'] + t*dz
    }
    return math.sqrt(dist_sq(pt, closest))

def analyze_candidates(file_path):
    print(f"--- Loading {file_path} ---")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. Flatten Data
    faces = []
    for main_k, main_v in data.items():
        for sub_k, sub_v in main_v.items():
            verts = []
            sorted_keys = sorted([k for k in sub_v.keys() if "vertex" in k.lower()])
            for k in sorted_keys:
                verts.append(sub_v[k])
            
            if len(verts) < 3: continue
            normal = calculate_normal(verts)
            # Plane Distance from origin D = -(Ax+By+Cz)
            d = -(normal[0]*verts[0]['x'] + normal[1]*verts[0]['y'] + normal[2]*verts[0]['z'])
            faces.append({
                'id': sub_k,
                'verts': verts,
                'normal': normal,
                'd': d,
                'edges': get_edge_vectors(verts)
            })

    print(f"Total Faces Found: {len(faces)}")
    
    # 2. Group by Plane (Strict Coplanar Check First)
    groups = []
    visited = [False] * len(faces)
    
    for i in range(len(faces)):
        if visited[i]: continue
        group = [faces[i]]
        visited[i] = True
        for j in range(i+1, len(faces)):
            if visited[j]: continue
            # Normal Dot Product Check
            dot = sum(a*b for a,b in zip(faces[i]['normal'], faces[j]['normal']))
            # Distance Check (같은 평면상에 있는지)
            dist_diff = abs(faces[i]['d'] - faces[j]['d'])
            
            if dot > (1.0 - NORM_TOL) and dist_diff < 0.05: # 평면 거리는 5cm 이내로 관대하게
                group.append(faces[j])
                visited[j] = True
        if len(group) > 1:
            groups.append(group)

    # 3. Analyze Proximity within Groups
    print(f"\n--- Analysis Results (Candidates within {SEARCH_RADIUS*100}cm) ---")
    
    for grp in groups:
        # 그룹 내에서 서로 가깝지만 붙어있지 않은 쌍 찾기
        for i in range(len(grp)):
            for j in range(i+1, len(grp)):
                f1, f2 = grp[i], grp[j]
                
                # Calculate Min Distance
                min_d = float('inf')
                
                # Check f1 vertices to f2 edges
                for v in f1['verts']:
                    for e in f2['edges']:
                        d_val = point_to_segment_dist(v, e)
                        if d_val < min_d: min_d = d_val
                
                # Check f2 vertices to f1 edges
                for v in f2['verts']:
                    for e in f1['edges']:
                        d_val = point_to_segment_dist(v, e)
                        if d_val < min_d: min_d = d_val
                
                if 0.001 < min_d < SEARCH_RADIUS: # 1mm보다 크고 설정 범위 이내인 경우
                    # Normal Angle
                    dot = sum(a*b for a,b in zip(f1['normal'], f2['normal']))
                    angle = math.degrees(math.acos(min(1.0, max(-1.0, dot))))
                    
                    # Edge Parallelism (가장 가까운 엣지끼리의 내적)
                    max_parallel = 0.0
                    for e1 in f1['edges']:
                        for e2 in f2['edges']:
                            # 평행 = 내적 절댓값이 1에 가까움
                            p_dot = abs(sum(a*b for a,b in zip(e1['vec'], e2['vec'])))
                            if p_dot > max_parallel: max_parallel = p_dot
                    
                    print(f"\n[Pair Found]")
                    print(f"  Face A: {f1['id']}")
                    print(f"  Face B: {f2['id']}")
                    print(f"  > Gap Distance: {min_d*100:.2f} cm")
                    print(f"  > Normal Deviation: {angle:.2f} deg")
                    print(f"  > Max Edge Parallelism: {max_parallel:.4f} (1.0 is parallel)")
                    
                    if min_d <= 0.05 and max_parallel > 0.9:
                        print("  => RECOMMENDED: Target for 2nd Pass Merge")

if __name__ == "__main__":
    # 실행 경로 설정 필요
    analyze_candidates("3D_Json_Processor/data/input/D320P_Surface.json")