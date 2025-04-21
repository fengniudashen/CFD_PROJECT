#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
高级效率对比脚本
比较Python和C++实现的自相交检测算法在性能、内存使用和CPU利用率方面的差异
"""

import numpy as np
import time
import os
import sys
import psutil
import trimesh
import matplotlib.pyplot as plt
from multiprocessing import cpu_count
import gc
from pathlib import Path
import threading

# 导入自相交检测算法
from src.algorithms.self_intersection_algorithm import SelfIntersectionAlgorithm

# 尝试导入C++模块
try:
    import self_intersection_cpp
    HAS_CPP_MODULE = True
except ImportError:
    HAS_CPP_MODULE = False
    print("警告: C++模块未找到，将只测试Python实现")

class ResourceMonitor(threading.Thread):
    """资源监控线程类"""
    
    def __init__(self, pid):
        """初始化资源监控器"""
        threading.Thread.__init__(self)
        self.pid = pid
        self.process = psutil.Process(pid)
        self.running = True
        self.memory_usage = []
        self.cpu_usage = []
        self.interval = 0.1  # 采样间隔(秒)
        
    def run(self):
        """线程运行函数"""
        while self.running:
            # 获取内存使用率
            memory_info = self.process.memory_info()
            self.memory_usage.append(memory_info.rss / 1024 / 1024)  # 转换为MB
            
            # 获取CPU使用率
            self.cpu_usage.append(self.process.cpu_percent())
            
            # 暂停一段时间
            time.sleep(self.interval)
            
    def stop(self):
        """停止监控线程"""
        self.running = False
        self.join()
        
    def get_average_memory(self):
        """获取平均内存使用率(MB)"""
        if not self.memory_usage:
            return 0
        return sum(self.memory_usage) / len(self.memory_usage)
        
    def get_peak_memory(self):
        """获取峰值内存使用率(MB)"""
        if not self.memory_usage:
            return 0
        return max(self.memory_usage)
        
    def get_average_cpu(self):
        """获取平均CPU使用率(%)"""
        if not self.cpu_usage:
            return 0
        return sum(self.cpu_usage) / len(self.cpu_usage)

def generate_test_mesh(num_vertices=1000, complexity=1.0):
    """生成测试用的随机网格"""
    # 生成随机顶点
    vertices = np.random.randn(num_vertices, 3) * complexity
    
    # 生成面片 (简化的三角剖分)
    faces = []
    max_faces = min(num_vertices * 2, 10000)
    
    for i in range(0, min(num_vertices - 2, max_faces)):
        # 随机选择三个顶点形成一个面片
        indices = np.random.choice(num_vertices, 3, replace=False)
        faces.append(indices)
    
    return np.array(vertices), np.array(faces)

def run_python_implementation(vertices, faces, threshold=0.1):
    """
    运行Python实现并监控资源使用情况
    
    返回:
    dict: 包含执行结果和资源使用信息
    """
    # 启动资源监控
    pid = os.getpid()
    monitor = ResourceMonitor(pid)
    monitor.start()
    
    # 创建算法实例
    algo = SelfIntersectionAlgorithm()
    algo.set_mesh(vertices, faces)
    
    # 强制使用Python实现
    algo.use_cpp = False
    
    # 执行算法
    gc.collect()  # 强制垃圾回收，确保测量的是算法本身的内存使用
    start_time = time.time()
    
    adjacent_faces = algo.find_adjacent_faces(
        judgment_distance=threshold,
        is_cpp=False,
        auto_set=False
    )
    
    execution_time = time.time() - start_time
    
    # 停止监控
    monitor.stop()
    
    return {
        "execution_time": execution_time,
        "result_size": len(adjacent_faces),
        "avg_memory": monitor.get_average_memory(),
        "peak_memory": monitor.get_peak_memory(),
        "avg_cpu": monitor.get_average_cpu()
    }

def run_cpp_implementation(vertices, faces, threshold=0.1):
    """
    运行C++实现并监控资源使用情况
    
    返回:
    dict: 包含执行结果和资源使用信息
    """
    if not HAS_CPP_MODULE:
        return {
            "execution_time": 0,
            "result_size": 0,
            "avg_memory": 0,
            "peak_memory": 0,
            "avg_cpu": 0
        }
    
    # 启动资源监控
    pid = os.getpid()
    monitor = ResourceMonitor(pid)
    monitor.start()
    
    # 执行算法
    gc.collect()  # 强制垃圾回收
    
    try:
        # 直接调用C++实现
        start_time = time.time()
        
        adjacent_faces, cpp_time = self_intersection_cpp.detect_self_intersections_with_timing(
            vertices, faces, float(threshold)
        )
        
        execution_time = time.time() - start_time
        
        # 停止监控
        monitor.stop()
        
        return {
            "execution_time": execution_time,
            "cpp_reported_time": cpp_time,  # C++内部计时
            "result_size": len(adjacent_faces),
            "avg_memory": monitor.get_average_memory(),
            "peak_memory": monitor.get_peak_memory(),
            "avg_cpu": monitor.get_average_cpu()
        }
    
    except Exception as e:
        print(f"C++实现执行出错: {str(e)}")
        monitor.stop()
        
        return {
            "execution_time": 0,
            "result_size": 0,
            "avg_memory": 0,
            "peak_memory": 0,
            "avg_cpu": 0,
            "error": str(e)
        }

def load_mesh_file(file_path):
    """从文件加载网格数据"""
    try:
        print(f"加载模型: {file_path}")
        mesh = trimesh.load(file_path)
        vertices = np.array(mesh.vertices)
        faces = np.array(mesh.faces)
        print(f"成功加载 {len(vertices)} 个顶点, {len(faces)} 个面片")
        return vertices, faces
    except Exception as e:
        print(f"加载模型文件失败: {str(e)}")
        return None, None

def compare_implementations(vertices, faces, thresholds=None):
    """
    对比Python和C++实现的效率
    
    参数:
    vertices: 顶点数组
    faces: 面片数组
    thresholds: 阈值列表
    
    返回:
    dict: 对比结果
    """
    if thresholds is None:
        thresholds = [0.01, 0.05, 0.1]
    
    results = []
    
    for threshold in thresholds:
        print(f"\n使用阈值: {threshold}")
        
        # 运行Python实现
        print("运行Python实现...")
        py_result = run_python_implementation(vertices, faces, threshold)
        
        # 运行C++实现
        print("运行C++实现...")
        cpp_result = run_cpp_implementation(vertices, faces, threshold)
        
        # 计算加速比
        if cpp_result["execution_time"] > 0:
            speedup = py_result["execution_time"] / cpp_result["execution_time"]
        else:
            speedup = 0
            
        # 计算内存使用比
        if cpp_result["avg_memory"] > 0:
            memory_ratio = py_result["avg_memory"] / cpp_result["avg_memory"]
        else:
            memory_ratio = 0
        
        # 收集测试结果
        test_result = {
            "threshold": threshold,
            "vertices_count": len(vertices),
            "faces_count": len(faces),
            "python": py_result,
            "cpp": cpp_result,
            "speedup": speedup,
            "memory_ratio": memory_ratio
        }
        
        # 打印结果概要
        print(f"Python时间: {py_result['execution_time']:.4f}秒, 内存: {py_result['peak_memory']:.2f}MB, CPU: {py_result['avg_cpu']:.2f}%")
        print(f"C++时间: {cpp_result['execution_time']:.4f}秒, 内存: {cpp_result['peak_memory']:.2f}MB, CPU: {cpp_result['avg_cpu']:.2f}%")
        print(f"加速比: {speedup:.2f}x, 内存使用比: {memory_ratio:.2f}x")
        
        results.append(test_result)
    
    return results

def visualize_comparison(results):
    """可视化对比结果"""
    # 提取数据
    thresholds = [r["threshold"] for r in results]
    py_times = [r["python"]["execution_time"] for r in results]
    cpp_times = [r["cpp"]["execution_time"] for r in results]
    py_memory = [r["python"]["peak_memory"] for r in results]
    cpp_memory = [r["cpp"]["peak_memory"] for r in results]
    py_cpu = [r["python"]["avg_cpu"] for r in results]
    cpp_cpu = [r["cpp"]["avg_cpu"] for r in results]
    speedups = [r["speedup"] for r in results]
    
    # 创建图表
    fig, axs = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. 执行时间对比
    axs[0, 0].bar(np.arange(len(thresholds))-0.2, py_times, width=0.4, label='Python')
    axs[0, 0].bar(np.arange(len(thresholds))+0.2, cpp_times, width=0.4, label='C++')
    axs[0, 0].set_xlabel('阈值')
    axs[0, 0].set_ylabel('执行时间 (秒)')
    axs[0, 0].set_title('执行时间对比')
    axs[0, 0].set_xticks(np.arange(len(thresholds)))
    axs[0, 0].set_xticklabels([str(t) for t in thresholds])
    axs[0, 0].legend()
    axs[0, 0].grid(True)
    
    # 2. 内存使用对比
    axs[0, 1].bar(np.arange(len(thresholds))-0.2, py_memory, width=0.4, label='Python')
    axs[0, 1].bar(np.arange(len(thresholds))+0.2, cpp_memory, width=0.4, label='C++')
    axs[0, 1].set_xlabel('阈值')
    axs[0, 1].set_ylabel('峰值内存 (MB)')
    axs[0, 1].set_title('内存使用对比')
    axs[0, 1].set_xticks(np.arange(len(thresholds)))
    axs[0, 1].set_xticklabels([str(t) for t in thresholds])
    axs[0, 1].legend()
    axs[0, 1].grid(True)
    
    # 3. CPU使用对比
    axs[1, 0].bar(np.arange(len(thresholds))-0.2, py_cpu, width=0.4, label='Python')
    axs[1, 0].bar(np.arange(len(thresholds))+0.2, cpp_cpu, width=0.4, label='C++')
    axs[1, 0].set_xlabel('阈值')
    axs[1, 0].set_ylabel('平均CPU使用 (%)')
    axs[1, 0].set_title('CPU使用对比')
    axs[1, 0].set_xticks(np.arange(len(thresholds)))
    axs[1, 0].set_xticklabels([str(t) for t in thresholds])
    axs[1, 0].legend()
    axs[1, 0].grid(True)
    
    # 4. 加速比
    axs[1, 1].plot(thresholds, speedups, 'o-', linewidth=2, color='green')
    axs[1, 1].set_xlabel('阈值')
    axs[1, 1].set_ylabel('加速比 (Python/C++)')
    axs[1, 1].set_title('C++相对于Python的加速比')
    axs[1, 1].grid(True)
    
    # 保存图表
    plt.tight_layout()
    plt.savefig('efficiency_comparison.png')
    print("\n效率对比图表已保存到 'efficiency_comparison.png'")
    
    # 显示图表
    plt.show()

def print_system_info():
    """打印系统信息"""
    print("\n===== 系统信息 =====")
    print(f"操作系统: {sys.platform}")
    print(f"CPU核心数: {cpu_count()}")
    print(f"Python版本: {sys.version}")
    
    # 内存信息
    memory = psutil.virtual_memory()
    print(f"总内存: {memory.total / (1024**3):.2f} GB")
    print(f"可用内存: {memory.available / (1024**3):.2f} GB")
    
    # C++模块信息
    if HAS_CPP_MODULE:
        print("C++模块: 已安装")
    else:
        print("C++模块: 未安装")

def main():
    """主函数"""
    # 打印系统信息
    print_system_info()
    
    # 判断是使用命令行参数的模型还是生成测试网格
    if len(sys.argv) > 1:
        # 使用命令行参数指定的模型文件
        model_file = sys.argv[1]
        vertices, faces = load_mesh_file(model_file)
        
        if vertices is None or faces is None:
            print("无法加载模型，将生成随机测试网格")
            vertices, faces = generate_test_mesh(5000)
    else:
        # 生成随机测试网格
        print("\n生成随机测试网格...")
        vertices, faces = generate_test_mesh(5000)
    
    # 运行对比测试
    print("\n===== 开始算法效率对比 =====")
    results = compare_implementations(
        vertices, faces, 
        thresholds=[0.001, 0.01, 0.05, 0.1]
    )
    
    # 计算平均加速比
    avg_speedup = sum(r["speedup"] for r in results) / len(results)
    print(f"\n===== 效率对比总结 =====")
    print(f"平均加速比: {avg_speedup:.2f}x")
    
    # 内存使用比较
    avg_memory_ratio = sum(r["memory_ratio"] for r in results) / len(results)
    print(f"平均内存使用比(Python/C++): {avg_memory_ratio:.2f}x")
    
    # 可视化结果
    visualize_comparison(results)

if __name__ == "__main__":
    main() 