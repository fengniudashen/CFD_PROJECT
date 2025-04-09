import numpy as np
import os

def create_cube_stl(filename: str, size: float = 1.0):
    """创建一个立方体的ASCII STL文件"""
    # 确保目标目录存在
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        f.write("solid cube\n")
        
        # 定义立方体的8个顶点
        vertices = np.array([
            [0, 0, 0], [size, 0, 0], [size, size, 0], [0, size, 0],
            [0, 0, size], [size, 0, size], [size, size, size], [0, size, size]
        ])
        
        # 定义6个面，每个面2个三角形
        faces = [
            # 前面
            ([0,1,2], [0,2,3]),
            # 后面
            ([4,6,5], [4,7,6]),
            # 顶面
            ([3,2,6], [3,6,7]),
            # 底面
            ([0,5,1], [0,4,5]),
            # 右面
            ([1,5,6], [1,6,2]),
            # 左面
            ([0,3,7], [0,7,4])
        ]
        
        # 写入每个三角形
        for face_pair in faces:
            for triangle in face_pair:
                v1, v2, v3 = vertices[triangle]
                # 计算法向量
                normal = np.cross(v2 - v1, v3 - v1)
                normal = normal / np.linalg.norm(normal)
                
                f.write(f"facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
                f.write("  outer loop\n")
                f.write(f"    vertex {v1[0]:.6f} {v1[1]:.6f} {v1[2]:.6f}\n")
                f.write(f"    vertex {v2[0]:.6f} {v2[1]:.6f} {v2[2]:.6f}\n")
                f.write(f"    vertex {v3[0]:.6f} {v3[1]:.6f} {v3[2]:.6f}\n")
                f.write("  endloop\n")
                f.write("endfacet\n")
        
        f.write("endsolid cube\n")

def create_cube_nas(filename: str, size: float = 1.0):
    """创建一个立方体的Nastran文件"""
    # 确保目标目录存在
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        # 写入头部
        f.write("$ Nastran input file for a cube\n")
        
        # 写入8个节点，使用固定格式
        nodes = [
            [1, 0.0, 0.0, 0.0],
            [2, size, 0.0, 0.0],
            [3, size, size, 0.0],
            [4, 0.0, size, 0.0],
            [5, 0.0, 0.0, size],
            [6, size, 0.0, size],
            [7, size, size, size],
            [8, 0.0, size, size]
        ]
        
        # 使用固定格式写入GRID
        for node in nodes:
            f.write(f"GRID    {node[0]:8d}        {node[1]:8.1f}{node[2]:8.1f}{node[3]:8.1f}\n")
        
        # 写入六面体单元，使用固定格式
        f.write("CHEXA   1       1       1       2       3       4       5       6\n")
        f.write("+           7       8\n")  # 续行标记为+，从第8列开始写节点ID

if __name__ == "__main__":
    # 创建测试文件
    create_cube_stl("data/test_cube.stl", 1.0)
    create_cube_nas("data/test_cube.nas", 1.0) 