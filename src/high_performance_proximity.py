"""
高性能面片邻近性检测模块

本模块提供对三角形网格的高性能面片邻近性检测，使用了以下优化:
1. NumPy向量化
2. 空间哈希网格加速空间查询
3. 多线程并行计算
4. 早期剔除策略

作者: QIMIN-CFD-PROJECT
"""

import numpy as np
import time
from multiprocessing import Pool, cpu_count, Manager
from typing import Dict, List, Tuple, Set

def vector_build_adjacency(faces: np.ndarray) -> List[Set[int]]:
    """
    构建面片邻接关系，高性能向量化实现
    
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


def compute_face_data(faces: np.ndarray, vertices: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    计算面片的特征数据，包括特征尺寸、包围盒和中心点
    
    参数:
        faces: 面片数组，形状为(n_faces, 3)
        vertices: 顶点坐标数组，形状为(n_vertices, 3)
        
    返回:
        char_lengths: 特征尺寸数组
        face_centers: 面片中心点数组
        face_min: 面片包围盒最小点数组
        face_max: 面片包围盒最大点数组
    """
    # 获取所有面片的顶点坐标，形状为(n_faces, 3, 3)
    face_vertices = vertices[faces]
    
    # 计算面积 - 使用叉积
    v1 = face_vertices[:, 1] - face_vertices[:, 0]  # 第一条边向量
    v2 = face_vertices[:, 2] - face_vertices[:, 0]  # 第二条边向量
    
    # 叉乘计算面积的两倍
    cross_products = np.cross(v1, v2)
    areas = 0.5 * np.linalg.norm(cross_products, axis=1)
    
    # 计算特征尺寸 - 使用面积的平方根
    char_lengths = np.sqrt(np.maximum(areas, 1e-10))  # 避免零面积导致的数值问题
    
    # 计算包围盒和中心点
    face_min = np.min(face_vertices, axis=1)  # 形状为(n_faces, 3)
    face_max = np.max(face_vertices, axis=1)  # 形状为(n_faces, 3)
    face_centers = np.mean(face_vertices, axis=1)  # 形状为(n_faces, 3)
    
    return char_lengths, face_centers, face_min, face_max


def create_spatial_hash_grid(face_min: np.ndarray, face_max: np.ndarray, char_lengths: np.ndarray) -> Tuple[Dict, np.ndarray, np.ndarray, float]:
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


def min_point_triangle_distance(point: np.ndarray, triangle: np.ndarray) -> float:
    """
    计算点到三角形的最短距离，高性能实现
    
    参数:
        point: 点坐标
        triangle: 三角形的三个顶点坐标
        
    返回:
        最短距离
    """
    # 计算点到三个顶点的最短距离
    d1 = np.linalg.norm(point - triangle[0])
    d2 = np.linalg.norm(point - triangle[1])
    d3 = np.linalg.norm(point - triangle[2])
    min_dist = min(d1, d2, d3)
    
    # 计算点到三条边的距离
    edges = [(0, 1), (1, 2), (2, 0)]
    for e in edges:
        p1, p2 = triangle[e[0]], triangle[e[1]]
        edge_vec = p2 - p1
        edge_len_sq = np.dot(edge_vec, edge_vec)
        
        # 防止除零
        if edge_len_sq < 1e-10:
            continue
            
        # 计算投影参数
        t = max(0, min(1, np.dot(point - p1, edge_vec) / edge_len_sq))
        proj = p1 + t * edge_vec
        dist = np.linalg.norm(point - proj)
        min_dist = min(min_dist, dist)
    
    # 计算点到三角形平面的距离
    v1 = triangle[1] - triangle[0]
    v2 = triangle[2] - triangle[0]
    normal = np.cross(v1, v2)
    normal_len = np.linalg.norm(normal)
    
    # 退化三角形处理
    if normal_len < 1e-10:
        return min_dist
    
    normal = normal / normal_len
    plane_dist = abs(np.dot(point - triangle[0], normal))
    
    # 计算投影点
    proj_point = point - plane_dist * normal
    
    # 判断投影点是否在三角形内
    area = 0.5 * normal_len
    
    # 使用重心坐标判断
    area1 = 0.5 * np.linalg.norm(np.cross(triangle[1] - proj_point, triangle[2] - proj_point))
    area2 = 0.5 * np.linalg.norm(np.cross(triangle[2] - proj_point, triangle[0] - proj_point))
    area3 = 0.5 * np.linalg.norm(np.cross(triangle[0] - proj_point, triangle[1] - proj_point))
    
    # 如果三个子三角形的面积之和近似等于原三角形的面积，则投影点在三角形内部
    if abs((area1 + area2 + area3) - area) < 1e-6 * area:
        return min(min_dist, plane_dist)
    
    return min_dist


