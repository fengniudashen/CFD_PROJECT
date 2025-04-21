"""
测试面片质量分析模块的性能和准确性
比较C++和Python实现的差异
"""

import numpy as np
import time
import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入算法
from algorithms.face_quality_algorithm import FaceQualityAlgorithm

# 尝试导入C++模块
try:
    import face_quality_cpp
    HAS_CPP_MODULE = True
    print("已加载面片质量分析C++模块")
except ImportError:
    HAS_CPP_MODULE = False
    print("未找到面片质量分析C++模块，仅测试Python实现")

def load_mesh(filename):
    """加载测试用的网格文件"""
    if not os.path.exists(filename):
        # 如果文件不存在，创建一个简单的网格
        print(f"未找到文件 {filename}，创建简单网格...")
        vertices = np.array([
            [0.0, 0.0, 0.0],  # 0
            [1.0, 0.0, 0.0],  # 1
            [0.0, 1.0, 0.0],  # 2
            [1.0, 1.0, 0.0],  # 3
            [0.0, 0.0, 1.0],  # 4
            [1.0, 0.0, 1.0],  # 5
            [0.0, 1.0, 1.0],  # 6
            [1.0, 1.0, 1.0],  # 7
        ], dtype=np.float32)
        
        faces = np.array([
            [0, 1, 2],  # 底面1
            [1, 3, 2],  # 底面2
            [4, 6, 5],  # 顶面1
            [5, 6, 7],  # 顶面2
            [0, 4, 1],  # 侧面1
            [1, 4, 5],  # 侧面2
            [1, 5, 3],  # 侧面3
            [3, 5, 7],  # 侧面4
            [3, 7, 2],  # 侧面5
            [2, 7, 6],  # 侧面6
            [2, 6, 0],  # 侧面7
            [0, 6, 4],  # 侧面8
        ], dtype=np.int32)
        
        return {'vertices': vertices, 'faces': faces}
    
    # 这里假设有一个简单的格式，实际上可能需要根据文件格式调整
    # 这只是一个示例
    print(f"加载网格文件: {filename}")
    vertices = []
    faces = []
    
    with open(filename, 'r') as f:
        lines = f.readlines()
        
        for i, line in enumerate(lines):
            if line.startswith('v '):
                parts = line.split()
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif line.startswith('f '):
                parts = line.split()
                # OBJ格式索引从1开始，需要减1
                faces.append([int(parts[1].split('/')[0]) - 1, 
                            int(parts[2].split('/')[0]) - 1, 
                            int(parts[3].split('/')[0]) - 1])
    
    return {'vertices': np.array(vertices, dtype=np.float32), 
            'faces': np.array(faces, dtype=np.int32)}

def test_python_implementation(mesh_data, threshold=0.3):
    """测试Python实现的面片质量分析"""
    print("\n测试Python实现:")
    start_time = time.time()
    
    # 创建算法实例
    algorithm = FaceQualityAlgorithm(mesh_data, threshold)
    algorithm.use_cpp = False  # 强制使用Python实现
    
    # 确保正确设置顶点和面片数据
    if not algorithm.set_mesh_data(mesh_data):
        print("设置网格数据失败！")
        return {'selected_faces': [], 'stats': {}}
    
    # 手动调用analyze_face_quality方法
    algorithm.analyze_face_quality()
    result = algorithm.result
    result['stats'] = algorithm.stats
    
    # 计算执行时间
    end_time = time.time()
    elapsed = end_time - start_time
    result['stats']['execution_time'] = elapsed
    
    print(f"Python实现用时: {elapsed:.4f}秒")
    print(f"检测到 {len(result['selected_faces'])} 个低质量面片 (阈值 < {threshold})")
    return result

