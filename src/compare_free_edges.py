#!/usr/bin/env python
"""
比较C++和Python实现的自由边检测算法性能
"""
import os
import sys
import time
import numpy as np
from PyQt5.QtWidgets import QApplication
import matplotlib.pyplot as plt
import subprocess
import platform

# 检查是否已安装pybind11
try:
    import pybind11
except ImportError:
    print("正在安装pybind11...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pybind11"])

# 尝试导入C++模块，如果不存在则编译
try:
    import free_edges_cpp
except ImportError:
    print("C++模块不存在，正在编译...")
    # 获取当前路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 运行编译命令
    if platform.system() == "Windows":
        compile_result = subprocess.call([sys.executable, "setup.py", "build_ext", "--inplace"], cwd=current_dir)
    else:
        compile_result = subprocess.call([sys.executable, "setup.py", "build_ext", "--inplace"], cwd=current_dir)
    
    if compile_result != 0:
        print("编译失败！请检查C++编译器和pybind11是否正确安装")
        sys.exit(1)
    
    # 再次尝试导入
    try:
        import free_edges_cpp
    except ImportError:
        print("编译成功但导入失败，可能需要重新运行此脚本")
        sys.exit(1)

# 自由边检测 - Python实现
def detect_free_edges_py(faces):
    """
    选择自由边的Python实现
    """
    # 记录开始时间
    start_time = time.time()
    
    # 用字典记录每条边出现的次数
    edge_count = {}
    
    # 遍历所有面片，收集边信息
    for face in faces:
        # 获取面片的三条边
        edge1 = tuple(sorted([face[0], face[1]]))
        edge2 = tuple(sorted([face[1], face[2]]))
        edge3 = tuple(sorted([face[2], face[0]]))
        
        # 更新边的计数
        edge_count[edge1] = edge_count.get(edge1, 0) + 1
        edge_count[edge2] = edge_count.get(edge2, 0) + 1
        edge_count[edge3] = edge_count.get(edge3, 0) + 1
    
    # 找出只出现一次的边（自由边）
    free_edges = [edge for edge, count in edge_count.items() if count == 1]
    
    # 计算执行时间
    duration = time.time() - start_time
    
    return free_edges, duration

def load_model():
    """加载大型模型"""
    print("加载3D模型...")
    
    # 设置NAS文件路径
    nas_file = os.path.join("src", "data", "complex_3d_model.nas")
    
    # 确保文件存在
    if not os.path.exists(nas_file):
        print(f"错误: 文件不存在 {nas_file}")
        print("请先运行 generate_complex_3d.py 生成文件")
        return None
    
    # 直接读取NAS文件
    vertices = []
    faces = []
    vertex_id_map = {}  # 用于存储NAS文件中的节点ID到索引的映射
    
    with open(nas_file, 'r') as f:
        lines = f.readlines()
    
    # 第一遍：读取所有顶点
    i = 0
    print(f"解析数据，共{len(lines)}行...")
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('GRID*'):
            # GRID*格式（长格式，占两行）
            if i + 1 < len(lines):
                parts1 = line.split()
                next_line = lines[i+1].strip()
                
                if next_line.startswith('*'):
                    parts2 = next_line.split()
                    
                    try:
                        # 解析节点ID和坐标
                        node_id = int(parts1[1])
                        x = float(parts1[3])
                        y = float(parts1[4])
                        z = float(parts2[1])
                        
                        # 添加到顶点列表并记录ID映射
                        vertex_id_map[node_id] = len(vertices)
                        vertices.append([x, y, z])
                    except (ValueError, IndexError):
                        pass
                    
                    i += 1  # 跳过已处理的下一行
        i += 1
    
    # 第二遍：读取所有三角形面片
    print("解析面片数据...")
    for i, line in enumerate(lines):
        if line.startswith('CTRIA3'):
            parts = line.split()
            if len(parts) >= 6:
                try:
                    # NAS文件中的节点ID从1开始，需要转换为从0开始的索引
                    n1 = int(parts[3])
                    n2 = int(parts[4])
                    n3 = int(parts[5])
                    
                    # 使用之前建立的映射转换ID
                    if n1 in vertex_id_map and n2 in vertex_id_map and n3 in vertex_id_map:
                        v1 = vertex_id_map[n1]
                        v2 = vertex_id_map[n2]
                        v3 = vertex_id_map[n3]
                        faces.append([v1, v2, v3])
                except (ValueError, IndexError):
                    pass
    
    # 转换为numpy数组
    vertices = np.array(vertices, dtype=np.float32)
    faces = np.array(faces, dtype=np.int32)
    
    print(f"模型加载完成: {len(vertices)}个顶点, {len(faces)}个面片")
    return {'vertices': vertices, 'faces': faces}

def compare_performance(mesh_data):
    """比较Python和C++实现的性能"""
    faces = mesh_data['faces']
    
    print("\n性能对比测试开始...")
    
    # 运行Python版本
    print("\n运行Python版本的自由边检测...")
    python_free_edges, python_time = detect_free_edges_py(faces)
    print(f"Python版本检测到{len(python_free_edges)}条自由边")
    print(f"执行时间: {python_time:.4f}秒")
    
    # 运行C++版本
    print("\n运行C++版本的自由边检测...")
    cpp_free_edges, cpp_time = free_edges_cpp.detect_free_edges_with_timing(faces.tolist())
    print(f"C++版本检测到{len(cpp_free_edges)}条自由边")
    print(f"执行时间: {cpp_time:.4f}秒")
    
    # 验证结果一致性
    # 将C++结果转换为Python格式进行比较
    cpp_edges_set = set(tuple(edge) for edge in cpp_free_edges)
    python_edges_set = set(python_free_edges)
    
    if len(cpp_edges_set) == len(python_edges_set) and cpp_edges_set == python_edges_set:
        print("\n验证: 两种实现的结果完全一致")
    else:
        print("\n警告: 两种实现的结果不一致!")
        print(f"Python结果数量: {len(python_edges_set)}")
        print(f"C++结果数量: {len(cpp_edges_set)}")
        common = len(cpp_edges_set.intersection(python_edges_set))
        print(f"共同结果数量: {common}")
    
    # 计算加速比
    speedup = python_time / cpp_time
    print(f"\nC++版本比Python版本快{speedup:.2f}倍")
    
    # 绘制性能对比图
    labels = ['Python', 'C++']
    times = [python_time, cpp_time]
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(labels, times, color=['blue', 'red'])
    plt.title('自由边检测算法性能对比')
    plt.ylabel('执行时间 (秒)')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # 在柱状图上添加具体数值
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                 f'{height:.4f}s', ha='center', va='bottom')
    
    # 添加加速比文本
    plt.text(0.5, max(times) * 0.5, f'加速比: {speedup:.2f}x', 
             ha='center', va='center', fontsize=14, 
             bbox=dict(facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    # 保存图表
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "free_edges_performance.png")
    plt.savefig(output_file)
    print(f"\n性能对比图表已保存至: {output_file}")
    
    # 显示图表
    plt.show()
    
    return python_time, cpp_time, speedup

def main():
    """主函数"""
    # 加载模型
    mesh_data = load_model()
    if mesh_data is None:
        return 1
    
    # 比较性能
    python_time, cpp_time, speedup = compare_performance(mesh_data)
    
    print("\n性能对比总结:")
    print(f"Python执行时间: {python_time:.4f}秒")
    print(f"C++执行时间: {cpp_time:.4f}秒")
    print(f"C++比Python快: {speedup:.2f}倍")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 