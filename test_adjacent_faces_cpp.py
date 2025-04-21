import numpy as np
import time

print("正在导入C++模块...")
try:
    import adjacent_faces_cpp
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

def test_adjacent_faces():
    """测试相邻面检测"""
    # 使用简单的平面网格
    vertices = np.array([
        [0, 0, 0],  # 顶点0
        [1, 0, 0],  # 顶点1
        [1, 1, 0],  # 顶点2
        [0, 1, 0],  # 顶点3
        [0.5, 0.5, 0.05]  # 顶点4 - 略微高于平面
    ], dtype=np.float32)
    
    faces = np.array([
        [0, 1, 2],  # 面片0
        [0, 2, 3],  # 面片1
        [0, 1, 4],  # 面片2 - 与面片0相邻
        [2, 3, 4]   # 面片3 - 与面片1相邻
    ], dtype=np.int32)
    
    print("开始检测相邻面...")
    try:
        # 默认阈值0.5
        print("使用默认阈值0.5:")
        adjacent_faces, execution_time = adjacent_faces_cpp.detect_adjacent_faces_with_timing(
            vertices, faces
        )
        print(f"检测到{len(adjacent_faces)}个相邻面")
        print(f"执行时间: {execution_time:.6f}秒")
        print(f"相邻面对: {adjacent_faces}")
        
        # 使用较小的阈值0.1
        print("\n使用较小阈值0.1:")
        adjacent_faces, execution_time = adjacent_faces_cpp.detect_adjacent_faces_with_timing(
            vertices, faces, proximity_threshold=0.1
        )
        print(f"检测到{len(adjacent_faces)}个相邻面")
        print(f"执行时间: {execution_time:.6f}秒")
        print(f"相邻面对: {adjacent_faces}")
        
        # 使用更大的阈值1.0
        print("\n使用较大阈值1.0:")
        adjacent_faces, execution_time = adjacent_faces_cpp.detect_adjacent_faces_with_timing(
            vertices, faces, proximity_threshold=1.0
        )
        print(f"检测到{len(adjacent_faces)}个相邻面")
        print(f"执行时间: {execution_time:.6f}秒")
        print(f"相邻面对: {adjacent_faces}")
        
    except Exception as e:
        print(f"检测过程出错: {str(e)}")

def run_performance_test():
    """运行性能测试"""
    print("\n开始性能测试...")
    vertices, faces = generate_test_mesh(size=20)
    
    print(f"测试网格：{len(vertices)}个顶点，{len(faces)}个面片")
    print(f"顶点数组形状: {vertices.shape}")
    print(f"面片数组形状: {faces.shape}")
    
    thresholds = [0.1, 0.5, 1.0]
    for threshold in thresholds:
        print(f"\n使用阈值 {threshold}:")
        try:
            start_time = time.time()
            result, cpp_time = adjacent_faces_cpp.detect_adjacent_faces_with_timing(
                vertices, faces, proximity_threshold=threshold
            )
            end_time = time.time()
            
            print(f"检测到{len(result)}个相邻面")
            print(f"C++内部计时: {cpp_time:.4f}秒")
            print(f"总运行时间: {end_time - start_time:.4f}秒")
        except Exception as e:
            print(f"C++版本出错: {e}")

if __name__ == "__main__":
    print("开始测试相邻面检测C++模块...")
    test_adjacent_faces()
    run_performance_test()
    print("测试完成") 