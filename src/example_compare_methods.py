"""
穿刺面检测算法对比示例
此脚本创建一个包含穿刺面的模型，并使用C++和Python算法分别检测，对比性能
"""

import numpy as np
import time
import os
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
import matplotlib.pyplot as plt

# 初始化QApplication
app = QApplication(sys.argv)

# 导入项目中的其他模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 导入mesh_viewer_qt模块
from mesh_viewer_qt import MeshViewerQt

# 尝试导入C++模块
try:
    import pierced_faces_cpp
    HAS_CPP_MODULE = True
except ImportError:
    HAS_CPP_MODULE = False
    print("警告：未找到C++模块，请先编译：")
    print("cd src")
    print("python setup_pierced_faces.py build_ext --inplace")
    sys.exit(1)

# 创建一个包含穿刺面的简单模型
def create_intersecting_model(num_faces=1000):
    """创建一个包含穿刺面的简单模型"""
    # 创建一组随机顶点
    num_vertices = num_faces * 2  # 确保有足够的顶点
    vertices = np.random.rand(num_vertices, 3) * 10
    
    # 创建面片
    faces = []
    for i in range(num_faces - 10):  # 普通面片
        # 随机选择3个顶点索引
        v1, v2, v3 = np.random.choice(num_vertices, 3, replace=False)
        faces.append([v1, v2, v3])
    
    # 创建一些穿刺面（10个，固定位置，确保相交）
    # 面片1：XY平面上的一个三角形
    f1_v1 = len(vertices)
    vertices = np.append(vertices, [[0, 0, 0]], axis=0)
    f1_v2 = len(vertices)
    vertices = np.append(vertices, [[2, 0, 0]], axis=0)
    f1_v3 = len(vertices)
    vertices = np.append(vertices, [[1, 2, 0]], axis=0)
    faces.append([f1_v1, f1_v2, f1_v3])
    
    # 面片2：与面片1相交的三角形
    f2_v1 = len(vertices)
    vertices = np.append(vertices, [[1, 1, -1]], axis=0)
    f2_v2 = len(vertices)
    vertices = np.append(vertices, [[2, 1, 1]], axis=0)
    f2_v3 = len(vertices)
    vertices = np.append(vertices, [[0, 1, 1]], axis=0)
    faces.append([f2_v1, f2_v2, f2_v3])
    
    # 面片3和4：相交于Z轴
    f3_v1 = len(vertices)
    vertices = np.append(vertices, [[3, 0, 0]], axis=0)
    f3_v2 = len(vertices)
    vertices = np.append(vertices, [[5, 0, 0]], axis=0)
    f3_v3 = len(vertices)
    vertices = np.append(vertices, [[4, 0, 2]], axis=0)
    faces.append([f3_v1, f3_v2, f3_v3])
    
    f4_v1 = len(vertices)
    vertices = np.append(vertices, [[4, -1, 1]], axis=0)
    f4_v2 = len(vertices)
    vertices = np.append(vertices, [[4, 1, 1]], axis=0)
    f4_v3 = len(vertices)
    vertices = np.append(vertices, [[4, 0, -1]], axis=0)
    faces.append([f4_v1, f4_v2, f4_v3])
    
    # 添加更多的相交面片
    for i in range(6):
        v1 = len(vertices)
        vertices = np.append(vertices, [[i*2, i*1.5, 5]], axis=0)
        v2 = len(vertices)
        vertices = np.append(vertices, [[i*2+1, i*1.5+1, 5]], axis=0)
        v3 = len(vertices)
        vertices = np.append(vertices, [[i*2+0.5, i*1.5+0.5, 7]], axis=0)
        faces.append([v1, v2, v3])
        
        v4 = len(vertices)
        vertices = np.append(vertices, [[i*2+0.5, i*1.5+0.5, 4]], axis=0)
        v5 = len(vertices)
        vertices = np.append(vertices, [[i*2+1.5, i*1.5+0.5, 6]], axis=0)
        v6 = len(vertices)
        vertices = np.append(vertices, [[i*2-0.5, i*1.5+0.5, 6]], axis=0)
        faces.append([v4, v5, v6])
    
    return np.array(vertices), np.array(faces)

# Python版穿刺面检测函数（从MeshViewerQt中提取）
def detect_pierced_faces_python(faces, vertices):
    """使用Python检测穿刺面"""
    # 创建一个MeshViewerQt实例，但不显示界面
    mesh_viewer = MeshViewerQt({'vertices': vertices, 'faces': faces})
    
    # 开始计时
    start_time = time.time()
    
    # 使用直接检测方法，不使用八叉树
    # 计算每个面片的AABB包围盒
    face_bboxes = []
    for face_idx in range(len(faces)):
        face_verts = vertices[faces[face_idx]]
        min_coords = np.min(face_verts, axis=0)
        max_coords = np.max(face_verts, axis=0)
        face_bboxes.append((min_coords, max_coords))
    
    # 存储相交面片
    intersecting_faces = set()
    
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
    
    # 记录结果
    mesh_viewer.selected_faces = list(intersecting_faces)
    
    # 计时结束
    end_time = time.time()
    
    # 返回结果
    return list(intersecting_faces), end_time - start_time

