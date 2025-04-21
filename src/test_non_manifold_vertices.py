import numpy as np
import sys
import os
import time

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.non_manifold_vertices_algorithm import NonManifoldVerticesAlgorithm
import non_manifold_vertices_cpp

def create_test_mesh():
    """创建一个包含非流形顶点的测试网格"""
    # 创建一个简单的立方体网格，并添加一些非流形情况
    vertices = np.array([
        [0, 0, 0],  # 0
        [1, 0, 0],  # 1
        [1, 1, 0],  # 2
        [0, 1, 0],  # 3
        [0, 0, 1],  # 4
        [1, 0, 1],  # 5
        [1, 1, 1],  # 6
        [0, 1, 1],  # 7
        [0.5, 0.5, 0.5],  # 8 - 非流形顶点
    ], dtype=np.float64)

    # 创建面片，包括一些共享顶点8的不连通面片
    faces = np.array([
        [0, 1, 2], [0, 2, 3],  # 底面
        [4, 5, 6], [4, 6, 7],  # 顶面
        [0, 4, 8], [1, 5, 8],  # 使用顶点8的面片组1
        [2, 6, 8], [3, 7, 8],  # 使用顶点8的面片组2
    ], dtype=np.int32)

    return vertices, faces

def create_simple_test_mesh():
    """创建一个简单的测试网格，用于调试"""
    vertices = np.array([
        [0, 0, 0],  # 0
        [1, 0, 0],  # 1
        [1, 1, 0],  # 2
        [0, 1, 0],  # 3
        [0.5, 0.5, 1],  # 4 - 非流形顶点
    ], dtype=np.float64)

    faces = np.array([
        [0, 1, 2], [0, 2, 3],  # 底面
        [0, 1, 4], [1, 2, 4],  # 使用顶点4的面片组1
        [2, 3, 4], [3, 0, 4],  # 使用顶点4的面片组2
    ], dtype=np.int32)

    return vertices, faces

def create_large_test_mesh(size=1000):
    """创建一个更大的测试网格"""
    # 创建一个网格，包含多个非流形顶点
    vertices = []
    faces = []
    
    # 创建一个网格平面
    n = int(np.sqrt(size))
    for i in range(n):
        for j in range(n):
            vertices.append([i, j, 0])
            if i > 0 and j > 0:
                # 添加两个三角形
                idx = i * n + j
                faces.append([idx, idx-1, idx-n])
                faces.append([idx-1, idx-n-1, idx-n])
                
                # 每隔一定距离添加一个非流形结构
                if i % 10 == 0 and j % 10 == 0:
                    # 添加一个向上的三角形
                    vertices.append([i, j, 1])
                    new_vertex_idx = len(vertices) - 1
                    faces.append([idx, idx-1, new_vertex_idx])
                    faces.append([idx, new_vertex_idx, idx-n])

    return np.array(vertices, dtype=np.float64), np.array(faces, dtype=np.int32)

def test_cpp_implementation(vertices, faces, tolerance=1e-6):
    """测试C++实现"""
    start_time = time.time()
    result = non_manifold_vertices_cpp.detect_non_manifold_vertices_with_timing(
        vertices, faces, tolerance
    )
    total_time = time.time() - start_time
    return result[0], result[1], total_time

def test_python_implementation(vertices, faces):
    """测试Python实现"""
    mesh_data = MeshData(vertices, faces)
    algorithm = NonManifoldVerticesAlgorithm(mesh_data)
    algorithm.progress = SimpleProgress()
    
    start_time = time.time()
    non_manifold_vertices = algorithm.detect_non_manifold_vertices_python()
    python_time = time.time() - start_time
    
    return non_manifold_vertices, python_time

class MeshData:
    """简单的网格数据类"""
    def __init__(self, vertices, faces):
        self.vertices = vertices
        self.faces = faces
        self.non_manifold_vertices = None
        self.execution_time = 0
        self.cpp_time = 0
        self.python_time = 0

class SimpleProgress:
    """简单的进度回调"""
    def emit(self, value):
        pass

