#!/usr/bin/env python
"""
加载和显示large_star.nas文件的3D模型
"""
import sys
import os
import time
import numpy as np
from PyQt5.QtWidgets import QApplication
from mesh_viewer_qt import MeshViewerQt

def load_nas_file(file_path):
    """
    读取NAS文件并转换为mesh_viewer_qt需要的格式
    
    Args:
        file_path: NAS文件路径
        
    Returns:
        包含vertices, faces, normals的字典
    """
    print(f"正在读取NAS文件: {file_path}")
    start_time = time.time()
    
    # 直接读取NAS文件
    vertices = []
    faces = []
    vertex_id_map = {}  # 用于存储NAS文件中的节点ID到索引的映射
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    print(f"文件加载完成，开始解析数据，共{len(lines)}行...")
    
    # 第一遍：读取所有顶点
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('GRID*'):
            # GRID*格式（长格式，占两行）
            if i + 1 < len(lines):
                parts1 = line.split()
                next_line = lines[i+1].strip()
                
                if next_line.startswith('*'):
                    parts2 = next_line.split()
                    
                    try:
                        # 解析节点ID和坐标
                        node_id = int(parts1[1])
                        x = float(parts1[3])
                        y = float(parts1[4])
                        z = float(parts2[1])
                        
                        # 添加到顶点列表并记录ID映射
                        vertex_id_map[node_id] = len(vertices)
                        vertices.append([x, y, z])
                    except (ValueError, IndexError):
                        pass
                    
                    i += 1  # 跳过已处理的下一行
        i += 1
        
        # 打印进度
        if i % 500000 == 0:
            print(f"已处理 {i}/{len(lines)} 行，解析了 {len(vertices)} 个顶点...")
    
    print(f"顶点解析完成，共 {len(vertices)} 个顶点。开始解析面片...")
    
    # 第二遍：读取所有三角形面片
    face_count = 0
    for i, line in enumerate(lines):
        if line.startswith('CTRIA3'):
            parts = line.split()
            if len(parts) >= 6:
                try:
                    # NAS文件中的节点ID从1开始，需要转换为从0开始的索引
                    n1 = int(parts[3])
                    n2 = int(parts[4])
                    n3 = int(parts[5])
                    
                    # 使用之前建立的映射转换ID
                    if n1 in vertex_id_map and n2 in vertex_id_map and n3 in vertex_id_map:
                        v1 = vertex_id_map[n1]
                        v2 = vertex_id_map[n2]
                        v3 = vertex_id_map[n3]
                        faces.append([v1, v2, v3])
                        face_count += 1
                        
                        # 打印进度
                        if face_count % 100000 == 0:
                            print(f"已解析 {face_count} 个面片...")
                except (ValueError, IndexError):
                    pass
    
    # 转换为numpy数组
    vertices = np.array(vertices, dtype=np.float32)
    faces = np.array(faces, dtype=np.int32)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"解析完成，耗时 {duration:.2f} 秒")
    print(f"模型信息：{len(vertices)} 个顶点，{len(faces)} 个面片")
    
    # 计算顶点法向量
    print("正在计算法向量...")
    normals = compute_normals(vertices, faces)
    
    print("模型处理完成，准备渲染...")
    
    return {
        'vertices': vertices,
        'faces': faces,
        'normals': normals
    }

def compute_normals(vertices, faces):
    """计算顶点法向量"""
    normals = np.zeros_like(vertices)
    
    # 只处理部分面以提高计算速度
    max_faces = min(len(faces), 100000)  # 限制处理的面数以提高性能
    print(f"为提高性能，仅计算 {max_faces}/{len(faces)} 个面片的法向量...")
    
    # 计算每个面的法向量
    for i, face in enumerate(faces[:max_faces]):
        if len(face) >= 3:
            v1, v2, v3 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
            # 计算两条边
            edge1 = v2 - v1
            edge2 = v3 - v1
            # 计算面法向量
            face_normal = np.cross(edge1, edge2)
            # 归一化
            norm = np.linalg.norm(face_normal)
            if norm > 0:
                face_normal /= norm
            # 将面法向量加到顶点
            for idx in face:
                normals[idx] += face_normal
    
    # 归一化顶点法向量
    for i in range(len(normals)):
        norm = np.linalg.norm(normals[i])
        if norm > 0:
            normals[i] /= norm
        else:
            normals[i] = np.array([0, 0, 1])  # 默认法向量
    
    return normals

def main():
    # 设置NAS文件路径
    nas_file = os.path.join("src", "data", "large_star.nas")
    
    # 确保文件存在
    if not os.path.exists(nas_file):
        print(f"错误: 文件不存在 {nas_file}")
        print("请先运行 generate_large_nas.py 生成文件")
        return 1
    
    # 读取NAS文件
    mesh_data = load_nas_file(nas_file)
    
    # 检查是否成功读取
    if len(mesh_data['vertices']) == 0 or len(mesh_data['faces']) == 0:
        print("错误: 无法从文件中提取有效的网格数据")
        return 1
    
    print(f"开始显示3D模型，网格大小: {len(mesh_data['vertices'])}个顶点，{len(mesh_data['faces'])}个面片")
    
    # 使用Qt显示器显示模型
    app = QApplication(sys.argv)
    viewer = MeshViewerQt(mesh_data)
    viewer.show()
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main()) 