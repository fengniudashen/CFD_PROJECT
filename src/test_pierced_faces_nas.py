"""
使用实际NAS文件测试穿刺面检测算法性能
比较C++和Python的穿刺面检测算法在实际复杂模型上的性能
"""

import numpy as np
import time
import os
import sys
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication
import threading
import _thread
import argparse  # 添加argparse用于解析命令行参数

# 初始化QApplication
app = QApplication(sys.argv)

# 解析命令行参数
parser = argparse.ArgumentParser(description='测试穿刺面检测算法性能')
parser.add_argument('--sample', type=float, default=5000, help='采样面片数量，0表示使用所有面片')
parser.add_argument('--model', type=str, default=None, help='要测试的模型文件路径')
args = parser.parse_args()

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 尝试导入C++模块，如果失败则给出提示
try:
    import pierced_faces_cpp
except ImportError:
    print("未找到C++模块，请先编译：")
    print("cd src")
    print("python setup_pierced_faces.py build_ext --inplace")
    sys.exit(1)

# 导入相关模块
from mesh_viewer_qt import MeshViewerQt
from compare_pierced_faces import detect_pierced_faces_python

# 超时处理函数
def timeout_handler():
    _thread.interrupt_main()

# 设置超时时间（秒）
TIMEOUT = 300  # 5分钟超时

# 检查NAS文件是否存在
if args.model:
    # 使用命令行指定的模型
    nas_file = args.model
    if not os.path.isabs(nas_file):
        # 如果提供的是相对路径，转换为绝对路径
        nas_file = os.path.join(current_dir, nas_file)
else:
    # 使用默认的复杂3D模型
    nas_file = os.path.join(current_dir, 'data', 'complex_3d_model.nas')

if not os.path.exists(nas_file):
    print(f"错误: 找不到NAS文件 '{nas_file}'")
    print("请检查文件路径是否正确")
    sys.exit(1)

# 使用mesh_reader读取NAS文件
try:
    # 尝试导入mesh_reader
    from mesh_reader import create_mesh_reader, read_nas_file
    print(f"正在读取NAS文件: {nas_file}")
    print("这可能需要一些时间，请耐心等待...")
    
    # 读取NAS文件
    mesh_data = read_nas_file(nas_file)
    vertices = mesh_data['vertices']
    faces = mesh_data['faces']
    
    print(f"文件读取完成，共有 {len(vertices)} 个顶点和 {len(faces)} 个面片")
except Exception as e:
    print(f"读取NAS文件时出错: {str(e)}")
    # 如果特定的mesh_reader读取失败，使用简单方法读取文件
    print("尝试使用备用方法读取...")
    
    # 简单的NAS文件读取函数
    def simple_read_nas(file_path):
        vertices = []
        faces = []
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('GRID'):
                    # 解析顶点行
                    parts = line.split()
                    if len(parts) >= 7:
                        x = float(parts[3])
                        y = float(parts[4])
                        z = float(parts[5])
                        vertices.append([x, y, z])
                elif line.startswith('CTRIA3'):
                    # 解析三角形面片行
                    parts = line.split()
                    if len(parts) >= 7:
                        v1 = int(parts[3]) - 1  # NAS文件索引从1开始
                        v2 = int(parts[4]) - 1
                        v3 = int(parts[5]) - 1
                        faces.append([v1, v2, v3])
        
        return {
            'vertices': np.array(vertices),
            'faces': np.array(faces)
        }
    
    try:
        mesh_data = simple_read_nas(nas_file)
        vertices = mesh_data['vertices']
        faces = mesh_data['faces']
        print(f"备用读取方法成功，共有 {len(vertices)} 个顶点和 {len(faces)} 个面片")
    except Exception as e2:
        print(f"备用读取方法也失败: {str(e2)}")
        sys.exit(1)

# 如果模型太大，可以采样一部分面片来测试
MAX_FACES = int(args.sample) if args.sample > 0 else sys.maxsize  # 使用参数指定的采样数量
if len(faces) > MAX_FACES:
    print(f"模型面片数量({len(faces)})超过限制({MAX_FACES})，将随机采样进行测试")
    # 随机选择面片
    indices = np.random.choice(len(faces), MAX_FACES, replace=False)
    sampled_faces = faces[indices]
    # 收集所有用到的顶点
    used_vertices = set()
    for face in sampled_faces:
        for vertex in face:
            used_vertices.add(vertex)
    
    # 创建顶点映射
    vertex_map = {}
    new_vertices = []
    for i, v_idx in enumerate(used_vertices):
        vertex_map[v_idx] = i
        new_vertices.append(vertices[v_idx])
    
    # 重新映射面片索引
    new_faces = []
    for face in sampled_faces:
        new_face = [vertex_map[v] for v in face]
        new_faces.append(new_face)
    
    vertices = np.array(new_vertices)
    faces = np.array(new_faces)
    print(f"采样后: {len(vertices)} 个顶点和 {len(faces)} 个面片")

