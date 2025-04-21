"""
穿刺面检测算法性能比较
比较C++和Python的穿刺面检测算法性能，并生成比较图表
"""

import numpy as np
import time
import matplotlib.pyplot as plt
import os
import sys
import importlib.util

# 导入项目中的其他模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 尝试导入C++模块，如果失败则指导用户如何编译
try:
    import pierced_faces_cpp
except ImportError:
    print("未找到C++模块，请先编译：")
    print("cd src")
    print("python setup_pierced_faces.py build_ext --inplace")
    sys.exit(1)

# 导入mesh_viewer_qt.py中的check_triangle_intersection函数
from mesh_viewer_qt import MeshViewerQt

# 创建测试网格
def create_test_mesh(num_vertices, num_faces, randomize=True):
    """创建测试网格，可以选择是否随机化顶点位置"""
    if randomize:
        # 创建随机顶点
        vertices = np.random.rand(num_vertices, 3) * 10
    else:
        # 创建规则分布的顶点
        side = int(np.ceil(np.cbrt(num_vertices)))
        x = np.linspace(0, 10, side)
        y = np.linspace(0, 10, side)
        z = np.linspace(0, 10, side)
        X, Y, Z = np.meshgrid(x, y, z)
        vertices = np.column_stack((X.flatten(), Y.flatten(), Z.flatten()))
        vertices = vertices[:num_vertices]
    
    # 创建随机面
    faces = np.zeros((num_faces, 3), dtype=np.int32)
    for i in range(num_faces):
        # 确保面片的顶点不重复
        face = np.random.choice(num_vertices, 3, replace=False)
        faces[i] = face
    
    return vertices, faces

# Python版穿刺面检测函数（使用MeshViewerQt中的算法）
def detect_pierced_faces_python(faces, vertices):
    """
    使用Python实现的穿刺面检测函数
    基于MeshViewerQt中的check_triangle_intersection函数
    """
    # 创建MeshViewerQt实例，但不创建界面
    mesh_viewer = MeshViewerQt({'vertices': vertices, 'faces': faces})
    
    # 计算每个面片的AABB包围盒
    face_bboxes = []
    for face_idx in range(len(faces)):
        face_verts = vertices[faces[face_idx]]
        min_coords = np.min(face_verts, axis=0)
        max_coords = np.max(face_verts, axis=0)
        face_bboxes.append((min_coords, max_coords))
    
    # 存储相交面片
    intersecting_faces = set()
    
    # 记录开始时间
    start_time = time.time()
    
    # 简化版本：暴力循环检测所有可能的面片对
    for i in range(len(faces)):
        face1_verts = vertices[faces[i]]
        min1, max1 = face_bboxes[i]
        
        for j in range(i + 1, len(faces)):
            # 快速AABB包围盒检测
            min2, max2 = face_bboxes[j]
            if np.all(max1 >= min2) and np.all(max2 >= min1):
                face2_verts = vertices[faces[j]]
                # 只有当两个面片不共享顶点时才检查相交
                if not set(faces[i]).intersection(set(faces[j])):
                    if mesh_viewer.check_triangle_intersection(face1_verts, face2_verts):
                        intersecting_faces.add(i)
                        intersecting_faces.add(j)
    
    # 计算用时
    elapsed_time = time.time() - start_time
    
    return list(intersecting_faces), elapsed_time

# 主测试函数
def run_comparison_tests():
    """运行性能比较测试并生成图表"""
    # 生成不同规模的测试数据
    test_sizes = [
        (100, 100),    # 100顶点，100面
        (200, 400),    # 200顶点，400面
        (500, 1000),   # 500顶点，1000面
        (1000, 2000),  # 1000顶点，2000面
        (2000, 4000),  # 2000顶点，4000面
    ]
    
    # 存储测试结果
    python_times = []
    cpp_times = []
    python_counts = []
    cpp_counts = []
    face_counts = []
    
    # 运行测试
    for num_vertices, num_faces in test_sizes:
        print(f"测试规模: {num_vertices}顶点, {num_faces}面")
        
        # 创建测试网格
        vertices, faces = create_test_mesh(num_vertices, num_faces)
        face_counts.append(num_faces)
        
        # 测试Python版本
        print("  运行Python版本...")
        py_results, py_time = detect_pierced_faces_python(faces, vertices)
        python_times.append(py_time)
        python_counts.append(len(py_results))
        print(f"  Python检测到{len(py_results)}个穿刺面，用时{py_time:.4f}秒")
        
        # 测试C++版本
        print("  运行C++版本...")
        cpp_results, cpp_time = pierced_faces_cpp.detect_pierced_faces_with_timing(faces, vertices)
        cpp_times.append(cpp_time)
        cpp_counts.append(len(cpp_results))
        print(f"  C++检测到{len(cpp_results)}个穿刺面，用时{cpp_time:.4f}秒")
        
        # 检查结果一致性
        py_set = set(py_results)
        cpp_set = set(cpp_results)
        if py_set == cpp_set:
            print("  结果一致 ✓")
        else:
            precision = len(cpp_set.intersection(py_set)) / len(cpp_set) if len(cpp_set) > 0 else 0
            recall = len(cpp_set.intersection(py_set)) / len(py_set) if len(py_set) > 0 else 0
            print(f"  结果不完全一致: 精确率={precision:.2f}, 召回率={recall:.2f}")
        
        print()
    
    # 生成性能比较图
    plt.figure(figsize=(12, 10))
    
    # 1. 执行时间对比图
    plt.subplot(2, 1, 1)
    bar_width = 0.35
    x = np.arange(len(face_counts))
    
    plt.bar(x - bar_width/2, python_times, bar_width, label='Python')
    plt.bar(x + bar_width/2, cpp_times, bar_width, label='C++')
    
    plt.xlabel('面片数量')
    plt.ylabel('执行时间 (秒)')
    plt.title('穿刺面检测算法执行时间对比')
    plt.xticks(x, face_counts)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # 添加具体时间数字和加速比
    for i, (py_time, cpp_time) in enumerate(zip(python_times, cpp_times)):
        speedup = py_time / cpp_time if cpp_time > 0 else float('inf')
        plt.text(i - bar_width/2, py_time + 0.05, f"{py_time:.2f}s", ha='center', va='bottom')
        plt.text(i + bar_width/2, cpp_time + 0.05, f"{cpp_time:.2f}s", ha='center', va='bottom')
        plt.text(i, max(py_time, cpp_time) + 0.1, f"加速比: {speedup:.2f}x", ha='center', va='bottom')
    
    # 2. 检测到的穿刺面数量对比
    plt.subplot(2, 1, 2)
    plt.plot(face_counts, python_counts, 'o-', label='Python检测数量')
    plt.plot(face_counts, cpp_counts, 's-', label='C++检测数量')
    
    plt.xlabel('面片数量')
    plt.ylabel('检测到的穿刺面数量')
    plt.title('穿刺面检测算法结果对比')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # 保存图表
    plt.tight_layout()
    
    # 确保输出目录存在
    output_dir = os.path.join(current_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, 'pierced_faces_comparison.png')
    plt.savefig(output_path)
    plt.close()
    
    print(f"比较图表已保存到: {output_path}")
    
    # 输出总体性能提升
    avg_speedup = np.mean([py_time / cpp_time for py_time, cpp_time in zip(python_times, cpp_times)])
    print(f"C++版本平均提速: {avg_speedup:.2f}倍")
    
    # 返回图表路径
    return output_path

if __name__ == "__main__":
    output_image = run_comparison_tests()
    print(f"测试完成，图表保存在: {output_image}") 