def triangle_triangle_distance(tri1: np.ndarray, tri2: np.ndarray) -> float:
    """
    计算两个三角形之间的最短距离，高性能实现
    
    参数:
        tri1: 第一个三角形的三个顶点坐标
        tri2: 第二个三角形的三个顶点坐标
        
    返回:
        最短距离
    """
    # 首先检查三角形AABB包围盒是否相交
    min1, max1 = np.min(tri1, axis=0), np.max(tri1, axis=0)
    min2, max2 = np.min(tri2, axis=0), np.max(tri2, axis=0)
    
    # 如果包围盒不相交，可以快速返回下界距离
    if np.any(min1 > max2) or np.any(min2 > max1):
        # 计算包围盒之间的距离
        dx = max(0, max(min1[0] - max2[0], min2[0] - max1[0]))
        dy = max(0, max(min1[1] - max2[1], min2[1] - max1[1]))
        dz = max(0, max(min1[2] - max2[2], min2[2] - max1[2]))
        return np.sqrt(dx*dx + dy*dy + dz*dz)
    
    # 计算每个三角形的点到另一个三角形的最短距离
    d1 = min_point_triangle_distance(tri1[0], tri2)
    
    # 提前终止优化 - 如果第一个点已经非常接近，可能不需要检查其他点
    if d1 < 1e-10:
        return d1
    
    d2 = min_point_triangle_distance(tri1[1], tri2)
    if d2 < 1e-10:
        return d2
    
    d3 = min_point_triangle_distance(tri1[2], tri2)
    if d3 < 1e-10:
        return d3
    
    d4 = min_point_triangle_distance(tri2[0], tri1)
    if d4 < 1e-10:
        return d4
    
    d5 = min_point_triangle_distance(tri2[1], tri1)
    if d5 < 1e-10:
        return d5
    
    d6 = min_point_triangle_distance(tri2[2], tri1)
    
    return min(d1, d2, d3, d4, d5, d6)


def process_face_batch(batch_args):
    """
    处理一批面片的邻近性检测，用于多线程并行计算
    
    参数:
        batch_args: 批处理参数组
        
    返回:
        检测到的邻近面片集合
    """
    # 解包参数
    (face_indices, faces, vertices, char_lengths, face_centers, face_adjacency, 
     grid, global_min, grid_dims, grid_size, threshold) = batch_args
    
    local_result = set()
    
    for face_idx in face_indices:
        # 获取当前面片特征尺寸和顶点
        current_face = faces[face_idx]
        current_verts = vertices[current_face]
        current_length = char_lengths[face_idx]
        
        # 获取当前面片中心和特征尺寸
        center = face_centers[face_idx]
        
        # 计算搜索半径 - 基于当前面片的特征尺寸
        search_radius = threshold * current_length * 2 # 乘以2以确保捕捉所有潜在邻近面片
        
        # 计算包围盒
        tri_min = np.min(current_verts, axis=0)
        tri_max = np.max(current_verts, axis=0)
        
        # 扩展包围盒以包含可能的邻近面片
        search_min = tri_min - search_radius
        search_max = tri_max + search_radius
        
        # 计算搜索网格单元范围
        grid_min = np.floor((search_min - global_min) / grid_size).astype(int)
        grid_max = np.ceil((search_max - global_min) / grid_size).astype(int)
        
        # 限制在有效范围内
        grid_min = np.maximum(grid_min, 0)
        grid_max = np.minimum(grid_max, grid_dims - 1)
        
        # 获取邻接面片（不需要检查）
        neighbors = face_adjacency[face_idx]
        
        # 收集潜在的邻近面片
        potential_neighbors = set()
        
        # 搜索所有相关的网格单元
        for x in range(grid_min[0], grid_max[0] + 1):
            for y in range(grid_min[1], grid_max[1] + 1):
                for z in range(grid_min[2], grid_max[2] + 1):
                    cell_key = (x, y, z)
                    if cell_key in grid:
                        # 添加该单元中的所有面片
                        for j in grid[cell_key]:
                            if j != face_idx and j not in neighbors:
                                # 快速中心距离检查
                                center_dist = np.linalg.norm(center - face_centers[j])
                                if center_dist <= search_radius + char_lengths[j]:
                                    potential_neighbors.add(j)
        
        # 检查每个潜在邻近面片
        for j in potential_neighbors:
            # 获取邻近面片顶点
            neighbor_face = faces[j]
            neighbor_verts = vertices[neighbor_face]
            neighbor_length = char_lengths[j]
            
            # 计算两个面片之间的距离
            distance = triangle_triangle_distance(current_verts, neighbor_verts)
            
            # 使用两个面片中较小的特征尺寸作为参考（与STAR-CCM+一致）
            reference_length = min(current_length, neighbor_length)
            
            # 计算邻近性比率
            if reference_length > 1e-10:  # 避免除零
                proximity_ratio = distance / reference_length
                
                # 如果邻近性低于阈值，标记为有问题
                if proximity_ratio < threshold:
                    local_result.add(face_idx)
                    local_result.add(j)
    
    return local_result


