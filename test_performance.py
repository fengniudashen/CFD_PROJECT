#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
比较Python和C++实现的自相交检测算法性能
"""

import numpy as np
import time
import os
import sys
import trimesh
import matplotlib.pyplot as plt
from src.algorithms.self_intersection_algorithm import SelfIntersectionAlgorithm

def load_mesh(file_path):
    """加载3D模型"""
    print(f"加载模型: {file_path}")
    try:
        mesh = trimesh.load(file_path)
        return mesh
    except Exception as e:
        print(f"加载模型失败: {e}")
        return None

def run_performance_test(mesh, judgment_distance=0.1):
    """
    运行性能测试，比较Python和C++实现
    
    参数:
    mesh: 三角网格模型
    judgment_distance: 相邻面判断距离
    
    返回:
    dict: 包含性能测试结果和比较的字典
    """
    # 创建算法实例
    algo = SelfIntersectionAlgorithm()
    
    # 设置参数
    algo.set_mesh(mesh.vertices, mesh.faces)
    
    # 测试Python实现
    print("运行Python实现...")
    py_start_time = time.time()
    py_result = algo.find_adjacent_faces(judgment_distance=judgment_distance, 
                                         is_cpp=False, auto_set=False)
    py_time = time.time() - py_start_time
    
    # 测试C++实现
    print("运行C++实现...")
    cpp_start_time = time.time()
    cpp_result = algo.find_adjacent_faces(judgment_distance=judgment_distance, 
                                          is_cpp=True, auto_set=False)
    cpp_time = time.time() - cpp_start_time
    
    # 计算加速比
    speedup = py_time / cpp_time if cpp_time > 0 else float('inf')
    
    # 检查结果是否一致
    is_same = set(py_result) == set(cpp_result)
    
    # 收集结果
    result = {
        "python_time": py_time,
        "cpp_time": cpp_time,
        "speedup": speedup,
        "python_faces": len(py_result),
        "cpp_faces": len(cpp_result),
        "results_match": is_same,
        "judgment_distance": judgment_distance,
        "vertices_count": len(mesh.vertices),
        "faces_count": len(mesh.faces)
    }
    
    return result

def visualize_results(results):
    """可视化性能测试结果"""
    # 创建图表
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 执行时间对比
    bar_width = 0.35
    x = np.arange(len(results))
    labels = [f"测试 {i+1}" for i in range(len(results))]
    
    py_times = [r["python_time"] for r in results]
    cpp_times = [r["cpp_time"] for r in results]
    
    ax1.bar(x - bar_width/2, py_times, bar_width, label='Python实现')
    ax1.bar(x + bar_width/2, cpp_times, bar_width, label='C++实现')
    ax1.set_xlabel('测试')
    ax1.set_ylabel('执行时间（秒）')
    ax1.set_title('执行时间对比')
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.legend()
    
    # 加速比
    speedups = [r["speedup"] for r in results]
    ax2.plot(x, speedups, 'o-', linewidth=2)
    ax2.set_xlabel('测试')
    ax2.set_ylabel('加速比 (Python/C++)')
    ax2.set_title('C++实现相对于Python的加速比')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig('performance_comparison.png')
    plt.show()

def print_results(results):
    """打印性能测试结果"""
    print("\n性能测试结果:")
    print("-" * 80)
    print(f"{'测试':<10}{'Python时间(秒)':<15}{'C++时间(秒)':<15}{'加速比':<10}{'结果一致':<10}")
    print("-" * 80)
    
    for i, r in enumerate(results):
        print(f"{i+1:<10}{r['python_time']:<15.4f}{r['cpp_time']:<15.4f}{r['speedup']:<10.2f}{r['results_match']:<10}")
    
    print("-" * 80)
    avg_speedup = sum(r["speedup"] for r in results) / len(results)
    print(f"平均加速比: {avg_speedup:.2f}x")
    print(f"最大加速比: {max(r['speedup'] for r in results):.2f}x")
    print("-" * 80)

def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python test_performance.py <model_file1> [model_file2 ...]")
        print("例如: python test_performance.py models/bunny.obj models/dragon.obj")
        return

    # 准备测试模型列表
    model_files = sys.argv[1:]
    results = []
    
    # 运行测试
    for model_file in model_files:
        if not os.path.exists(model_file):
            print(f"错误: 找不到模型文件 '{model_file}'")
            continue
            
        mesh = load_mesh(model_file)
        if mesh is None:
            continue
        
        print(f"\n测试模型: {os.path.basename(model_file)}")
        print(f"顶点数: {len(mesh.vertices)}, 面片数: {len(mesh.faces)}")
        
        # 对不同判断距离进行测试
        for distance in [0.01, 0.05, 0.1]:
            print(f"\n使用判断距离: {distance}")
            result = run_performance_test(mesh, judgment_distance=distance)
            result["model"] = os.path.basename(model_file)
            results.append(result)
    
    # 输出结果
    if results:
        print_results(results)
        visualize_results(results)
    else:
        print("没有成功完成任何测试")

if __name__ == "__main__":
    main() 