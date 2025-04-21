"""
生成穿透测试模型

创建一个包含穿透面片的3D模型，用于测试穿透面检测算法
"""

import numpy as np
import os
import math

def create_sphere(center, radius, num_segments=10):
    """
    创建一个球体
    
    参数:
    center: 球心坐标 [x, y, z]
    radius: 球半径
    num_segments: 分段数，影响球面三角形的数量
    
    返回:
    vertices: 顶点列表
    faces: 面片列表，每个面片包含三个顶点索引
    """
    vertices = []
    faces = []
    
    # 添加北极点
    north_pole_idx = len(vertices)
    vertices.append([center[0], center[1], center[2] + radius])
    
    # 生成球面上的其他顶点
    for i in range(num_segments):
        phi = math.pi * (i + 1) / num_segments  # 从北极到南极的角度
        for j in range(num_segments * 2):
            theta = 2.0 * math.pi * j / (num_segments * 2)  # 围绕Z轴的角度
            
            x = center[0] + radius * math.sin(phi) * math.cos(theta)
            y = center[1] + radius * math.sin(phi) * math.sin(theta)
            z = center[2] + radius * math.cos(phi)
            
            vertices.append([x, y, z])
    
    # 添加南极点
    south_pole_idx = len(vertices)
    vertices.append([center[0], center[1], center[2] - radius])
    
    # 生成北极冠面片
    start_idx = north_pole_idx + 1
    for i in range(num_segments * 2):
        v1 = north_pole_idx
        v2 = start_idx + i
        v3 = start_idx + (i + 1) % (num_segments * 2)
        faces.append([v1, v2, v3])
    
    # 生成中间部分的面片
    for i in range(num_segments - 1):
        for j in range(num_segments * 2):
            row1_start = north_pole_idx + 1 + i * (num_segments * 2)
            row2_start = north_pole_idx + 1 + (i + 1) * (num_segments * 2)
            
            v1 = row1_start + j
            v2 = row1_start + (j + 1) % (num_segments * 2)
            v3 = row2_start + (j + 1) % (num_segments * 2)
            v4 = row2_start + j
            
            # 每个方形分成两个三角形
            faces.append([v1, v2, v3])
            faces.append([v1, v3, v4])
    
    # 生成南极冠面片
    start_idx = north_pole_idx + 1 + (num_segments - 1) * (num_segments * 2)
    for i in range(num_segments * 2):
        v1 = south_pole_idx
        v2 = start_idx + (i + 1) % (num_segments * 2)
        v3 = start_idx + i
        faces.append([v1, v2, v3])
    
    return vertices, faces

def create_cube(center, size):
    """
    创建一个立方体
    
    参数:
    center: 立方体中心坐标 [x, y, z]
    size: 立方体边长
    
    返回:
    vertices: 顶点列表
    faces: 面片列表，每个面片包含三个顶点索引
    """
    half_size = size / 2
    
    # 定义8个顶点
    vertices = [
        [center[0] - half_size, center[1] - half_size, center[2] - half_size],  # 0: 左下后
        [center[0] + half_size, center[1] - half_size, center[2] - half_size],  # 1: 右下后
        [center[0] + half_size, center[1] + half_size, center[2] - half_size],  # 2: 右上后
        [center[0] - half_size, center[1] + half_size, center[2] - half_size],  # 3: 左上后
        [center[0] - half_size, center[1] - half_size, center[2] + half_size],  # 4: 左下前
        [center[0] + half_size, center[1] - half_size, center[2] + half_size],  # 5: 右下前
        [center[0] + half_size, center[1] + half_size, center[2] + half_size],  # 6: 右上前
        [center[0] - half_size, center[1] + half_size, center[2] + half_size]   # 7: 左上前
    ]
    
    # 定义立方体的12个三角形面片
    faces = [
        [0, 1, 2], [0, 2, 3],  # 后面
        [4, 6, 5], [4, 7, 6],  # 前面
        [0, 4, 1], [1, 4, 5],  # 下面
        [2, 6, 3], [3, 6, 7],  # 上面
        [0, 3, 4], [3, 7, 4],  # 左面
        [1, 5, 2], [2, 5, 6]   # 右面
    ]
    
    return vertices, faces

def create_cylinder(center, radius, height, num_segments=16):
    """
    创建一个圆柱体
    
    参数:
    center: 圆柱体中心坐标 [x, y, z]
    radius: 圆柱体半径
    height: 圆柱体高度
    num_segments: 圆周分段数
    
    返回:
    vertices: 顶点列表
    faces: 面片列表，每个面片包含三个顶点索引
    """
    vertices = []
    faces = []
    
    half_height = height / 2
    
    # 生成上下两个圆面的顶点
    for i in range(num_segments):
        angle = 2.0 * math.pi * i / num_segments
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        
        # 下底面顶点
        vertices.append([x, y, center[2] - half_height])
        # 上底面顶点
        vertices.append([x, y, center[2] + half_height])
    
    # 添加两个中心点
    bottom_center_idx = len(vertices)
    vertices.append([center[0], center[1], center[2] - half_height])
    top_center_idx = len(vertices)
    vertices.append([center[0], center[1], center[2] + half_height])
    
    # 生成侧面的三角形
    for i in range(num_segments):
        # 当前边的两个顶点
        v1_bottom = i * 2
        v1_top = i * 2 + 1
        # 下一个边的两个顶点（循环回到第一个顶点）
        v2_bottom = ((i + 1) % num_segments) * 2
        v2_top = ((i + 1) % num_segments) * 2 + 1
        
        # 添加两个三角形形成一个矩形侧面
        faces.append([v1_bottom, v2_bottom, v2_top])
        faces.append([v1_bottom, v2_top, v1_top])
        
        # 添加底面三角形
        faces.append([bottom_center_idx, v2_bottom, v1_bottom])
        
        # 添加顶面三角形
        faces.append([top_center_idx, v1_top, v2_top])
    
    return vertices, faces