def test_cpp_implementation(mesh_data, threshold=0.3):
    """测试C++实现的面片质量分析"""
    if not HAS_CPP_MODULE:
        print("\nC++模块未加载，跳过C++测试")
        return None
    
    print("\n测试C++实现:")
    start_time = time.time()
    
    vertices = mesh_data['vertices']
    faces = mesh_data['faces']
    
    low_quality_faces, stats, cpp_time = face_quality_cpp.analyze_face_quality_with_timing(
        vertices, faces, threshold)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"C++实现用时: {cpp_time:.4f}秒 (总用时: {elapsed:.4f}秒)")
    print(f"检测到 {len(low_quality_faces)} 个低质量面片 (阈值 < {threshold})")
    
    result = {
        'selected_faces': low_quality_faces,
        'stats': stats
    }
    return result

def compare_results(python_result, cpp_result):
    """比较Python和C++实现的结果"""
    if cpp_result is None:
        print("\n无法比较结果：C++模块未加载")
        return
    
    print("\n比较结果:")
    
    python_selected = set(python_result['selected_faces'])
    cpp_selected = set(cpp_result['selected_faces'])
    
    if python_selected == cpp_selected:
        print("结果完全一致！")
    else:
        common = python_selected.intersection(cpp_selected)
        only_in_python = python_selected - cpp_selected
        only_in_cpp = cpp_selected - python_selected
        
        print(f"共同选择的面片: {len(common)}")
        print(f"仅在Python中选择: {len(only_in_python)}")
        print(f"仅在C++中选择: {len(only_in_cpp)}")
        
        if len(only_in_python) > 0 or len(only_in_cpp) > 0:
            print("注意：结果不完全一致，可能是由于浮点精度差异导致的。")

def create_large_test_mesh(vertices_count=10000, faces_count=20000):
    """创建一个大型测试网格"""
    print(f"创建大型测试网格 (顶点: {vertices_count}, 面片: {faces_count})...")
    
    # 生成随机顶点
    vertices = np.random.rand(vertices_count, 3).astype(np.float32)
    
    # 创建随机面片（确保索引有效）
    faces = np.random.randint(0, vertices_count, (faces_count, 3)).astype(np.int32)
    
    return {'vertices': vertices, 'faces': faces}

def main():
    """主函数"""
    print("面片质量分析模块性能测试")
    print("=" * 40)
    
    # 测试小型网格
    mesh_data = load_mesh("test_mesh.obj")
    print(f"加载的网格: {len(mesh_data['vertices'])} 顶点, {len(mesh_data['faces'])} 面片")
    
    # 运行Python测试
    python_result = test_python_implementation(mesh_data)
    
    # 运行C++测试
    cpp_result = test_cpp_implementation(mesh_data)
    
    # 比较结果
    compare_results(python_result, cpp_result)
    
    # 测试大型网格
    print("\n\n测试大型网格性能")
    print("=" * 40)
    
    large_mesh = create_large_test_mesh()
    print(f"大型网格: {len(large_mesh['vertices'])} 顶点, {len(large_mesh['faces'])} 面片")
    
    # 运行Python测试
    python_result_large = test_python_implementation(large_mesh)
    
    # 运行C++测试
    cpp_result_large = test_cpp_implementation(large_mesh)
    
    # 比较结果
    compare_results(python_result_large, cpp_result_large)
    
    if HAS_CPP_MODULE:
        print("\n性能加速总结:")
        
        # 小型网格性能比较
        python_time = python_result['stats'].get('execution_time', 0)
        cpp_time = cpp_result['stats'].get('execution_time', 0)
        if python_time > 0 and cpp_time > 0:
            speedup = python_time / cpp_time
            print(f"小型网格加速比: {speedup:.2f}x")
        
        # 大型网格性能比较
        python_time_large = python_result_large['stats'].get('execution_time', 0)
        cpp_time_large = cpp_result_large['stats'].get('execution_time', 0)
        if python_time_large > 0 and cpp_time_large > 0:
            speedup_large = python_time_large / cpp_time_large
            print(f"大型网格加速比: {speedup_large:.2f}x")

if __name__ == "__main__":
    main() 