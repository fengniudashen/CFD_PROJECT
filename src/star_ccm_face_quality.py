#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
STAR-CCM+面片质量分析模块

本模块实现了与STAR-CCM+完全一致的面片质量计算算法：

face quality = 2 * (r/R)

其中：
- r 是三角形的内接圆半径
- R 是三角形的外接圆半径

对于理想的等边三角形，r/R = 1/2，因此质量分数为1.0
对于退化的三角形，r/R接近0，因此质量分数接近0.0
"""

import numpy as np
import time
from typing import Dict, List, Tuple, Callable, Optional, Union


def compute_face_quality(vertices: np.ndarray, faces: np.ndarray, 
                        threshold: float = 0.5, 
                        progress_callback: Optional[Callable] = None) -> Dict:
    """
    计算面片质量，使用STAR-CCM+的算法: face quality = 2 * (r/R)
    
    参数:
        vertices (np.ndarray): 顶点坐标数组，形状为(n_vertices, 3)
        faces (np.ndarray): 面片索引数组，形状为(n_faces, 3)
        threshold (float): 质量阈值，低于此值的面片将被标记为低质量
        progress_callback (callable, 可选): 进度回调函数，接收参数(percentage, message)
        
    返回:
        dict: 包含以下键的结果字典:
            - 'quality': 每个面片的质量分数 (0-1)
            - 'low_quality_faces': 低于阈值的面片索引列表
            - 'stats': 统计信息
    """
    start_time = time.time()
    
    # 创建面片质量数组
    n_faces = len(faces)
    face_quality = np.zeros(n_faces)
    
    # 初始化统计数据
    stats = {
        'total_faces': n_faces,
        'low_quality': 0,
        'min_quality': 1.0,
        'max_quality': 0.0,
        'avg_quality': 0.0,
        'threshold': threshold
    }
    
    # 报告初始进度
    if progress_callback:
        progress_callback(0, f"准备分析 {n_faces} 个面片...")
    
    # 遍历计算每个面片的质量
    update_interval = max(1, n_faces // 100)  # 更新进度的间隔
    
    for i, face in enumerate(faces):
        # 更新进度
        if progress_callback and i % update_interval == 0:
            progress_percent = int(i / n_faces * 100)
            progress_callback(progress_percent, f"分析面片 {i}/{n_faces}...")
        
        # 获取面片的三个顶点
        v1 = vertices[face[0]]
        v2 = vertices[face[1]]
        v3 = vertices[face[2]]
        
        # 计算三角形的三条边长
        a = np.linalg.norm(v2 - v3)
        b = np.linalg.norm(v3 - v1)
        c = np.linalg.norm(v1 - v2)
        
        # 处理退化三角形
        if a < 1e-10 or b < 1e-10 or c < 1e-10 or a + b <= c or b + c <= a or c + a <= b:
            face_quality[i] = 0.0
            continue
        
        # 使用海伦公式计算面积
        s = (a + b + c) / 2.0
        area = np.sqrt(max(0, s * (s - a) * (s - b) * (s - c)))
        
        # 处理面积过小的情况
        if area < 1e-10:
            face_quality[i] = 0.0
            continue
            
        # 计算内接圆半径 r = 面积 / 半周长
        r = area / s
        
        # 计算外接圆半径 R = (a * b * c) / (4 * 面积)
        R = (a * b * c) / (4.0 * area)
        
        # STAR-CCM+面片质量公式: face quality = 2 * (r/R)
        # 对于等边三角形，r/R = 1/2，因此质量分数为1.0
        quality = 2.0 * (r / R)
        
        # 确保质量在[0,1]之间
        quality = max(0.0, min(1.0, quality))
        face_quality[i] = quality
    
    # 更新最终进度
    if progress_callback:
        progress_callback(99, "生成结果报告...")
    
    # 计算统计信息
    stats['min_quality'] = np.min(face_quality)
    stats['max_quality'] = np.max(face_quality)
    stats['avg_quality'] = np.mean(face_quality)
    stats['low_quality'] = np.sum(face_quality < threshold)
    
    # 找出质量低于阈值的面片
    low_quality_faces = np.where(face_quality < threshold)[0].tolist()
    
    # 计算总时间
    elapsed_time = time.time() - start_time
    stats['elapsed_time'] = elapsed_time
    
    # 最终进度
    if progress_callback:
        progress_callback(100, f"分析完成，用时 {elapsed_time:.2f} 秒")
    
    # 返回结果
    return {
        'quality': face_quality,
        'low_quality_faces': low_quality_faces,
        'stats': stats
    }


def analyze_face_quality(vertices: np.ndarray, faces: np.ndarray, 
                       threshold: float = 0.5, 
                       progress_callback: Optional[Callable] = None) -> Dict:
    """
    分析三角形网格的面片质量，使用STAR-CCM+的算法
    
    参数:
        vertices (np.ndarray): 顶点坐标数组
        faces (np.ndarray): 面片索引数组
        threshold (float): 质量阈值，低于此值的面片将被标记为低质量
        progress_callback (callable): 进度回调函数
        
    返回:
        dict: 分析结果字典
    """
    return compute_face_quality(vertices, faces, threshold, progress_callback)


def generate_quality_report(stats: Dict) -> str:
    """
    生成面片质量分析报告
    
    参数:
        stats (dict): 统计信息字典
        
    返回:
        str: 格式化的质量报告文本
    """
    total_faces = stats['total_faces']
    low_quality = stats['low_quality']
    threshold = stats['threshold']
    
    report = f'STAR-CCM+面片质量分析结果:\n'
    report += f'低质量面片: {low_quality} ({low_quality/total_faces*100:.1f}%)\n'
    report += f'\n质量统计:\n'
    report += f'最小质量: {stats["min_quality"]:.4f}\n'
    report += f'最大质量: {stats["max_quality"]:.4f}\n'
    report += f'平均质量: {stats["avg_quality"]:.4f}\n'
    
    if 'elapsed_time' in stats:
        report += f'\n分析用时: {stats["elapsed_time"]:.2f} 秒\n'
    
    report += f'\n已选中 {low_quality} 个质量低于 {threshold} 的面片'
    
    return report


def validate_algorithm() -> None:
    """
    验证算法正确性，通过计算几个已知三角形的质量
    """
    print("验证STAR-CCM+面片质量算法:")
    
    # 创建测试三角形
    vertices = np.array([
        # 等边三角形
        [0, 0, 0],
        [1, 0, 0],
        [0.5, np.sqrt(3)/2, 0],
        
        # 直角等腰三角形
        [0, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
        
        # 极度不平衡的三角形
        [0, 0, 0],
        [1, 0, 0],
        [0.1, 0.01, 0]
    ])
    
    faces = np.array([
        [0, 1, 2],  # 等边三角形
        [3, 4, 5],  # 直角等腰三角形
        [6, 7, 8]   # 不平衡三角形
    ])
    
    # 计算质量
    result = compute_face_quality(vertices, faces)
    quality = result['quality']
    
    # 理论质量值
    # 等边三角形：1.0
    # 直角等腰三角形：约0.828
    # 不平衡三角形：接近0
    
    print(f"等边三角形质量: {quality[0]:.6f} (理论值: 1.0)")
    print(f"直角等腰三角形质量: {quality[1]:.6f} (理论值: 0.828)")
    print(f"不平衡三角形质量: {quality[2]:.6f} (理论值: 接近0)")


if __name__ == "__main__":
    validate_algorithm()