def analyze_vertex(mesh_data, vertex_idx):
    """分析特定顶点的邻接关系"""
    print(f"\n分析顶点 {vertex_idx}:")
    
    # 获取与该顶点相连的面片
    vertex_adjacent_faces = {}
    for face_idx, face in enumerate(mesh_data.faces):
        if vertex_idx in face:
            if vertex_idx not in vertex_adjacent_faces:
                vertex_adjacent_faces[vertex_idx] = []
            vertex_adjacent_faces[vertex_idx].append(face_idx)
    
    print(f"相连的面片: {vertex_adjacent_faces[vertex_idx]}")
    
    # 分析面片的连通性
    algorithm = NonManifoldVerticesAlgorithm(mesh_data)
    sectors = algorithm.find_vertex_sectors(vertex_idx, vertex_adjacent_faces[vertex_idx])
    print(f"面片扇区数量: {len(sectors)}")
    print(f"面片扇区: {sectors}")
    
    # 分析边的连通性
    edges = set()
    for face_idx in vertex_adjacent_faces[vertex_idx]:
        face = mesh_data.faces[face_idx]
        # 找到与vertex_idx相连的边
        for i in range(3):
            if face[i] == vertex_idx:
                v1 = face[(i+1)%3]
                v2 = face[(i+2)%3]
                edges.add((min(v1, v2), max(v1, v2)))
    
    print(f"相连的边: {edges}")
    return len(sectors) > 1

def test_and_compare():
    """测试并比较Python和C++实现的性能"""
    try:
        print("测试简单网格...")
        vertices, faces = create_simple_test_mesh()
        mesh_data = MeshData(vertices, faces)
        
        # 分析每个顶点
        for vertex_idx in range(len(vertices)):
            is_non_manifold = analyze_vertex(mesh_data, vertex_idx)
            print(f"顶点 {vertex_idx} 是否为非流形: {is_non_manifold}")
        
        # 测试Python实现
        py_vertices, py_time = test_python_implementation(vertices, faces)
        
        # 测试C++实现
        cpp_vertices, cpp_internal_time, cpp_total_time = test_cpp_implementation(vertices, faces)
        
        print(f"\n简单网格结果:")
        print(f"网格大小: {len(vertices)}顶点, {len(faces)}面片")
        print(f"Python检测到的非流形顶点: {sorted(py_vertices)}")
        print(f"C++检测到的非流形顶点: {sorted(cpp_vertices)}")
        print(f"Python执行时间: {py_time:.6f}秒")
        print(f"C++内部执行时间: {cpp_internal_time:.6f}秒")
        print(f"C++总执行时间: {cpp_total_time:.6f}秒")
        if cpp_internal_time > 0:
            print(f"加速比(基于内部时间): {py_time/cpp_internal_time:.2f}x")
        print("\n")

        print("测试小型网格...")
        vertices, faces = create_test_mesh()
        mesh_data = MeshData(vertices, faces)
        
        # 分析每个顶点
        for vertex_idx in range(len(vertices)):
            is_non_manifold = analyze_vertex(mesh_data, vertex_idx)
            print(f"顶点 {vertex_idx} 是否为非流形: {is_non_manifold}")
        
        # 测试Python实现
        py_vertices, py_time = test_python_implementation(vertices, faces)
        
        # 测试C++实现
        cpp_vertices, cpp_internal_time, cpp_total_time = test_cpp_implementation(vertices, faces)
        
        print(f"\n小型网格结果:")
        print(f"网格大小: {len(vertices)}顶点, {len(faces)}面片")
        print(f"Python检测到的非流形顶点: {sorted(py_vertices)}")
        print(f"C++检测到的非流形顶点: {sorted(cpp_vertices)}")
        print(f"Python执行时间: {py_time:.6f}秒")
        print(f"C++内部执行时间: {cpp_internal_time:.6f}秒")
        print(f"C++总执行时间: {cpp_total_time:.6f}秒")
        if cpp_internal_time > 0:
            print(f"加速比(基于内部时间): {py_time/cpp_internal_time:.2f}x")
        print("\n")

        print("测试大型网格...")
        vertices, faces = create_large_test_mesh(size=10000)  # 使用更大的网格
        
        # 测试Python实现
        py_vertices, py_time = test_python_implementation(vertices, faces)
        
        # 测试C++实现
        cpp_vertices, cpp_internal_time, cpp_total_time = test_cpp_implementation(vertices, faces)
        
        print(f"\n大型网格结果:")
        print(f"网格大小: {len(vertices)}顶点, {len(faces)}面片")
        print(f"Python检测到的非流形顶点数量: {len(py_vertices)}")
        print(f"C++检测到的非流形顶点数量: {len(cpp_vertices)}")
        print(f"结果是否一致: {sorted(py_vertices) == sorted(cpp_vertices)}")
        print(f"Python执行时间: {py_time:.6f}秒")
        print(f"C++内部执行时间: {cpp_internal_time:.6f}秒")
        print(f"C++总执行时间: {cpp_total_time:.6f}秒")
        if cpp_internal_time > 0:
            print(f"加速比(基于内部时间): {py_time/cpp_internal_time:.2f}x")

    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_and_compare() 