# 运行Python版本的穿刺面检测
print("\n运行Python版本的穿刺面检测...")
py_results = []
py_time = 0
py_total_time = 0

try:
    # 设置超时
    timer = threading.Timer(TIMEOUT, timeout_handler)
    timer.start()
    
    # 预热运行
    print("预热运行...")
    detect_pierced_faces_python(faces[:100], vertices)
    
    # 实际测试
    print("开始实际测试...")
    py_start = time.time()
    py_results, py_time = detect_pierced_faces_python(faces, vertices)
    py_end = time.time()
    py_total_time = py_end - py_start
    
    # 取消超时
    timer.cancel()
    
    print(f"Python检测完成: 检测到 {len(py_results)} 个穿刺面")
    print(f"Python算法用时: {py_time:.4f}秒 (总耗时: {py_total_time:.4f}秒)")
except KeyboardInterrupt:
    print("Python版本检测超时，跳过Python版本测试")
except Exception as e:
    print(f"Python版本检测出错: {str(e)}")

# 运行C++版本的穿刺面检测
print("\n运行C++版本的穿刺面检测...")
cpp_results = []
cpp_time = 0
cpp_total_time = 0

try:
    # 设置超时
    timer = threading.Timer(TIMEOUT, timeout_handler)
    timer.start()
    
    # 预热运行
    print("预热运行...")
    pierced_faces_cpp.detect_pierced_faces_with_timing(faces[:100], vertices)
    
    # 实际测试
    print("开始实际测试...")
    cpp_start = time.time()
    cpp_results, cpp_time = pierced_faces_cpp.detect_pierced_faces_with_timing(faces, vertices)
    cpp_end = time.time()
    cpp_total_time = cpp_end - cpp_start
    
    # 取消超时
    timer.cancel()
    
    print(f"C++检测完成: 检测到 {len(cpp_results)} 个穿刺面")
    print(f"C++算法用时: {cpp_time:.4f}秒 (总耗时: {cpp_total_time:.4f}秒)")
except KeyboardInterrupt:
    print("C++版本检测超时，跳过C++版本测试")
except Exception as e:
    print(f"C++版本检测出错: {str(e)}")

# 计算加速比
if cpp_time > 0 and py_time > 0:
    speedup = py_time / cpp_time
    print(f"\nC++算法加速比: {speedup:.2f}倍")

# 检查结果一致性
if py_results and cpp_results:
    py_set = set(py_results)
    cpp_set = set(cpp_results)
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

# 生成比较图表
# 创建输出目录（如果不存在）
output_dir = os.path.join(current_dir, 'output')
os.makedirs(output_dir, exist_ok=True)

plt.figure(figsize=(12, 6))
plt.subplot(1, 2, 1)
bars = plt.bar(['Python', 'C++'], [py_time, cpp_time])
plt.ylabel('执行时间（秒）')
if args.sample > 0:
    plt.title(f'穿刺面检测算法性能比较 (采样{len(faces)}面)')
else:
    plt.title(f'穿刺面检测算法性能比较 (全部{len(faces)}面)')
# 为柱状图添加标签
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 0.01,
            f'{height:.4f}s',
            ha='center', va='bottom')

plt.subplot(1, 2, 2)
if py_time > 0 and cpp_time > 0:
    speedup = py_time / cpp_time
    plt.bar(['加速比'], [speedup])
    plt.text(0, speedup + 0.5, f'{speedup:.2f}x', ha='center')
    if args.sample > 0:
        plt.title(f'C++相对Python加速比 (采样{len(faces)}面)')
    else:
        plt.title(f'C++相对Python加速比 (全部{len(faces)}面)')
else:
    plt.text(0.5, 0.5, '无法计算加速比\n(一个或多个算法未执行)', ha='center', va='center')
    plt.title('加速比')

plt.tight_layout()

# 保存图表
model_name = os.path.splitext(os.path.basename(nas_file))[0]
output_file = os.path.join(output_dir, f'performance_comparison_{model_name}.png')
plt.savefig(output_file)
print(f"\n性能比较图表已保存到: {output_file}")

# 关闭图表而不显示
plt.close()
# plt.show()  # 注释掉这行，不显示图表 