def generate_test_model():
    """
    生成一个包含穿透面的测试模型
    
    返回:
    vertices: 顶点坐标数组
    faces: 面片索引数组
    """
    all_vertices = []
    all_faces = []
    
    # 在中心创建一个大球体
    sphere_vertices, sphere_faces = create_sphere([0, 0, 0], 15.0, 15)
    
    # 添加顶点和面片，更新面片的顶点索引
    sphere_offset = len(all_vertices)
    all_vertices.extend(sphere_vertices)
    for face in sphere_faces:
        all_faces.append([face[0] + sphere_offset, face[1] + sphere_offset, face[2] + sphere_offset])
    
    # 创建穿刺立方体
    num_cubes = 15
    for i in range(num_cubes):
        angle = 2 * math.pi * i / num_cubes
        distance = 10.0
        
        # 计算立方体的中心位置
        cube_center = [
            distance * math.cos(angle),
            distance * math.sin(angle),
            0
        ]
        
        cube_vertices, cube_faces = create_cube(cube_center, 8.0)
        
        # 添加顶点和面片，更新面片的顶点索引
        cube_offset = len(all_vertices)
        all_vertices.extend(cube_vertices)
        for face in cube_faces:
            all_faces.append([face[0] + cube_offset, face[1] + cube_offset, face[2] + cube_offset])
    
    # 创建穿刺圆柱体
    num_cylinders = 12
    for i in range(num_cylinders):
        angle = 2 * math.pi * i / num_cylinders
        distance = 12.0
        
        # 倾斜放置的圆柱体
        cylinder_center = [
            distance * math.cos(angle),
            distance * math.sin(angle),
            3.0 * math.sin(3 * angle)  # 上下波动
        ]
        
        cylinder_vertices, cylinder_faces = create_cylinder(cylinder_center, 3.0, 12.0)
        
        # 添加顶点和面片，更新面片的顶点索引
        cylinder_offset = len(all_vertices)
        all_vertices.extend(cylinder_vertices)
        for face in cylinder_faces:
            all_faces.append([face[0] + cylinder_offset, face[1] + cylinder_offset, face[2] + cylinder_offset])
    
    # 添加一些小球体，确保它们与立方体和圆柱体相交
    num_spheres = 20
    for i in range(num_spheres):
        angle = 2 * math.pi * i / num_spheres
        distance = 13.0
        
        # 计算球体的中心位置
        sphere_center = [
            distance * math.cos(angle),
            distance * math.sin(angle),
            5.0 * math.cos(5 * angle)  # 上下波动
        ]
        
        small_sphere_vertices, small_sphere_faces = create_sphere(sphere_center, 4.0, 8)
        
        # 添加顶点和面片，更新面片的顶点索引
        small_sphere_offset = len(all_vertices)
        all_vertices.extend(small_sphere_vertices)
        for face in small_sphere_faces:
            all_faces.append([face[0] + small_sphere_offset, face[1] + small_sphere_offset, face[2] + small_sphere_offset])
    
    return np.array(all_vertices), np.array(all_faces)

def write_nas_file(filename, vertices, faces):
    """
    将顶点和面片数据写入NAS文件
    
    参数:
    filename: 输出的NAS文件名
    vertices: 顶点坐标数组
    faces: 面片索引数组
    """
    # 创建目录（如果不存在）
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        # 写入头部
        f.write("$ Generated test model for pierced faces detection\n")
        f.write(f"$ Vertices: {len(vertices)}, Faces: {len(faces)}\n")
        
        # 写入顶点（GRID格式）
        for i, (x, y, z) in enumerate(vertices, 1):
            f.write(f"GRID    {i:8d}        {x:16.8f}{y:16.8f}{z:16.8f}\n")
        
        # 写入面片（CTRIA3格式）
        for i, (v1, v2, v3) in enumerate(faces, 1):
            # NAS文件的索引从1开始，所以要加1
            f.write(f"CTRIA3  {i:8d}       1{v1+1:8d}{v2+1:8d}{v3+1:8d}\n")
        
        # 写入材料和属性（简化）
        f.write("MAT1     1      2.1+5           0.3\n")
        f.write("PSHELL   1       1      1.\n")
        f.write("ENDDATA\n")

if __name__ == "__main__":
    # 生成模型
    print("生成穿透测试模型...")
    vertices, faces = generate_test_model()
    print(f"生成了 {len(vertices)} 个顶点和 {len(faces)} 个面片")
    
    # 输出文件路径
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "pierced_test_model.nas")
    
    # 写入NAS文件
    write_nas_file(output_file, vertices, faces)
    print(f"模型已保存到: {output_file}")
    
    print("可以使用以下命令测试穿透面检测:")
    print(f"python src/test_pierced_faces_nas.py --sample 0 --model {output_file}") 