# C++版穿刺面检测函数
def detect_pierced_faces_cpp(faces, vertices):
    """使用C++检测穿刺面"""
    # 开始计时
    start_time = time.time()
    
    # 调用C++函数
    result, cpp_time = pierced_faces_cpp.detect_pierced_faces_with_timing(faces, vertices)
    
    # 计时结束
    end_time = time.time()
    
    return result, cpp_time

# 主函数
def main():
    """主函数"""
    # 创建一个包含穿刺面的模型
    print("创建测试模型...")
    vertices, faces = create_intersecting_model(num_faces=500)
    print(f"模型包含 {len(vertices)} 个顶点和 {len(faces)} 个面片")
    
    # 使用Python算法检测
    print("\n使用Python算法检测穿刺面...")
    try:
        py_start_time = time.time()
        py_result, py_time = detect_pierced_faces_python(faces, vertices)
        py_total_time = time.time() - py_start_time
        print(f"Python算法检测到 {len(py_result)} 个穿刺面")
        print(f"Python算法用时: {py_time:.4f}秒 (总用时: {py_total_time:.4f}秒)")
    except Exception as e:
        print(f"Python算法出错: {str(e)}")
        py_result = []
        py_time = 0
        py_total_time = 0
    
    # 使用C++算法检测
    print("\n使用C++算法检测穿刺面...")
    try:
        cpp_start_time = time.time()
        cpp_result, cpp_time = detect_pierced_faces_cpp(faces, vertices)
        cpp_total_time = time.time() - cpp_start_time
        print(f"C++算法检测到 {len(cpp_result)} 个穿刺面")
        print(f"C++算法用时: {cpp_time:.4f}秒 (总用时: {cpp_total_time:.4f}秒)")
    except Exception as e:
        print(f"C++算法出错: {str(e)}")
        cpp_result = []
        cpp_time = 0
        cpp_total_time = 0
    
    # 比较结果
    if py_result and cpp_result:
        py_set = set(py_result)
        cpp_set = set(cpp_result)
        if py_set == cpp_set:
            print("\n两种算法结果完全一致 ✓")
        else:
            common = len(py_set.intersection(cpp_set))
            precision = common / len(cpp_set) if len(cpp_set) > 0 else 0
            recall = common / len(py_set) if len(py_set) > 0 else 0
            print(f"\n两种算法结果不完全一致:")
            print(f"共同检测到的穿刺面: {common} 个")
            print(f"精确率: {precision:.2f}, 召回率: {recall:.2f}")
            print(f"Python独有: {len(py_set - cpp_set)} 个")
            print(f"C++独有: {len(cpp_set - py_set)} 个")
    
    # 计算加速比
    if cpp_time > 0 and py_time > 0:
        speedup = py_time / cpp_time
        print(f"\nC++算法加速比: {speedup:.2f}倍")
    
    # 生成性能对比图
    if py_time > 0 or cpp_time > 0:
        plt.figure(figsize=(10, 6))
        labels = ['Python', 'C++']
        times = [py_time, cpp_time]
        plt.bar(labels, times, color=['blue', 'red'])
        plt.ylabel('执行时间 (秒)')
        plt.title(f'穿刺面检测算法性能对比 ({len(faces)} 个面片)')
        plt.grid(True, linestyle='--', alpha=0.7)

        # 添加时间标签
        for i, v in enumerate(times):
            if v > 0:
                plt.text(i, v + 0.05, f"{v:.4f}s", ha='center')

        if cpp_time > 0 and py_time > 0:
            plt.text(0.5, max(times) * 1.1, f"加速比: {speedup:.2f}倍", 
                    ha='center', fontsize=12, fontweight='bold')

        # 保存图表
        output_dir = os.path.join(current_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'algorithm_comparison.png')
        plt.savefig(output_path)
        plt.close()

        print(f"\n性能对比图已保存到: {output_path}")
    
    # 使用MeshViewerQt显示模型
    print("\n启动网格查看器...")
    
    # 创建MeshViewerQt实例
    viewer = MeshViewerQt({
        'vertices': vertices,
        'faces': faces
    })
    
    # 显示界面
    viewer.show()
    
    # 显示提示信息
    QMessageBox.information(viewer, "穿刺面检测", 
                           f"模型已加载，包含 {len(faces)} 个面片。\n\n"
                           f"Python算法检测到 {len(py_result)} 个穿刺面，用时 {py_time:.4f}秒\n"
                           f"C++算法检测到 {len(cpp_result)} 个穿刺面，用时 {cpp_time:.4f}秒\n\n"
                           f"加速比: {speedup:.2f}倍\n\n"
                           "点击界面右侧的 '交叉面' 按钮执行检测")
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 