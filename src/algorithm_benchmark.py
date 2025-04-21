#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
算法性能基准测试
用于比较Python和C++版本的相邻面检测算法的性能差异
"""

import numpy as np
import time
import os
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# 添加项目根目录到Python路径
current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
project_root = current_dir.parent
sys.path.append(str(project_root))

# 导入相关算法
from src.algorithms.self_intersection_algorithm import SelfIntersectionAlgorithm

try:
    import self_intersection_cpp
    HAS_CPP_MODULE = True
except ImportError:
    HAS_CPP_MODULE = False
    print("警告: C++模块未找到，将只评估Python版本")

class AlgorithmBenchmark:
    """算法基准测试类"""
    
    def __init__(self, mesh_data=None):
        """
        初始化基准测试
        
        参数:
        mesh_data (dict): 包含顶点和面片数据的字典
        """
        self.mesh_data = mesh_data
        self.results = {}
        
    def load_mesh_from_file(self, file_path):
        """
        从文件加载网格数据
        
        参数:
        file_path: 网格文件路径
        """
        # 这里简化处理，实际应用中可能需要更复杂的网格加载逻辑
        # 假设文件是NumPy存档格式(.npz)，包含vertices和faces数组
        try:
            data = np.load(file_path)
            self.mesh_data = {
                'vertices': data['vertices'],
                'faces': data['faces']
            }
            print(f"已加载网格数据: {len(self.mesh_data['vertices'])} 个顶点, {len(self.mesh_data['faces'])} 个面片")
            return True
        except Exception as e:
            print(f"加载网格数据失败: {str(e)}")
            return False
            
    def generate_test_mesh(self, num_vertices=1000, complexity=1.0):
        """
        生成测试用的网格数据
        
        参数:
        num_vertices: 顶点数量
        complexity: 复杂度系数，影响网格的复杂性
        """
        # 生成随机顶点
        vertices = np.random.randn(num_vertices, 3) * complexity
        
        # 生成面片 (简化的三角剖分)
        # 这里使用一个简单的方法来生成面片，实际应用中可能需要更复杂的三角剖分算法
        faces = []
        max_faces = min(num_vertices * 2, 10000)  # 限制面片数量
        
        for i in range(0, min(num_vertices - 2, max_faces)):
            # 随机选择三个顶点形成一个面片
            indices = np.random.choice(num_vertices, 3, replace=False)
            faces.append(indices)
        
        self.mesh_data = {
            'vertices': vertices,
            'faces': np.array(faces)
        }
        
        print(f"已生成测试网格: {len(vertices)} 个顶点, {len(faces)} 个面片")
        return True
    
    def run_python_algorithm(self, threshold=0.001, sampling_rate=1.0, timeout=300):
        """
        运行Python版本的算法
        
        参数:
        threshold: 判断阈值
        sampling_rate: 采样率
        timeout: 超时时间(秒)
        
        返回:
        tuple: (相邻面列表, 执行时间)
        """
        if not self.mesh_data:
            print("错误: 没有可用的网格数据")
            return [], 0
            
        # 创建算法实例
        algorithm = SelfIntersectionAlgorithm(self.mesh_data)
        
        # 禁用C++实现，强制使用Python实现
        algorithm.use_cpp = False
        
        # 记录开始时间
        start_time = time.time()
        
        # 执行算法
        adjacent_faces = algorithm.execute(
            threshold=threshold,
            sampling_rate=sampling_rate,
            timeout=timeout,
            auto_set=False
        )
        
        # 计算执行时间
        execution_time = time.time() - start_time
        
        print(f"Python实现: 找到 {len(adjacent_faces)} 个相邻面片，用时 {execution_time:.4f} 秒")
        
        return adjacent_faces, execution_time
    
    def run_cpp_algorithm(self, threshold=0.001, sampling_rate=1.0, timeout=300):
        """
        运行C++版本的算法
        
        参数:
        threshold: 判断阈值
        sampling_rate: 采样率
        timeout: 超时时间(秒)
        
        返回:
        tuple: (相邻面列表, 执行时间)
        """
        if not HAS_CPP_MODULE:
            print("错误: C++模块未找到")
            return [], 0
            
        if not self.mesh_data:
            print("错误: 没有可用的网格数据")
            return [], 0
            
        vertices = self.mesh_data['vertices']
        faces = self.mesh_data['faces']
        
        try:
            # 调用C++实现
            adjacent_faces, execution_time = self_intersection_cpp.detect_self_intersections_with_timing(
                vertices, faces, float(threshold)
            )
            
            print(f"C++实现: 找到 {len(adjacent_faces)} 个相邻面片，用时 {execution_time:.4f} 秒")
            
            return adjacent_faces, execution_time
            
        except Exception as e:
            print(f"C++算法执行失败: {str(e)}")
            return [], 0
    
    def benchmark(self, thresholds=None, sampling_rates=None, vertex_counts=None):
        """
        进行基准测试
        
        参数:
        thresholds: 阈值列表
        sampling_rates: 采样率列表
        vertex_counts: 顶点数量列表，用于生成不同大小的测试网格
        
        返回:
        dict: 基准测试结果
        """
        if thresholds is None:
            thresholds = [0.001, 0.01, 0.1]
            
        if sampling_rates is None:
            sampling_rates = [0.25, 0.5, 1.0]
            
        if vertex_counts is None:
            vertex_counts = [1000, 5000, 10000]
        
        results = {
            'thresholds': {},
            'sampling_rates': {},
            'mesh_sizes': {}
        }
        
        # 测试不同的阈值
        print("\n===== 测试不同的阈值 =====")
        for threshold in thresholds:
            print(f"\n阈值: {threshold}")
            
            # 确保有测试数据
            if not self.mesh_data:
                self.generate_test_mesh(5000)
                
            # 运行Python实现
            py_faces, py_time = self.run_python_algorithm(threshold=threshold)
            
            # 运行C++实现(如果可用)
            cpp_faces, cpp_time = [], 0
            if HAS_CPP_MODULE:
                cpp_faces, cpp_time = self.run_cpp_algorithm(threshold=threshold)
                
            results['thresholds'][threshold] = {
                'python': {'faces': len(py_faces), 'time': py_time},
                'cpp': {'faces': len(cpp_faces), 'time': cpp_time}
            }
        
        # 测试不同的采样率
        print("\n===== 测试不同的采样率 =====")
        for rate in sampling_rates:
            print(f"\n采样率: {rate}")
            
            # 确保有测试数据
            if not self.mesh_data:
                self.generate_test_mesh(5000)
                
            # 运行Python实现
            py_faces, py_time = self.run_python_algorithm(sampling_rate=rate)
            
            # 运行C++实现(如果可用)
            cpp_faces, cpp_time = [], 0
            if HAS_CPP_MODULE:
                cpp_faces, cpp_time = self.run_cpp_algorithm(sampling_rate=rate)
                
            results['sampling_rates'][rate] = {
                'python': {'faces': len(py_faces), 'time': py_time},
                'cpp': {'faces': len(cpp_faces), 'time': cpp_time}
            }
            
        # 测试不同大小的网格
        print("\n===== 测试不同大小的网格 =====")
        for count in vertex_counts:
            print(f"\n顶点数量: {count}")
            
            # 生成测试网格
            self.generate_test_mesh(count)
            
            # 运行Python实现
            py_faces, py_time = self.run_python_algorithm()
            
            # 运行C++实现(如果可用)
            cpp_faces, cpp_time = [], 0
            if HAS_CPP_MODULE:
                cpp_faces, cpp_time = self.run_cpp_algorithm()
                
            results['mesh_sizes'][count] = {
                'python': {'faces': len(py_faces), 'time': py_time},
                'cpp': {'faces': len(cpp_faces), 'time': cpp_time}
            }
            
        self.results = results
        return results
    
    def visualize_results(self):
        """可视化基准测试结果"""
        if not self.results:
            print("没有可视化的结果")
            return
            
        # 创建图表
        fig, axs = plt.subplots(3, 1, figsize=(10, 15))
        
        # 1. 阈值对比
        if self.results.get('thresholds'):
            thresholds = list(self.results['thresholds'].keys())
            py_times = [self.results['thresholds'][t]['python']['time'] for t in thresholds]
            cpp_times = [self.results['thresholds'][t]['cpp']['time'] for t in thresholds]
            
            axs[0].plot(thresholds, py_times, 'o-', label='Python')
            if HAS_CPP_MODULE:
                axs[0].plot(thresholds, cpp_times, 's-', label='C++')
            axs[0].set_xlabel('阈值')
            axs[0].set_ylabel('执行时间 (秒)')
            axs[0].set_title('不同阈值下的算法性能对比')
            axs[0].legend()
            axs[0].grid(True)
        
        # 2. 采样率对比
        if self.results.get('sampling_rates'):
            rates = list(self.results['sampling_rates'].keys())
            py_times = [self.results['sampling_rates'][r]['python']['time'] for r in rates]
            cpp_times = [self.results['sampling_rates'][r]['cpp']['time'] for r in rates]
            
            axs[1].plot(rates, py_times, 'o-', label='Python')
            if HAS_CPP_MODULE:
                axs[1].plot(rates, cpp_times, 's-', label='C++')
            axs[1].set_xlabel('采样率')
            axs[1].set_ylabel('执行时间 (秒)')
            axs[1].set_title('不同采样率下的算法性能对比')
            axs[1].legend()
            axs[1].grid(True)
        
        # 3. 网格大小对比
        if self.results.get('mesh_sizes'):
            sizes = list(self.results['mesh_sizes'].keys())
            py_times = [self.results['mesh_sizes'][s]['python']['time'] for s in sizes]
            cpp_times = [self.results['mesh_sizes'][s]['cpp']['time'] for s in sizes]
            
            axs[2].plot(sizes, py_times, 'o-', label='Python')
            if HAS_CPP_MODULE:
                axs[2].plot(sizes, cpp_times, 's-', label='C++')
            axs[2].set_xlabel('顶点数量')
            axs[2].set_ylabel('执行时间 (秒)')
            axs[2].set_title('不同网格大小下的算法性能对比')
            axs[2].legend()
            axs[2].grid(True)
        
        plt.tight_layout()
        
        # 保存图表
        plt.savefig('benchmark_results.png')
        print("基准测试结果图表已保存到 'benchmark_results.png'")
        
        # 显示图表
        plt.show()
        
    def print_summary(self):
        """打印性能测试摘要"""
        if not self.results:
            print("没有可用的结果摘要")
            return
            
        print("\n====== 性能测试摘要 ======")
        
        # 计算平均加速比
        speedups = []
        
        # 从阈值测试中获取加速比
        if self.results.get('thresholds'):
            for threshold, data in self.results['thresholds'].items():
                py_time = data['python']['time']
                cpp_time = data['cpp']['time']
                if cpp_time > 0:
                    speedup = py_time / cpp_time
                    speedups.append(speedup)
                    print(f"阈值 {threshold}: Python {py_time:.4f}秒, C++ {cpp_time:.4f}秒, 加速比: {speedup:.2f}x")
        
        # 从采样率测试中获取加速比
        if self.results.get('sampling_rates'):
            for rate, data in self.results['sampling_rates'].items():
                py_time = data['python']['time']
                cpp_time = data['cpp']['time']
                if cpp_time > 0:
                    speedup = py_time / cpp_time
                    speedups.append(speedup)
                    print(f"采样率 {rate}: Python {py_time:.4f}秒, C++ {cpp_time:.4f}秒, 加速比: {speedup:.2f}x")
                    
        # 从网格大小测试中获取加速比
        if self.results.get('mesh_sizes'):
            for size, data in self.results['mesh_sizes'].items():
                py_time = data['python']['time']
                cpp_time = data['cpp']['time']
                if cpp_time > 0:
                    speedup = py_time / cpp_time
                    speedups.append(speedup)
                    print(f"顶点数 {size}: Python {py_time:.4f}秒, C++ {cpp_time:.4f}秒, 加速比: {speedup:.2f}x")
        
        # 计算平均加速比
        if speedups:
            avg_speedup = sum(speedups) / len(speedups)
            print(f"\n平均加速比: {avg_speedup:.2f}x")
            print(f"C++实现比Python实现平均快 {avg_speedup:.2f} 倍")
        else:
            print("\n无法计算加速比 (C++模块未找到或执行失败)")

def main():
    """主函数"""
    benchmark = AlgorithmBenchmark()
    
    # 生成测试网格或加载已有网格
    # benchmark.load_mesh_from_file("mesh_data.npz")  # 如果有现成的网格数据文件
    benchmark.generate_test_mesh(5000)  # 生成测试网格
    
    # 运行基准测试
    benchmark.benchmark(
        thresholds=[0.001, 0.005, 0.01, 0.05, 0.1],
        sampling_rates=[0.1, 0.25, 0.5, 0.75, 1.0],
        vertex_counts=[1000, 2500, 5000, 7500, 10000]
    )
    
    # 打印测试摘要
    benchmark.print_summary()
    
    # 可视化结果
    benchmark.visualize_results()

if __name__ == "__main__":
    main() 