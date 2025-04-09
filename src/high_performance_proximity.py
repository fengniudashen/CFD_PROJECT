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
    执行面片邻近性检测
    
    参数:
        faces: 网格面片数组
        vertices: 顶点坐标数组
        threshold: 邻近性阈值，默认为0.1
        use_multiprocessing: 是否使用多进程加速
        progress_callback: 进度回调函数
        num_processes: 使用的进程数量
        
    返回:
        检测到的邻近面片集合
    """
    start_time = time.time()
    
    # 报告进度
    if progress_callback:
        progress_callback(5, "构建邻接关系...")
    
    # 1. 构建面片邻接关系
    face_adjacency = vector_build_adjacency(faces)
    
    if progress_callback:
        progress_callback(15, "计算面片数据...")
    
    # 2. 计算面片数据
    char_lengths, face_centers, face_min, face_max = compute_face_data(faces, vertices)
    
    if progress_callback:
        progress_callback(25, "创建空间哈希网格...")
    
    # 3. 创建空间哈希网格
    grid, global_min, grid_dims, grid_size = create_spatial_hash_grid(face_min, face_max, char_lengths)
    
    if progress_callback:
        progress_callback(40, "检测面片邻近性...")
    
    # 4. 检测面片邻近性
    proximity_faces = set()
    
    # 确定使用的CPU数量
    if num_processes is None:
        num_processes = cpu_count() if use_multiprocessing else 1
    num_processes = min(num_processes, 8)  # 限制最大进程数
    
    # 如果面片数量太少，不使用多进程
    if len(faces) < 100 or not use_multiprocessing:
        num_processes = 1
    
    # 准备批处理参数
    face_indices = list(range(len(faces)))
    batch_size = max(100, len(faces) // (num_processes * 4))  # 每个批次至少100个面片
    batches = []
    
    # 分割面片为多个批次
    for i in range(0, len(faces), batch_size):
        batch = face_indices[i:min(i + batch_size, len(faces))]
        batches.append(batch)
    
    # 准备批处理函数参数
    common_args = (
        faces, vertices, char_lengths, face_centers, face_adjacency,
        grid, global_min, grid_dims, grid_size, threshold
    )
    
    # 多进程处理
    if num_processes > 1:
        batch_args = [(batch,) + common_args for batch in batches]
        
        try:
            with Pool(processes=num_processes) as pool:
                # 创建异步任务
                results = []
                
                # 提交所有批次
                for i, args in enumerate(batch_args):
                    result = pool.apply_async(process_face_batch, (args,))
                    results.append(result)
                
                # 等待结果并更新进度
                for i, result in enumerate(results):
                    local_result = result.get()
                    proximity_faces.update(local_result)
                    
                    # 更新进度
                    if progress_callback:
                        progress = 40 + 55 * (i + 1) / len(results)
                        progress_callback(int(progress), f"处理批次 {i+1}/{len(results)}...")
        
        except Exception as e:
            print(f"多线程处理失败: {e}, 回退到单线程...")
            proximity_faces = set()
            num_processes = 1
    
    # 单线程处理
    if num_processes == 1:
        for i, batch in enumerate(batches):
            batch_args = (batch,) + common_args
            local_result = process_face_batch(batch_args)
            proximity_faces.update(local_result)
            
            # 更新进度
            if progress_callback:
                progress = 40 + 55 * (i + 1) / len(batches)
                progress_callback(int(progress), f"处理批次 {i+1}/{len(batches)}...")
    
    if progress_callback:
        progress_callback(95, "完成检测")
    
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"面片邻近性检测完成，耗时: {execution_time:.2f}秒，检测到 {len(proximity_faces)} 个邻近面片，占总面片数的 {len(proximity_faces)/len(faces)*100:.2f}%")
    
    return proximity_faces 