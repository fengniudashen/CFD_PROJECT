#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
面片邻近性分析模块

该模块提供了基于STAR-CCM+方法的三角形面片邻近性分析算法，用于检测网格中距离过近的面片。
实现了以下功能：
- 精确的面片间距离计算
- 考虑面片法线角度关系的邻近性判定
- 空间哈希网格加速空间查询
- 面片特征尺寸自适应的阈值判定

主要函数:
- detect_face_proximity: 检测网格中距离过近的面片
"""

import numpy as np
import time
from typing import Set, List, Tuple, Dict, Callable, Optional


def detect_face_proximity(faces: np.ndarray, 
                          vertices: np.ndarray, 
                          threshold: float = 0.1, 
                          progress_callback: Optional[Callable] = None) -> Set[int]:
    """
    实现STAR-CCM+式的面片邻近性检测算法
    
    参数:
        faces: 面片索引数组，形状为(n_faces, 3)
        vertices: 顶点坐标数组，形状为(n_vertices, 3)
        threshold: 邻近性阈值(相对于面片特征尺寸的比例)，默认为0.1
        progress_callback: 进度回调函数，接收参数(percentage, message)
        
    返回:
        邻近面片的索引集合
    """
    start_time = time.time()

    # 报告初始进度
    if progress_callback:
        progress_callback(0, "正在准备邻近性分析数据...")
    
    # 计算面片特征数据
    char_lengths, face_centers, face_min, face_max, face_normals = compute_face_data(faces, vertices)
    
    if progress_callback:
        progress_callback(5, "构建空间索引...")
    
    # 创建空间哈希网格加速查询
    grid, global_min, grid_dims, grid_size = create_spatial_hash_grid(face_min, face_max, char_lengths)
    
    # 计算参考特征尺寸
    median_length = np.median(char_lengths)
    proximity_threshold = threshold * median_length
    
    if progress_callback:
        progress_callback(10, f"开始检测邻近面片 (阈值: {proximity_threshold:.4f})...")
    
    # 构建面片邻接关系
    if progress_callback:
        progress_callback(15, "构建面片邻接关系...")
    
    adjacency = build_adjacency(faces)
    
    # 准备分析面片对
    if progress_callback:
        progress_callback(20, "筛选邻近面片候选...")
    
    # 使用空间哈希网格确定潜在的邻近面片对
    potential_pairs = []
    last_progress = 20
    total_faces = len(faces)
    
    for i in range(total_faces):
        if progress_callback and i % 1000 == 0:
            current_progress = 20 + int(i / total_faces * 20)
            if current_progress > last_progress:
                progress_callback(current_progress, f"筛选邻近面片候选... ({i}/{total_faces})")
                last_progress = current_progress
        
        # 获取当前面片的边界框
        min_coords = face_min[i]
        max_coords = face_max[i]
        
        # 扩展搜索范围，确保邻近面片不会被遗漏
        extended_min = min_coords - proximity_threshold
        extended_max = max_coords + proximity_threshold
        
        # 计算对应的网格索引
        min_grid_idx = np.floor((extended_min - global_min) / grid_size).astype(int)
        max_grid_idx = np.ceil((extended_max - global_min) / grid_size).astype(int)
        
        # 限制索引范围在有效范围内
        min_grid_idx = np.maximum(min_grid_idx, [0, 0, 0])
        max_grid_idx = np.minimum(max_grid_idx, grid_dims - 1)
        
        # 获取所有可能的邻近面片
        potential_neighbors = set()
        
        for x in range(min_grid_idx[0], max_grid_idx[0] + 1):
            for y in range(min_grid_idx[1], max_grid_idx[1] + 1):
                for z in range(min_grid_idx[2], max_grid_idx[2] + 1):
                    cell_key = (x, y, z)
                    if cell_key in grid:
                        potential_neighbors.update(grid[cell_key])
        
        # 排除自身和直接邻接的面片
        for j in potential_neighbors:
            if j <= i or j in adjacency[i]:  # 排除自身和已知邻接的面片
                continue
            potential_pairs.append((i, j))
    
    if progress_callback:
        progress_callback(40, f"发现 {len(potential_pairs)} 对潜在邻近面片，正在详细分析...")
    
    # 分析潜在邻近面片对
    proximity_faces = set()
    
    # 单进程处理
    for idx, (face_i, face_j) in enumerate(potential_pairs):
        if progress_callback and idx % 1000 == 0:
            progress_value = 40 + int(idx / len(potential_pairs) * 50)
            progress_callback(progress_value, f"分析面片对 {idx}/{len(potential_pairs)}...")
        
        # 检查面片间距离和法线角度
        if is_proximity(face_i, face_j, face_centers, face_normals, char_lengths, 
                       proximity_threshold, vertices, faces):
            proximity_faces.add(face_i)
            proximity_faces.add(face_j)
    
    if progress_callback:
        progress_callback(95, f"分析完成. 发现 {len(proximity_faces)} 个邻近面片.")
    
    elapsed_time = time.time() - start_time
    if progress_callback:
        progress_callback(100, f"邻近性分析完成，用时 {elapsed_time:.2f} 秒.")
    
    return proximity_faces


def compute_face_data(faces: np.ndarray, vertices: np.ndarray) -> Tuple:
    """
    计算面片的特征数据，包括特征尺寸、中心点、包围盒和法线
    
    参数:
        faces: 面片数组，形状为(n_faces, 3)
        vertices: 顶点坐标数组，形状为(n_vertices, 3)
        
    返回:
        char_lengths: 特征尺寸数组
        face_centers: 面片中心点数组
        face_min: 面片包围盒最小点数组
        face_max: 面片包围盒最大点数组
        face_normals: 面片法线数组
    """
    # 获取所有面片的顶点坐标，形状为(n_faces, 3, 3)
    face_vertices = vertices[faces]
    
    # 计算面片法线 - 使用叉积
    v1 = face_vertices[:, 1] - face_vertices[:, 0]  # 第一条边向量
    v2 = face_vertices[:, 2] - face_vertices[:, 0]  # 第二条边向量
    
    # 叉乘计算面法线
    cross_products = np.cross(v1, v2)
    
    # 计算法线长度（同时也是面积的两倍）
    norms = np.linalg.norm(cross_products, axis=1, keepdims=True)
    
    # 防止除零
    norms[norms < 1e-10] = 1.0
    
    # 单位化法线向量
    face_normals = cross_products / norms
    
    # 计算面积
    areas = 0.5 * norms.flatten()
    
    # 计算特征尺寸 - 使用面积的平方根，类似于STAR-CCM+
    char_lengths = np.sqrt(np.maximum(areas, 1e-10))  # 避免零面积导致的数值问题
    
    # 计算包围盒和中心点
    face_min = np.min(face_vertices, axis=1)  # 形状为(n_faces, 3)
    face_max = np.max(face_vertices, axis=1)  # 形状为(n_faces, 3)
    face_centers = np.mean(face_vertices, axis=1)  # 形状为(n_faces, 3)
    
    return char_lengths, face_centers, face_min, face_max, face_normals


def create_spatial_hash_grid(face_min: np.ndarray, face_max: np.ndarray, char_lengths: np.ndarray) -> Tuple:
    """
    创建空间哈希网格用于快速空间查询
    
    参数:
        face_min: 面片包围盒最小点数组
        face_max: 面片包围盒最大点数组
        char_lengths: 特征尺寸数组
        
    返回:
        grid: 空间哈希网格
        global_min: 全局最小坐标
        grid_dims: 网格尺寸
        grid_size: 网格单元大小
    """
    # 确定网格大小 - 使用平均特征尺寸的倍数
    mean_char_length = np.mean(char_lengths)
    grid_size = mean_char_length * 3  # 可调整的参数
    
    # 计算空间范围
    global_min = np.min(face_min, axis=0)
    global_max = np.max(face_max, axis=0)
    
    # 计算网格尺寸
    grid_dims = np.ceil((global_max - global_min) / grid_size).astype(int)
    grid_dims = np.maximum(grid_dims, 1)  # 确保至少有1个单元
    
    # 创建空间哈希网格
    grid = {}
    
    # 计算面片在哪些网格单元中
    for i in range(len(face_min)):
        # 计算面片包围盒覆盖的网格单元
        min_indices = np.floor((face_min[i] - global_min) / grid_size).astype(int)
        max_indices = np.ceil((face_max[i] - global_min) / grid_size).astype(int)
        
        # 限制索引在有效范围内
        min_indices = np.maximum(min_indices, 0)
        max_indices = np.minimum(max_indices, grid_dims - 1)
        
        # 将面片添加到每个覆盖的网格单元
        for x in range(min_indices[0], max_indices[0] + 1):
            for y in range(min_indices[1], max_indices[1] + 1):
                for z in range(min_indices[2], max_indices[2] + 1):
                    cell_key = (x, y, z)
                    if cell_key not in grid:
                        grid[cell_key] = []
                    grid[cell_key].append(i)
    
    return grid, global_min, grid_dims, grid_size


def build_adjacency(faces: np.ndarray) -> List[Set[int]]:
    """
    构建面片邻接关系
    
    参数:
        faces: 网格面片数组，形状为(n_faces, 3)
        
    返回:
        face_adjacency: 面片邻接关系，每个面片的相邻面片集合
    """
    # 创建边到面片的映射
    edge_to_faces = {}
    
    # 为每个面片构建边
    for i, face in enumerate(faces):
        # 对每个面片的三条边
        for j in range(3):
            # 确保边的顺序一致（顶点索引小的在前）
            edge = tuple(sorted([face[j], face[(j+1)%3]]))
            if edge not in edge_to_faces:
                edge_to_faces[edge] = []
            edge_to_faces[edge].append(i)
    
    # 构建面片邻接关系
    face_adjacency = [set() for _ in range(len(faces))]
    
    for edge, connected_faces in edge_to_faces.items():
        # 如果一条边连接了多个面片，这些面片互相邻接
        for i in range(len(connected_faces)):
            for j in range(i+1, len(connected_faces)):
                face_adjacency[connected_faces[i]].add(connected_faces[j])
                face_adjacency[connected_faces[j]].add(connected_faces[i])
    
    return face_adjacency


def is_proximity(face_i: int, face_j: int, face_centers: np.ndarray, 
                face_normals: np.ndarray, char_lengths: np.ndarray,
                proximity_threshold: float, vertices: np.ndarray, 
                faces: np.ndarray) -> bool:
    """
    使用STAR-CCM+风格的标准检查两个面片是否邻近
    
    参数:
        face_i, face_j: 待检查的两个面片索引
        face_centers: 面片中心点数组
        face_normals: 面片法线数组
        char_lengths: 面片特征尺寸数组
        proximity_threshold: 邻近性阈值
        vertices: 顶点坐标数组
        faces: 面片索引数组
        
    返回:
        布尔值，表示两个面片是否邻近
    """
    # 获取面片中心和法线
    center_i = face_centers[face_i]
    center_j = face_centers[face_j]
    
    # 快速检查: 根据中心点距离进行初步筛选
    center_distance = np.linalg.norm(center_i - center_j)
    
    # 如果中心点距离已经远大于阈值，可以直接排除
    max_char_length = max(char_lengths[face_i], char_lengths[face_j])
    if center_distance > proximity_threshold + max_char_length:
        return False
    
    # 获取法线向量
    normal_i = face_normals[face_i]
    normal_j = face_normals[face_j]
    
    # STAR-CCM+ 风格的角度影响: 法线夹角越大，容忍的距离越小
    # 计算法线夹角的余弦值
    cos_angle = np.clip(np.dot(normal_i, normal_j), -1.0, 1.0)
    angle_factor = 0.5 * (1.0 + cos_angle)  # 从0.0(180°)到1.0(0°)的因子
    
    # 根据角度调整阈值: 平行面片用完整阈值，垂直面片用一半阈值
    adjusted_threshold = proximity_threshold * (0.5 + 0.5 * angle_factor)
    
    # 获取面片顶点
    tri1_verts = vertices[faces[face_i]]
    tri2_verts = vertices[faces[face_j]]
    
    # 计算两个面片之间的精确距离
    min_distance = triangle_distance(tri1_verts, tri2_verts, normal_i, normal_j)
    
    # 根据调整后的阈值判断是否邻近
    return min_distance < adjusted_threshold


def triangle_distance(tri1: np.ndarray, tri2: np.ndarray, normal1: np.ndarray, normal2: np.ndarray) -> float:
    """
    计算两个三角形之间的最短距离
    
    参数:
        tri1: 第一个三角形的三个顶点
        tri2: 第二个三角形的三个顶点
        normal1: 第一个三角形的法线
        normal2: 第二个三角形的法线
        
    返回:
        两个三角形之间的最短距离
    """
    # 1. 计算每个点到另一个三角形的距离
    min_dist = float('inf')
    
    # 点到面的距离
    for point in tri1:
        dist = point_to_triangle_distance(point, tri2, normal2)
        min_dist = min(min_dist, dist)
    
    for point in tri2:
        dist = point_to_triangle_distance(point, tri1, normal1)
        min_dist = min(min_dist, dist)
    
    # 2. 计算边到边的距离
    edges1 = [(0, 1), (1, 2), (2, 0)]
    edges2 = [(0, 1), (1, 2), (2, 0)]
    
    for e1 in edges1:
        for e2 in edges2:
            edge1 = (tri1[e1[0]], tri1[e1[1]])
            edge2 = (tri2[e2[0]], tri2[e2[1]])
            
            dist = edge_to_edge_distance(edge1, edge2)
            min_dist = min(min_dist, dist)
    
    return min_dist


def point_to_triangle_distance(point: np.ndarray, triangle: np.ndarray, triangle_normal: np.ndarray) -> float:
    """
    计算点到三角形的最短距离
    
    参数:
        point: 点坐标
        triangle: 三角形的三个顶点坐标
        triangle_normal: 三角形的法线向量
        
    返回:
        点到三角形的最短距离
    """
    # 计算投影点（点到平面的投影）
    v0 = triangle[0]
    
    # 点到平面的有向距离
    vec_to_point = point - v0
    signed_dist = np.dot(vec_to_point, triangle_normal)
    
    # 投影点
    proj_point = point - signed_dist * triangle_normal
    
    # 检查投影点是否在三角形内
    # 使用重心坐标判断
    inside = is_point_in_triangle(proj_point, triangle)
    
    if inside:
        # 如果在三角形内，距离就是点到平面的距离
        return abs(signed_dist)
    else:
        # 否则，计算点到三角形边缘的最短距离
        edges = [(triangle[0], triangle[1]), 
                 (triangle[1], triangle[2]), 
                 (triangle[2], triangle[0])]
        
        min_edge_dist = float('inf')
        for edge in edges:
            dist = point_to_line_segment_distance(point, edge[0], edge[1])
            min_edge_dist = min(min_edge_dist, dist)
        
        return min_edge_dist


def is_point_in_triangle(point: np.ndarray, triangle: np.ndarray) -> bool:
    """
    判断点是否在三角形内（使用重心坐标）
    
    参数:
        point: 点坐标
        triangle: 三角形的三个顶点坐标
        
    返回:
        布尔值，表示点是否在三角形内
    """
    v0, v1, v2 = triangle
    
    # 计算重心坐标
    v0v1 = v1 - v0
    v0v2 = v2 - v0
    v0p = point - v0
    
    # 计算点积
    d00 = np.dot(v0v1, v0v1)
    d01 = np.dot(v0v1, v0v2)
    d11 = np.dot(v0v2, v0v2)
    d20 = np.dot(v0p, v0v1)
    d21 = np.dot(v0p, v0v2)
    
    # 计算重心坐标系数
    denom = d00 * d11 - d01 * d01
    if abs(denom) < 1e-10:
        return False
    
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w
    
    # 判断点是否在三角形内（考虑数值误差）
    eps = 1e-5  # 数值精度
    return (u >= -eps) and (v >= -eps) and (w >= -eps) and (u + v + w <= 1 + eps)


def point_to_line_segment_distance(point: np.ndarray, line_start: np.ndarray, line_end: np.ndarray) -> float:
    """
    计算点到线段的最短距离
    
    参数:
        point: 点坐标
        line_start: 线段起点坐标
        line_end: 线段终点坐标
        
    返回:
        点到线段的最短距离
    """
    line_vec = line_end - line_start
    line_len_sq = np.dot(line_vec, line_vec)
    
    # 处理零长度线段
    if line_len_sq < 1e-10:
        return np.linalg.norm(point - line_start)
    
    # 计算投影点参数 t
    t = max(0, min(1, np.dot(point - line_start, line_vec) / line_len_sq))
    
    # 计算投影点
    projection = line_start + t * line_vec
    
    # 返回点到投影点的距离
    return np.linalg.norm(point - projection)


def edge_to_edge_distance(edge1: Tuple[np.ndarray, np.ndarray], edge2: Tuple[np.ndarray, np.ndarray]) -> float:
    """
    计算两条边（线段）之间的最短距离
    
    参数:
        edge1: 第一条边的两个端点
        edge2: 第二条边的两个端点
        
    返回:
        两条边之间的最短距离
    """
    p1, p2 = edge1
    q1, q2 = edge2
    
    # 边的方向向量
    u = p2 - p1
    v = q2 - q1
    w0 = p1 - q1
    
    # 计算系数
    a = np.dot(u, u)
    b = np.dot(u, v)
    c = np.dot(v, v)
    d = np.dot(u, w0)
    e = np.dot(v, w0)
    
    # 计算分母
    denominator = a * c - b * b
    
    # 处理平行线段
    if denominator < 1e-10:
        # 计算q1到edge1的距离
        dist1 = point_to_line_segment_distance(q1, p1, p2)
        # 计算q2到edge1的距离
        dist2 = point_to_line_segment_distance(q2, p1, p2)
        # 计算p1到edge2的距离
        dist3 = point_to_line_segment_distance(p1, q1, q2)
        # 计算p2到edge2的距离
        dist4 = point_to_line_segment_distance(p2, q1, q2)
        
        return min(dist1, dist2, dist3, dist4)
    
    # 计算最近点参数
    sc = (b * e - c * d) / denominator
    tc = (a * e - b * d) / denominator
    
    # 限制在[0,1]范围内
    sc = max(0, min(1, sc))
    tc = max(0, min(1, tc))
    
    # 计算最近点
    closest_on_edge1 = p1 + sc * u
    closest_on_edge2 = q1 + tc * v
    
    # 返回两点之间的距离
    return np.linalg.norm(closest_on_edge1 - closest_on_edge2)


# 测试函数
def test():
    """测试面片邻近性检测功能"""
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    
    # 创建一些测试三角形
    vertices = np.array([
        [0, 0, 0],        # 0
        [1, 0, 0],        # 1
        [0.5, 0.866, 0],  # 2 - 等边三角形的顶点
        [0.1, 0.1, 0.05], # 3 - 用于创建邻近三角形
        [0.9, 0.1, 0.05], # 4
        [0.5, 0.766, 0.05],# 5
    ], dtype=np.float32)
    
    faces = np.array([
        [0, 1, 2],       # 三角形1
        [3, 4, 5],       # 三角形2 - 靠近三角形1
    ], dtype=np.int32)
    
    def progress(value, message):
        print(f"Progress: {value}% - {message}")
    
    # 运行分析
    proximity_faces = detect_face_proximity(faces, vertices, 0.2, progress)
    
    # 打印结果
    print("\n邻近面片:", proximity_faces)
    
    # 可视化三角形和邻近性
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # 绘制每个三角形
    for i, face in enumerate(faces):
        triangle = vertices[face]
        
        # 设置颜色
        if i in proximity_faces:
            color = 'red'
            alpha = 0.7
        else:
            color = 'blue'
            alpha = 0.3
        
        # 绘制三角形
        tri = ax.plot_trisurf(triangle[:, 0], triangle[:, 1], triangle[:, 2], 
                            color=color, alpha=alpha)
        
        # 计算三角形中心并标记序号
        center = np.mean(triangle, axis=0)
        ax.text(center[0], center[1], center[2], f"{i}", 
                fontsize=12, ha='center')
    
    # 设置坐标轴和标签
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('三角形面片邻近性分析')
    
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    test() 