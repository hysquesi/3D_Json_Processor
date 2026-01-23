import json
import math
import os

# ==========================================
# 설정: 검사할 파일 경로 및 허용 오차
# ==========================================
# [수정됨] 파일 경로를 data/output 폴더로 지정
FILE_PATH = os.path.join('data', 'output', 'B230C_Surface_Modified.json')

NORMAL_TOLERANCE = 0.1  # +Y 방향 판정 오차
MERGE_DIST_TOL = 0.05   # 병합되어야 했다고 판단하는 거리 기준

def calculate_normal(verts):
    """주어진 버텍스 리스트로부터 법선 벡터 계산"""
    if len(verts) < 3: return (0,0,0)
    p0, p1, p2 = verts[0], verts[1], verts[2]
    
    # 벡터 계산 (v1: 0->1, v2: 1->2)
    v1 = (p1['x'] - p0['x'], p1['y'] - p0['y'], p1['z'] - p0['z'])
    v2 = (p2['x'] - p1['x'], p2['y'] - p1['y'], p2['z'] - p1['z'])
    
    # 외적 (Cross Product)
    nx = v1[1]*v2[2] - v1[2]*v2[1]
    ny = v1[2]*v2[0] - v1[0]*v2[2]
    nz = v1[0]*v2[1] - v1[1]*v2[0]
    
    length = math.sqrt(nx**2 + ny**2 + nz**2)
    if length < 1e-9: return (0,0,0)
    return (nx/length, ny/length, nz/length)

def load_and_analyze(file_path):
    if not os.path.exists(file_path):
        print(f"Error: 파일을 찾을 수 없습니다. 경로를 확인해주세요: {os.path.abspath(file_path)}")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return []

    target_planes = []
    print(f"--- 분석 시작: {file_path} ---")
    
    # 1. Plane 데이터 추출 및 Normal 필터링
    for key, val in data.items():
        if not key.startswith("Plane"): continue
        
        # 버텍스 추출
        verts = []
        # 키 이름이 Vertex_001, Vertex_002... 순서대로라고 가정
        v_keys = sorted([k for k in val.keys() if "Vertex" in k])
        for vk in v_keys:
            verts.append(val[vk])
            
        if len(verts) < 3: continue
        
        norm = calculate_normal(verts)
        
        # +Y 방향 필터링 (x, z는 0에 가깝고, y는 1에 가까운지)
        if abs(norm[0]) < NORMAL_TOLERANCE and norm[1] > (1.0 - NORMAL_TOLERANCE) and abs(norm[2]) < NORMAL_TOLERANCE:
            # 평면 방정식 ax+by+cz+d=0 에서 d 값 계산 (높이 비교용)
            d = -(norm[0]*verts[0]['x'] + norm[1]*verts[0]['y'] + norm[2]*verts[0]['z'])
            
            target_planes.append({
                'key': key,
                'normal': norm,
                'd': d,
                'verts': verts
            })

    print(f"검색된 +Y 방향 Plane 개수: {len(target_planes)}개")
    return target_planes

def inspect_merge_failures(planes):
    # d값(높이) 기준으로 정렬하여 비슷한 높이끼리 비교
    planes.sort(key=lambda x: x['d'])
    
    suspicious_pairs = []
    
    print("\n--- 병합 실패 원인 분석 (Merge Failure Inspection) ---")
    print(f"기준: 높이 차이 < {MERGE_DIST_TOL}, 버텍스 간 거리 < {MERGE_DIST_TOL*2}")
    
    for i in range(len(planes)):
        for j in range(i+1, len(planes)):
            p1 = planes[i]
            p2 = planes[j]
            
            # 1. 평면 높이 차이(d_diff) 검사
            d_diff = abs(p1['d'] - p2['d'])
            if d_diff > MERGE_DIST_TOL: 
                # 높이 차이가 크면 어차피 병합 대상 아님
                continue 
            
            # 2. 물리적 거리 검사 (가장 가까운 두 점 사이의 거리)
            min_dist = 1e9
            for v1 in p1['verts']:
                for v2 in p2['verts']:
                    dist = math.sqrt((v1['x']-v2['x'])**2 + (v1['y']-v2['y'])**2 + (v1['z']-v2['z'])**2)
                    if dist < min_dist: min_dist = dist
            
            # 3. 결과 판정
            if min_dist < (MERGE_DIST_TOL * 2): # 거리가 매우 가까움
                print(f"[의심] {p1['key']} <-> {p2['key']}")
                print(f"  - 높이 차이(d_diff): {d_diff:.6f}")
                print(f"  - 최소 거리(min_dist): {min_dist:.6f}")
                
                if min_dist < 1e-4:
                    print("  -> 판정: 완전히 맞닿아 있음 (병합 로직 누락 가능성 높음)")
                else:
                    print("  -> 판정: 아주 미세하게 떨어져 있음 (Tolerance 조절 필요)")
                suspicious_pairs.append((p1['key'], p2['key']))

    if not suspicious_pairs:
        print("\n분석 결과: 병합되어야 할 것으로 보이는 인접한 면이 발견되지 않았습니다.")
    else:
        print(f"\n총 {len(suspicious_pairs)}쌍의 병합 실패 의심 사례가 발견되었습니다.")

if __name__ == "__main__":
    planes = load_and_analyze(FILE_PATH)
    if planes:
        # 발견된 면 리스트 출력
        print("\n[발견된 +Y Plane 목록]")
        for p in planes:
            # 보기 좋게 소수점 포맷팅
            norm_str = f"({p['normal'][0]:.3f}, {p['normal'][1]:.3f}, {p['normal'][2]:.3f})"
            print(f" - {p['key']}: Normal={norm_str}, d={p['d']:.4f}")
            
        # 심층 분석 실행
        inspect_merge_failures(planes)