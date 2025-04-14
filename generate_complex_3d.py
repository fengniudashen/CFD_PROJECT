#!/usr/bin/env python
"""
生成复杂的3D门格海绵分形立体模型的NAS文件
"""
import os
import time
import numpy as np
from scipy.spatial import Delaunay
import itertools

def generate_cube(center, size):
    """生成一个立方体的顶点和面"""
    half_size = size / 2
    
    # 生成8个顶点
    vertices = []
    for dx, dy, dz in itertools.product([-1, 1], repeat=3):
        vertices.append([
            center[0] + dx * half_size,
            center[1] + dy * half_size,
            center[2] + dz * half_size
        ])
    
    # 定义12个面（每个面分为2个三角形）
    faces = [
        # 前面
        [0, 1, 2], [1, 3, 2],
        # 后面
        [4, 6, 5], [5, 6, 7],
        # 上面
        [2, 3, 6], [3, 7, 6],
        # 下面
        [0, 4, 1], [1, 4, 5],
        # 左面
        [0, 2, 4], [2, 6, 4],
        # 右面
        [1, 5, 3], [3, 5, 7]
    ]
    
    return vertices, faces

def generate_menger_sponge(center, size, level):
    """递归生成门格海绵的顶点和面"""
    if level == 0:
        return generate_cube(center, size)
    
    vertices = []
    faces = []
    
    # 门格海绵在每个维度被分为3份，形成27个小立方体
    # 其中挖去中心和穿过中心的3条"柱子"，剩下20个小立方体
    next_size = size / 3
    
    for x in [-1, 0, 1]:
        for y in [-1, 0, 1]:
            for z in [-1, 0, 1]:
                # 跳过中心小立方体
                if [x, y, z].count(0) >= 2:
                    continue
                
                new_center = [
                    center[0] + x * next_size,
                    center[1] + y * next_size,
                    center[2] + z * next_size
                ]
                
                # 递归生成更小的立方体
                sub_vertices, sub_faces = generate_menger_sponge(new_center, next_size, level - 1)
                
                # 添加顶点和面，调整索引
                vertex_offset = len(vertices)
                vertices.extend(sub_vertices)
                for face in sub_faces:
                    faces.append([f + vertex_offset for f in face])
    
    return vertices, faces

def decimate_mesh(vertices, faces, target_faces):
    """简化网格至目标面数"""
    print(f"简化网格，当前面数: {len(faces)}，目标面数: {target_faces}")
    
    if len(faces) <= target_faces:
        return vertices, faces
    
    # 计算要移除的面的百分比
    remove_ratio = 1 - (target_faces / len(faces))
    
    # 直接随机选择面保留（简单但有效的方法）
    indices = np.random.choice(len(faces), size=target_faces, replace=False)
    faces = [faces[i] for i in indices]
    
    print(f"网格简化完成，现有面数: {len(faces)}")
    return vertices, faces

def add_random_noise(vertices, noise_level=0.01):
    """给顶点添加随机噪声，使表面更不规则"""
    noisy_vertices = []
    for v in vertices:
        # 为每个坐标添加小量的随机噪声
        noise = np.random.normal(0, noise_level, 3)
        noisy_vertices.append([v[0] + noise[0], v[1] + noise[1], v[2] + noise[2]])
    return noisy_vertices

