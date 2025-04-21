import numpy as np
import self_intersection_cpp

def test_adjacent_faces():
    # 创建一个简单的网格（一个平面）
    vertices = np.array([
        [0, 0, 0],  # 顶点0
        [1, 0, 0],  # 顶点1
        [1, 1, 0],  # 顶点2
        [0, 1, 0],  # 顶点3
    ], dtype=np.float32)
    
    # 创建两个三角形面片
    faces = np.array([
        [0, 1, 2],  # 面片0
        [0, 2, 3]   # 面片1
    ], dtype=np.int32)
    
    # 调用C++扩展模块检测相邻面片
    adjacent_faces, execution_time = self_intersection_cpp.detect_self_intersections_with_timing(
        vertices, faces, proximity_threshold=0.1
    )
    
    print(f"检测到 {len(adjacent_faces)} 个相邻面片")
    print(f"执行时间: {execution_time:.6f} 秒")
    print(f"相邻面片索引: {adjacent_faces}")
    
    # 创建另一个测试网格，包含可能的相邻面
    vertices2 = np.array([
        [0, 0, 0],    # 顶点0
        [1, 0, 0],    # 顶点1
        [1, 1, 0],    # 顶点2
        [0, 1, 0],    # 顶点3
        [0.5, 0.5, 0.05]  # 顶点4 - 略微高于平面
    ], dtype=np.float32)
    
    faces2 = np.array([
        [0, 1, 2],  # 面片0
        [0, 2, 3],  # 面片1
        [0, 1, 4],  # 面片2 - 与面片0相邻
        [2, 3, 4]   # 面片3 - 与面片1相邻
    ], dtype=np.int32)
    
    # 检测相邻面片
    adjacent_faces2, execution_time2 = self_intersection_cpp.detect_self_intersections_with_timing(
        vertices2, faces2, proximity_threshold=0.1
    )
    
    print("\n第二个测试:")
    print(f"检测到 {len(adjacent_faces2)} 个相邻面片")
    print(f"执行时间: {execution_time2:.6f} 秒")
    print(f"相邻面片索引: {adjacent_faces2}")

if __name__ == "__main__":
    test_adjacent_faces() 