def detect_face_proximity(faces: np.ndarray, vertices: np.ndarray, threshold: float = 0.1, 
                          use_multiprocessing: bool = True, progress_callback=None, 
                          num_processes: int = None) -> Set[int]:
    """
    实现STAR-CCM+式的面片邻近性检测算法
    
    STAR-CCM+的面片邻近性算法主要基于以下标准:
    1. 面片之间的距离小于给定阈值(由用户定义的相对于面片特征尺寸的百分比)
    2. 面片间距和面法线方向(考虑面法线夹角)
    3. 相邻面片的特殊处理(可选择性地排除共享边的面片)
    
    参数:
        faces: 面片索引数组
        vertices: 顶点坐标数组
        threshold: 邻近性阈值(相对于面片特征尺寸的比例)
        use_multiprocessing: 是否使用多进程计算
        progress_callback: 进度回调函数
        num_processes: 并行处理的进程数
        
    返回:
        邻近面片的索引集合
    """
    if progress_callback:
        progress_callback(0, "正在准备邻近性分析数据...")
    
    # 计算面片特征数据(特征尺寸、中心点、法线等)
    char_lengths, face_centers, face_min, face_max, face_normals = compute_face_data_with_normals(faces, vertices)
    
    # 创建空间哈希网格加速查询
    if progress_callback:
        progress_callback(5, "构建空间索引...")
    
    grid, global_min, grid_dims, grid_size = create_spatial_hash_grid(face_min, face_max, char_lengths)
    
    # 计算全局特征尺寸(用于缩放)
    median_length = np.median(char_lengths)
    proximity_threshold = threshold * median_length
    
    if progress_callback:
        progress_callback(10, f"开始检测邻近面片 (阈值: {proximity_threshold:.4f})...")
    
    # 构建邻接关系
    if progress_callback:
        progress_callback(15, "构建面片邻接关系...")
    
    adjacency = vector_build_adjacency(faces)
    
    # 待检查的面片对
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
    
    if use_multiprocessing and len(potential_pairs) > 100:
        # 多进程分析潜在的邻近面片对
        if num_processes is None:
            num_processes = max(1, cpu_count() - 1)  # 默认使用CPU核心数-1
        
        # 准备多进程共享数据
        manager = Manager()
        shared_results = manager.list()
        
        # 将任务划分为多个批次
        batch_size = max(1, len(potential_pairs) // (num_processes * 4))
        batches = [potential_pairs[i:i+batch_size] for i in range(0, len(potential_pairs), batch_size)]
        
        if progress_callback:
            progress_callback(45, f"使用 {num_processes} 个进程并行分析 {len(batches)} 个批次...")
        
        # 准备进程池
        with Pool(processes=num_processes) as pool:
            # 提交所有批次任务
            results = []
            for batch_idx, batch in enumerate(batches):
                batch_args = (
                    batch,
                    face_centers,
                    face_normals,
                    char_lengths,
                    proximity_threshold,
                    vertices,
                    faces,
                    shared_results,
                    batch_idx,
                    len(batches)
                )
                results.append(pool.apply_async(process_face_proximity_batch, args=batch_args))
            
            # 等待所有结果并更新进度
            completed_batches = 0
            total_batches = len(batches)
            
            while completed_batches < total_batches:
                completed_batches = sum(1 for r in results if r.ready())
                if progress_callback:
                    progress_value = 45 + int(completed_batches / total_batches * 45)
                    progress_callback(progress_value, f"完成 {completed_batches}/{total_batches} 批次分析...")
                time.sleep(0.1)  # 避免占用过多CPU
            
            # 等待所有进程完成
            pool.close()
            pool.join()
        
        # 收集结果
        for result in shared_results:
            proximity_faces.update(result)
            
    else:
        # 单进程处理
        for idx, (face_i, face_j) in enumerate(potential_pairs):
            if progress_callback and idx % 1000 == 0:
                progress_value = 40 + int(idx / len(potential_pairs) * 50)
                progress_callback(progress_value, f"分析面片对 {idx}/{len(potential_pairs)}...")
            
            # 检查面片间距离
            if is_face_proximity_star_ccm(
                face_i, face_j, 
                face_centers, face_normals, char_lengths, 
                proximity_threshold, vertices, faces
            ):
                proximity_faces.add(face_i)
                proximity_faces.add(face_j)
    
    if progress_callback:
        progress_callback(95, f"分析完成. 发现 {len(proximity_faces)} 个邻近面片.")
    
    if progress_callback:
        progress_callback(100, "邻近性分析完成.")
    
    return proximity_faces


def compute_face_data_with_normals(faces: np.ndarray, vertices: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    计算面片的特征数据，包括特征尺寸、包围盒和中心点，以及面法线
    
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
    
    # 单位化法线向量
    norms = np.linalg.norm(cross_products, axis=1, keepdims=True)
    # 防止除零
    norms[norms < 1e-10] = 1.0
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


def process_face_proximity_batch(batch, face_centers, face_normals, char_lengths, 
                             proximity_threshold, vertices, faces, shared_results, 
                             batch_idx, total_batches):
    """
    并行处理一批面片对，检测它们是否符合STAR-CCM+的邻近性标准
    """
    proximity_faces = set()
    
    for face_i, face_j in batch:
        # 检查面片间距离和法线夹角
        if is_face_proximity_star_ccm(
            face_i, face_j, 
            face_centers, face_normals, char_lengths, 
            proximity_threshold, vertices, faces
        ):
            proximity_faces.add(face_i)
            proximity_faces.add(face_j)
    
    # 将结果添加到共享列表
    shared_results.append(proximity_faces)
    
    return len(proximity_faces)


def is_face_proximity_star_ccm(face_i, face_j, face_centers, face_normals, 
                          char_lengths, proximity_threshold, vertices, faces):
    """
    使用STAR-CCM+风格的标准检查两个面片是否邻近
    
    STAR-CCM+邻近性标准:
    1. 面片之间的最短距离小于给定阈值
    2. 面片法线方向相对关系（角度）也会影响判断
    3. 特征尺寸对阈值有影响
    
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
    # STAR-CCM+使用点到面片和边到边的最短距离
    min_distance = compute_triangle_triangle_distance(tri1_verts, tri2_verts, normal_i, normal_j)
    
    # 根据调整后的阈值判断是否邻近
    return min_distance < adjusted_threshold


def compute_triangle_triangle_distance(tri1, tri2, normal1, normal2):
    """
    计算两个三角形之间的最短距离，以STAR-CCM+的方式实现
    
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


def point_to_triangle_distance(point, triangle, triangle_normal):
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


def is_point_in_triangle(point, triangle):
    """
    判断点是否在三角形内（使用重心坐标）
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
    
    # 判断点是否在三角形内
    eps = 1e-5  # 数值精度
    return (u >= -eps) and (v >= -eps) and (w >= -eps) and (u + v + w <= 1 + eps)


def point_to_line_segment_distance(point, line_start, line_end):
    """
    计算点到线段的最短距离
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


def edge_to_edge_distance(edge1, edge2):
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