def extrude_and_deform(vertices, faces, deform_factor=0.3):
    """挤出并变形网格，创建更复杂的结构"""
    new_vertices = vertices.copy()
    new_faces = faces.copy()
    
    # 查找更多面进行挤出
    extrude_count = min(800000, len(faces) // 2)  # 增加挤出的面数量
    extrude_indices = np.random.choice(len(faces), size=extrude_count, replace=False)
    
    print(f"准备挤出 {extrude_count} 个面...")
    
    vertex_count = len(vertices)
    processed = 0
    
    for idx in extrude_indices:
        face = faces[idx]
        
        # 计算面的中心和法向量
        v1, v2, v3 = [vertices[i] for i in face]
        face_center = [(v1[0] + v2[0] + v3[0])/3, 
                      (v1[1] + v2[1] + v3[1])/3, 
                      (v1[2] + v2[2] + v3[2])/3]
        
        edge1 = [v2[0]-v1[0], v2[1]-v1[1], v2[2]-v1[2]]
        edge2 = [v3[0]-v1[0], v3[1]-v1[1], v3[2]-v1[2]]
        normal = [
            edge1[1]*edge2[2] - edge1[2]*edge2[1],
            edge1[2]*edge2[0] - edge1[0]*edge2[2],
            edge1[0]*edge2[1] - edge1[1]*edge2[0]
        ]
        
        # 归一化法向量
        length = np.sqrt(normal[0]**2 + normal[1]**2 + normal[2]**2)
        if length > 0:
            normal = [n/length for n in normal]
        else:
            continue
        
        # 设置挤出距离
        extrude_dist = np.random.uniform(0.02, 0.1)
        
        # 添加三个新顶点
        new_v1 = [v1[0] + normal[0] * extrude_dist, 
                 v1[1] + normal[1] * extrude_dist, 
                 v1[2] + normal[2] * extrude_dist]
        new_v2 = [v2[0] + normal[0] * extrude_dist, 
                 v2[1] + normal[1] * extrude_dist, 
                 v2[2] + normal[2] * extrude_dist]
        new_v3 = [v3[0] + normal[0] * extrude_dist, 
                 v3[1] + normal[1] * extrude_dist, 
                 v3[2] + normal[2] * extrude_dist]
        
        # 添加随机变形
        for v in [new_v1, new_v2, new_v3]:
            v[0] += np.random.normal(0, deform_factor * extrude_dist)
            v[1] += np.random.normal(0, deform_factor * extrude_dist)
            v[2] += np.random.normal(0, deform_factor * extrude_dist)
        
        # 添加新顶点到顶点列表
        v1_idx = vertex_count
        v2_idx = vertex_count + 1
        v3_idx = vertex_count + 2
        vertex_count += 3
        
        new_vertices.extend([new_v1, new_v2, new_v3])
        
        # 添加三个侧面 - 每个边增加2个三角形而不是1个，细分以增加面数
        # 侧面1
        new_faces.append([face[0], face[1], v1_idx])
        mid1 = [(vertices[face[0]][j] + vertices[face[1]][j])/2 for j in range(3)]
        mid1 = [mid1[0] + normal[0] * extrude_dist * 0.5,
               mid1[1] + normal[1] * extrude_dist * 0.5,
               mid1[2] + normal[2] * extrude_dist * 0.5]
        mid1_idx = vertex_count
        vertex_count += 1
        new_vertices.append(mid1)
        new_faces.append([face[0], mid1_idx, v1_idx])
        new_faces.append([face[1], v2_idx, mid1_idx])
        
        # 侧面2
        new_faces.append([face[1], face[2], v2_idx])
        mid2 = [(vertices[face[1]][j] + vertices[face[2]][j])/2 for j in range(3)]
        mid2 = [mid2[0] + normal[0] * extrude_dist * 0.5,
               mid2[1] + normal[1] * extrude_dist * 0.5,
               mid2[2] + normal[2] * extrude_dist * 0.5]
        mid2_idx = vertex_count
        vertex_count += 1
        new_vertices.append(mid2)
        new_faces.append([face[1], mid2_idx, v2_idx])
        new_faces.append([face[2], v3_idx, mid2_idx])
        
        # 侧面3
        new_faces.append([face[2], face[0], v3_idx])
        mid3 = [(vertices[face[2]][j] + vertices[face[0]][j])/2 for j in range(3)]
        mid3 = [mid3[0] + normal[0] * extrude_dist * 0.5,
               mid3[1] + normal[1] * extrude_dist * 0.5,
               mid3[2] + normal[2] * extrude_dist * 0.5]
        mid3_idx = vertex_count
        vertex_count += 1
        new_vertices.append(mid3)
        new_faces.append([face[2], mid3_idx, v3_idx])
        new_faces.append([face[0], v1_idx, mid3_idx])
        
        # 顶面 - 将一个三角形分成四个
        center_point = [(new_v1[j] + new_v2[j] + new_v3[j])/3 for j in range(3)]
        center_idx = vertex_count
        vertex_count += 1
        new_vertices.append(center_point)
        new_faces.append([v1_idx, v2_idx, center_idx])
        new_faces.append([v2_idx, v3_idx, center_idx])
        new_faces.append([v3_idx, v1_idx, center_idx])
        
        # 打印进度
        processed += 1
        if processed % 50000 == 0:
            print(f"已处理 {processed}/{extrude_count} 个挤出操作")
    
    return new_vertices, new_faces

def save_to_nas(vertices, faces, output_filename):
    """保存模型为NAS文件"""
    with open(output_filename, 'w') as f:
        print(f"写入文件 {output_filename}...")
        f.write("$ 生成的复杂3D门格海绵分形立体模型\n")
        f.write("BEGIN BULK\n")
        
        # 写入点
        for i, vertex in enumerate(vertices):
            # 写入GRID*格式（2行）
            node_id = i + 1
            line1 = f"GRID*   {node_id:<16}{0:<16}{vertex[0]:<16.8E}{vertex[1]:<16.8E}*       "
            line2 = f"*       {vertex[2]:<16.8E}"
            f.write(line1 + "\n")
            f.write(line2 + "\n")
        
        # 写入三角形面
        for i, face in enumerate(faces):
            element_id = i + 1
            # NAS文件的索引从1开始
            n1, n2, n3 = face[0] + 1, face[1] + 1, face[2] + 1
            f.write(f"CTRIA3  {element_id:<8}{1:<8}{n1:<8}{n2:<8}{n3:<8}\n")

def main():
    start_time = time.time()
    
    # 设置目标面数（确保超过100万）
    target_faces = 1200000
    
    # 设置门格海绵参数
    center = [0, 0, 0]
    size = 2.0
    level = 4  # 分形层级增加到4
    
    print(f"生成门格海绵分形，层级: {level}...")
    vertices, faces = generate_menger_sponge(center, size, level)
    print(f"基础模型生成完成，生成了 {len(vertices)} 个顶点和 {len(faces)} 个面")
    
    # 添加随机噪声使表面不那么规则
    print("为表面添加随机噪声...")
    vertices = add_random_noise(vertices, noise_level=0.01)
    
    # 如果面数不够，则进行挤出和变形
    if len(faces) < target_faces:
        print(f"面数不足，进行挤出和变形操作，当前面数: {len(faces)}")
        # 增加挤出操作的数量以生成更多面
        vertices, faces = extrude_and_deform(vertices, faces, deform_factor=0.3)
        print(f"第一次挤出变形后面数: {len(faces)}")
        
        # 如果面数还不够，继续挤出
        if len(faces) < target_faces:
            print(f"面数仍然不足，进行第二次挤出和变形操作")
            vertices, faces = extrude_and_deform(vertices, faces, deform_factor=0.2)
            print(f"第二次挤出变形后面数: {len(faces)}")
    
    # 如果面数过多，则进行简化
    if len(faces) > target_faces * 1.5:
        vertices, faces = decimate_mesh(vertices, faces, target_faces)
    
    # 创建输出目录
    os.makedirs("src/data", exist_ok=True)
    
    # 保存为NAS文件
    output_filename = "src/data/complex_3d_model.nas"
    save_to_nas(vertices, faces, output_filename)
    
    end_time = time.time()
    
    # 计算文件大小
    file_size_mb = os.path.getsize(output_filename) / (1024 * 1024)
    
    print(f"\n生成完成!")
    print(f"生成了 {len(vertices)} 个顶点和 {len(faces)} 个面")
    print(f"文件已保存至: {output_filename}")
    print(f"文件大小: {file_size_mb:.2f} MB")
    print(f"生成耗时: {end_time - start_time:.2f} 秒")

if __name__ == "__main__":
    main() 