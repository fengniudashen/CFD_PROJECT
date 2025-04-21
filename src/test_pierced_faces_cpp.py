import numpy as np
import pierced_faces_cpp
from create_football_mesh import create_football_mesh

def create_test_mesh_with_intersections():
    """创建一个具有穿刺面的测试网格"""
    # 创建一个简单的网格，包含两个相交的三角形
    vertices = np.array([
        [0, 0, 0],    # 0
        [1, 0, 0],    # 1
        [0, 1, 0],    # 2
        [0, 0, 1],    # 3
        [1, 1, 1],    # 4
        [0.2, 0.2, -0.5],  # 5
    ], dtype=np.float64)
    
    # 两个相交的三角形
    faces = np.array([
        [0, 1, 2],  # 底部三角形
        [3, 4, 5],  # 穿过底部三角形的三角形
    ], dtype=np.int32)
    
    return vertices, faces

def test_pierced_faces_cpp():
    print("测试穿刺面检测CPP模块...")
    
    # 测试1：使用足球网格（预期没有穿刺面）
    vertices1, faces1, _ = create_football_mesh(radius=100.0, subdivisions=2)
    
    print("\n测试1：使用足球网格")
    print(f"网格信息:")
    print(f"- 顶点数量: {len(vertices1)}")
    print(f"- 面片数量: {len(faces1)}")
    
    # 确保数据类型正确
    vertices1 = np.array(vertices1, dtype=np.float64)
    faces1 = np.array(faces1, dtype=np.int32)
    
    # 尝试调用C++模块
    try:
        print("调用新版C++模块(返回相交映射)...")
        intersecting_faces1, intersection_map1, detection_time1 = pierced_faces_cpp.detect_pierced_faces_with_timing(
            faces1, vertices1)
        
        print(f"检测用时: {detection_time1:.4f}秒")
        print(f"检测到{len(intersecting_faces1)}个穿刺面")
        
        # 验证相交映射
        if intersection_map1:
            total_relations1 = sum(len(relations) for relations in intersection_map1.values()) // 2
            print(f"相交关系总数: {total_relations1}")
        else:
            print("未检测到相交关系")
        
    except ValueError as e:
        print(f"错误: {e}")
    
    # 测试2：使用具有相交面的网格
    print("\n测试2：使用具有相交面的网格")
    vertices2, faces2 = create_test_mesh_with_intersections()
    
    print(f"网格信息:")
    print(f"- 顶点数量: {len(vertices2)}")
    print(f"- 面片数量: {len(faces2)}")
    
    try:
        intersecting_faces2, intersection_map2, detection_time2 = pierced_faces_cpp.detect_pierced_faces_with_timing(
            faces2, vertices2)
        
        print(f"检测用时: {detection_time2:.4f}秒")
        print(f"检测到{len(intersecting_faces2)}个穿刺面")
        
        # 验证相交映射
        if intersection_map2:
            total_relations2 = sum(len(relations) for relations in intersection_map2.values()) // 2
            print(f"相交关系总数: {total_relations2}")
            
            # 显示所有相交关系
            for face_idx, relations in intersection_map2.items():
                print(f"面片 #{face_idx} 与 {len(relations)} 个其他面片相交:")
                print(f"  相交面: {relations}")
        else:
            print("未检测到相交关系")
        
        return True
    except Exception as e:
        print(f"错误: {e}")
        return False

if __name__ == "__main__":
    test_pierced_faces_cpp() 