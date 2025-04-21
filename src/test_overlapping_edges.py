"""
重叠边检测算法测试脚本
比较Python和C++实现的性能差异
"""

import os
import time
import numpy as np
import matplotlib.pyplot as plt
import sys
from pathlib import Path

# 将项目根目录添加到路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.append(str(project_root))

# 导入我们的算法
from src.algorithms.overlapping_edges_algorithm import OverlappingEdgesAlgorithm

def create_test_mesh(num_vertices=1000, num_faces=2000, duplicate_rate=0.1):
    """创建一个包含重叠边的测试网格"""
    # 随机生成顶点
    vertices = np.random.rand(num_vertices, 3) * 100
    
    # 随机生成面片（三角形）
    faces = np.random.randint(0, num_vertices, (num_faces, 3))
    
    # 添加一些重叠边
    num_duplicates = int(num_faces * duplicate_rate)
    for i in range(num_duplicates):
        # 选择一个随机面
        face_idx = np.random.randint(0, num_faces)
        # 复制这个面的一条边到另一个面
        edge = [faces[face_idx][0], faces[face_idx][1]]
        
        # 创建一个新面，共享这条边
        new_face = np.array([edge[0], edge[1], np.random.randint(0, num_vertices)])
        
        # 替换一个现有面
        replace_idx = np.random.randint(0, num_faces)
        faces[replace_idx] = new_face
    
    return vertices, faces

def test_algorithm(vertices, faces, tolerance=1e-6):
    """测试重叠边检测算法的Python和C++实现"""
    print(f"测试网格包含 {len(vertices)} 个顶点和 {len(faces)} 个面片")
    print(f"使用容差: {tolerance}")
    print("-" * 50)
    
    # 创建网格数据字典，符合算法类的要求
    mesh_data = {
        'vertices': vertices,
        'faces': faces
    }
    
    # 测试Python实现
    print("\n使用Python实现检测重叠边...")
    algorithm_py = OverlappingEdgesAlgorithm(mesh_data, tolerance)
    # 确保设置了网格数据
    algorithm_py.set_mesh_data(mesh_data)
    
    start_time = time.time()
    py_result = algorithm_py.detect_overlapping_edges_python()
    py_time = time.time() - start_time
    print(f"Python实现检测到 {len(py_result)} 个重叠边")
    print(f"Python实现用时: {py_time:.4f}秒")
    
    # 测试C++实现
    print("\n使用C++实现检测重叠边...")
    try:
        # 检查是否可以导入C++模块
        try:
            import overlapping_edges_cpp
            has_cpp = True
        except ImportError:
            has_cpp = False
            
        if has_cpp:
            # 确保顶点和面片数据是numpy数组
            vertices_array = np.array(vertices, dtype=np.float64)
            faces_array = np.array(faces, dtype=np.int32)
            
            start_time = time.time()
            cpp_result, cpp_time = overlapping_edges_cpp.detect_overlapping_edges_with_timing(
                vertices_array, faces_array, tolerance)
            
            # 转换结果为元组列表，便于比较
            cpp_result = [tuple(edge) for edge in cpp_result]
            
            print(f"C++实现检测到 {len(cpp_result)} 个重叠边")
            print(f"C++实现用时: {cpp_time:.4f}秒")
            
            # 计算加速比
            speedup = py_time / cpp_time if cpp_time > 0 else float('inf')
            print(f"\nC++算法加速比: {speedup:.2f}倍")
            
            # 验证结果一致性
            py_result_set = set(map(tuple, py_result))
            cpp_result_set = set(map(tuple, cpp_result))
            
            if len(py_result_set) == len(cpp_result_set) and py_result_set == cpp_result_set:
                print("两种实现结果完全一致 ✓")
            else:
                print("警告: 两种实现的结果不一致 ✗")
                print(f"Python结果数量: {len(py_result_set)}, C++结果数量: {len(cpp_result_set)}")
                
            return py_time, cpp_time, py_result, cpp_result
        else:
            print("无法导入C++模块，请确保已编译overlapping_edges_cpp模块")
            return py_time, None, py_result, None
    
    except Exception as e:
        print(f"C++实现运行时错误: {e}")
        return py_time, None, py_result, None

def visualize_performance(sizes, py_times, cpp_times):
    """可视化性能对比"""
    plt.figure(figsize=(10, 6))
    
    plt.plot(sizes, py_times, 'o-', label='Python实现')
    if all(t is not None for t in cpp_times):
        plt.plot(sizes, cpp_times, 'o-', label='C++实现')
    
    plt.xlabel('面片数量')
    plt.ylabel('执行时间 (秒)')
    plt.title('重叠边检测算法性能对比')
    plt.legend()
    plt.grid(True)
    
    # 保存图表
    output_dir = os.path.join(current_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "overlapping_edges_performance.png")
    plt.savefig(output_path)
    print(f"\n性能对比图已保存到: {output_path}")

def main():
    """主函数"""
    # 不同大小的测试用例
    mesh_sizes = [1000, 2000, 5000, 10000]
    py_times = []
    cpp_times = []
    
    for size in mesh_sizes:
        print(f"\n测试网格大小: {size} 个面片")
        print("=" * 50)
        
        vertices, faces = create_test_mesh(size//2, size, 0.1)
        py_time, cpp_time, _, _ = test_algorithm(vertices, faces)
        
        py_times.append(py_time)
        cpp_times.append(cpp_time)
    
    # 可视化性能对比
    visualize_performance(mesh_sizes, py_times, cpp_times)

if __name__ == "__main__":
    main() 