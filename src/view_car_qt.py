#!/usr/bin/env python
"""
演示脚本：读取car_model.nas文件并使用mesh_viewer_qt.py显示
"""
import sys
import os
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
    
    # 直接读取NAS文件
    vertices = []
    faces = []
    vertex_id_map = {}  # 用于存储NAS文件中的节点ID到索引的映射
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
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
    
    # 第二遍：读取所有三角形面片
    for line in lines:
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
                except (ValueError, IndexError):
                    pass
    
    # 转换为numpy数组
    vertices = np.array(vertices, dtype=np.float32)
    faces = np.array(faces, dtype=np.int32)
    
    # 计算顶点法向量
    normals = compute_normals(vertices, faces)
    
    print(f"读取完成，顶点数: {len(vertices)}，面片数: {len(faces)}")
    
    return {
        'vertices': vertices,
        'faces': faces,
        'normals': normals
    }

def compute_normals(vertices, faces):
    """计算顶点法向量"""
    normals = np.zeros_like(vertices)
    
    # 计算每个面的法向量
    for face in faces:
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
    # 检查命令行参数
    if len(sys.argv) > 1:
        # 使用命令行参数作为文件路径
        nas_file = sys.argv[1]
    else:
        # 使用默认文件路径
        nas_file = os.path.join("data", "car_model.nas")
    
    # 确保文件存在
    if not os.path.exists(nas_file):
        print(f"错误: 文件不存在 {nas_file}")
        return 1
    
    # 读取NAS文件
    mesh_data = load_nas_file(nas_file)
    
    # 检查是否成功读取
    if len(mesh_data['vertices']) == 0 or len(mesh_data['faces']) == 0:
        print("错误: 无法从文件中提取有效的网格数据")
        return 1
    
    print(f"开始显示3D模型，模型大小: {len(mesh_data['faces'])}面")
    
    # 使用Qt显示器显示模型
    app = QApplication(sys.argv)
    viewer = MeshViewerQt(mesh_data)
    viewer.show()
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main()) 