import numpy as np
import time
import os

print("正在导入C++模块...")
try:
    import self_intersection_cpp
    print("成功导入C++模块")
except ImportError as e:
    print(f"导入失败: {e}")
    exit(1)

def generate_test_mesh(size=10):
    """生成测试网格"""
    print("开始生成网格...")
    # 生成一个简单的平面网格
    vertices = []
    faces = []
    
    # 创建顶点 - 基础平面
    for i in range(size+1):
        for j in range(size+1):
            x = i * 1.0
            y = j * 1.0
            z = 0.0
            vertices.append([x, y, z])
    
    # 创建面片 - 基础平面
    for i in range(size):
        for j in range(size):
            v1 = i * (size+1) + j
            v2 = i * (size+1) + (j+1)
            v3 = (i+1) * (size+1) + j
            v4 = (i+1) * (size+1) + (j+1)
            
            # 每个网格单元划分为两个三角形
            faces.append([v1, v2, v3])
            faces.append([v2, v4, v3])
    
    # 添加一个非常接近的第二个平面
    vertex_offset = len(vertices)
    for i in range(size+1):
        for j in range(size+1):
            x = i * 1.0
            y = j * 1.0
            z = 0.05  # 很接近的距离
            vertices.append([x, y, z])
    
    # 为第二个平面创建面片
    for i in range(size):
        for j in range(size):
            v1 = vertex_offset + i * (size+1) + j
            v2 = vertex_offset + i * (size+1) + (j+1)
            v3 = vertex_offset + (i+1) * (size+1) + j
            v4 = vertex_offset + (i+1) * (size+1) + (j+1)
            
            # 每个网格单元划分为两个三角形
            faces.append([v1, v2, v3])
            faces.append([v2, v4, v3])
    
    print(f"网格生成完成: {len(vertices)}个顶点, {len(faces)}个面片")
    return np.array(vertices, dtype=np.float32), np.array(faces, dtype=np.int32)

def run_test():
    """运行相邻面检测测试"""
    print("生成测试网格...")
    vertices, faces = generate_test_mesh(size=20)
    
    print(f"测试网格：{len(vertices)}个顶点，{len(faces)}个面片")
    print(f"顶点数组形状: {vertices.shape}")
    print(f"面片数组形状: {faces.shape}")
    
    # 运行C++版本
    print("\n运行C++版本...")
    try:
        start_time = time.time()
        result, cpp_time = self_intersection_cpp.detect_self_intersections_with_timing(
            vertices, faces, proximity_threshold=0.1
        )
        end_time = time.time()
        
        print(f"C++版本检测到{len(result)}个相邻面")
        print(f"C++内部计时: {cpp_time:.4f}秒")
        print(f"总运行时间: {end_time - start_time:.4f}秒")
    except Exception as e:
        print(f"C++版本出错: {e}")

if __name__ == "__main__":
    print("开始测试...")
    run_test()
    print("测试完成") 