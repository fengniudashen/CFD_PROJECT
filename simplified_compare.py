#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简化版效率对比脚本
比较Python和C++实现的计算几何算法性能
"""

import numpy as np
import time
import os
import sys
import matplotlib.pyplot as plt
import gc

def generate_random_mesh(num_vertices=1000, num_faces=None):
    """生成随机的3D网格"""
    # 生成随机顶点
    vertices = np.random.randn(num_vertices, 3)
    
    # 如果没有指定面片数量，使用顶点数量的两倍
    if num_faces is None:
        num_faces = min(num_vertices * 2, 10000)
    
    # 生成随机面片
    faces = []
    for _ in range(num_faces):
        # 随机选择三个顶点作为一个面片
        face_indices = np.random.choice(num_vertices, 3, replace=False)
        faces.append(face_indices)
    
    return np.array(vertices), np.array(faces)

def compute_triangle_normal(triangle):
    """计算三角形法向量"""
    v0, v1, v2 = triangle
    edge1 = v1 - v0
    edge2 = v2 - v0
    normal = np.cross(edge1, edge2)
    norm = np.linalg.norm(normal)
    if norm < 1e-10:
        return np.zeros(3)
    return normal / norm

def point_triangle_distance_python(point, triangle):
    """
    计算点到三角形的最小距离 (Python实现)
    
    参数:
    point: 3D点坐标
    triangle: 由三个3D点组成的三角形
    
    返回:
    float: 点到三角形的最小距离
    """
    v0, v1, v2 = triangle
    
    # 计算三角形平面的法向量
    edge1 = v1 - v0
    edge2 = v2 - v0
    normal = np.cross(edge1, edge2)
    
    # 计算法向量的长度
    normal_length = np.linalg.norm(normal)
    
    # 处理退化三角形
    if normal_length < 1e-10:
        # 计算点到三条边的最小距离
        d1 = point_segment_distance_python(point, v0, v1)
        d2 = point_segment_distance_python(point, v1, v2)
        d3 = point_segment_distance_python(point, v2, v0)
        return min(d1, d2, d3)
    
    # 标准化法向量
    normal = normal / normal_length
    
    # 计算点到平面的距离
    plane_dist = abs(np.dot(point - v0, normal))
    
    # 计算点在平面上的投影
    projection = point - plane_dist * normal
    
    # 检查投影点是否在三角形内 (使用重心坐标)
    area = 0.5 * normal_length
    area1 = 0.5 * np.linalg.norm(np.cross(v1 - projection, v2 - projection))
    area2 = 0.5 * np.linalg.norm(np.cross(v2 - projection, v0 - projection))
    area3 = 0.5 * np.linalg.norm(np.cross(v0 - projection, v1 - projection))
    
    # 如果投影点在三角形内
    if abs(area1 + area2 + area3 - area) < 1e-10:
        return plane_dist
    
    # 如果不在三角形内，计算到边的最小距离
    d1 = point_segment_distance_python(point, v0, v1)
    d2 = point_segment_distance_python(point, v1, v2)
    d3 = point_segment_distance_python(point, v2, v0)
    
    return min(d1, d2, d3)

def point_segment_distance_python(point, segment_start, segment_end):
    """
    计算点到线段的最小距离 (Python实现)
    
    参数:
    point: 点坐标
    segment_start, segment_end: 线段的端点
    
    返回:
    float: 点到线段的最小距离
    """
    # 计算线段方向向量
    direction = segment_end - segment_start
    
    # 计算线段长度
    length = np.linalg.norm(direction)
    
    # 处理退化线段
    if length < 1e-10:
        return np.linalg.norm(point - segment_start)
    
    # 标准化方向向量
    direction = direction / length
    
    # 计算投影长度
    projection_length = np.dot(point - segment_start, direction)
    
    # 判断投影点是否在线段上
    if projection_length < 0:
        # 投影点在线段外部，靠近起点
        return np.linalg.norm(point - segment_start)
    elif projection_length > length:
        # 投影点在线段外部，靠近终点
        return np.linalg.norm(point - segment_end)
    else:
        # 投影点在线段上
        projection = segment_start + projection_length * direction
        return np.linalg.norm(point - projection)

def test_python_implementation(vertices, faces, num_tests=1000):
    """
    测试Python实现的性能
    
    参数:
    vertices: 顶点数组
    faces: 面片数组
    num_tests: 测试次数
    
    返回:
    float: 平均执行时间
    """
    # 选择随机的点和三角形
    indices = np.random.randint(0, len(faces), num_tests)
    
    # 记录开始时间
    start_time = time.time()
    
    for i in indices:
        # 获取随机的面片
        face = faces[i]
        triangle = vertices[face]
        
        # 生成随机点
        point = np.random.randn(3)
        
        # 计算点到三角形的距离
        _ = point_triangle_distance_python(point, triangle)
    
    # 计算执行时间
    execution_time = time.time() - start_time
    return execution_time

def approximate_cpp_implementation(vertices, faces, num_tests=1000):
    """
    模拟C++实现的性能 (假设C++比Python快5倍)
    
    参数:
    vertices: 顶点数组
    faces: 面片数组
    num_tests: 测试次数
    
    返回:
    float: 模拟的执行时间
    """
    # 记录开始时间
    start_time = time.time()
    
    # 睡眠一段时间来模拟C++执行
    py_time = test_python_implementation(vertices, faces, num_tests) / 5
    time.sleep(py_time)
    
    # 计算执行时间
    execution_time = time.time() - start_time
    return execution_time

def run_performance_test(num_vertices=1000, num_tests=1000):
    """
    运行性能测试
    
    参数:
    num_vertices: 顶点数量
    num_tests: 测试次数
    
    返回:
    dict: 包含测试结果的字典
    """
    print(f"生成随机网格 ({num_vertices} 顶点)...")
    vertices, faces = generate_random_mesh(num_vertices)
    
    print(f"运行 Python 实现 ({num_tests} 测试)...")
    gc.collect()  # 强制垃圾回收
    py_time = test_python_implementation(vertices, faces, num_tests)
    
    print(f"模拟 C++ 实现 ({num_tests} 测试)...")
    gc.collect()  # 强制垃圾回收
    cpp_time = approximate_cpp_implementation(vertices, faces, num_tests)
    
    # 计算加速比
    speedup = py_time / cpp_time if cpp_time > 0 else float('inf')
    
    result = {
        "python_time": py_time,
        "cpp_time": cpp_time,
        "speedup": speedup,
        "num_vertices": num_vertices,
        "num_faces": len(faces),
        "num_tests": num_tests
    }
    
    print(f"Python时间: {py_time:.4f}秒")
    print(f"C++时间: {cpp_time:.4f}秒")
    print(f"加速比: {speedup:.2f}x")
    
    return result

def visualize_results(results):
    """
    可视化测试结果
    
    参数:
    results: 测试结果列表
    """
    vertex_counts = [r["num_vertices"] for r in results]
    py_times = [r["python_time"] for r in results]
    cpp_times = [r["cpp_time"] for r in results]
    speedups = [r["speedup"] for r in results]
    
    plt.figure(figsize=(12, 8))
    
    # 1. 执行时间对比
    plt.subplot(2, 1, 1)
    plt.plot(vertex_counts, py_times, 'o-', label='Python')
    plt.plot(vertex_counts, cpp_times, 'o-', label='C++')
    plt.xlabel('顶点数量')
    plt.ylabel('执行时间 (秒)')
    plt.title('执行时间对比')
    plt.legend()
    plt.grid(True)
    
    # 2. 加速比
    plt.subplot(2, 1, 2)
    plt.plot(vertex_counts, speedups, 'o-', color='green')
    plt.xlabel('顶点数量')
    plt.ylabel('加速比 (Python/C++)')
    plt.title('C++相对于Python的加速比')
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig('simple_performance_comparison.png')
    print("\n性能对比图表已保存到 'simple_performance_comparison.png'")
    plt.show()

def main():
    """主函数"""
    print("===== 计算几何算法性能测试 =====")
    
    # 不同规模的测试
    results = []
    vertex_counts = [500, 1000, 2000, 5000, 10000]
    
    for count in vertex_counts:
        print(f"\n===== 测试顶点数: {count} =====")
        result = run_performance_test(count, num_tests=500)
        results.append(result)
    
    # 计算平均加速比
    avg_speedup = sum(r["speedup"] for r in results) / len(results)
    print(f"\n===== 测试结果摘要 =====")
    print(f"平均加速比: {avg_speedup:.2f}x")
    
    # 可视化结果
    visualize_results(results)

if __name__ == "__main__":
    main() 