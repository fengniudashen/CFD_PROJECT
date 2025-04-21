import numpy as np
import sys
import os
sys.path.append('src')  # 添加src目录到Python路径
from create_football_mesh import create_football_mesh
import adjacent_faces_cpp
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# 生成足球网格
print("正在生成足球网格...")
vertices, faces, normals = create_football_mesh(radius=100.0, subdivisions=3)

# 打印网格信息
print(f"足球网格信息：")
print(f"- 顶点数量：{len(vertices)}")
print(f"- 面片数量：{len(faces)}")

# 计算每个面片的质心和平均边长
def calculate_centroid(face_vertices):
    return np.mean(face_vertices, axis=0)

def calculate_avg_edge_length(face_vertices):
    v0, v1, v2 = face_vertices
    e1 = np.linalg.norm(v1 - v0)
    e2 = np.linalg.norm(v2 - v1)
    e3 = np.linalg.norm(v0 - v2)
    return (e1 + e2 + e3) / 3.0

centroids = []
avg_edge_lengths = []

for face in faces:
    v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
    face_vertices = np.array([v0, v1, v2])
    centroids.append(calculate_centroid(face_vertices))
    avg_edge_lengths.append(calculate_avg_edge_length(face_vertices))

centroids = np.array(centroids)
avg_edge_lengths = np.array(avg_edge_lengths)

# 统计平均边长分布
print(f"\n边长统计:")
print(f"最小平均边长: {np.min(avg_edge_lengths):.4f}")
print(f"最大平均边长: {np.max(avg_edge_lengths):.4f}")
print(f"平均边长的平均值: {np.mean(avg_edge_lengths):.4f}")
print(f"平均边长的标准差: {np.std(avg_edge_lengths):.4f}")

# 调用C++模块检测相邻面
print("\n使用C++模块进行相邻面检测...")
thresholds = [0.1, 0.5, 1.0]
for threshold in thresholds:
    try:
        adjacent_pairs, execution_time = adjacent_faces_cpp.detect_adjacent_faces_with_timing(
            vertices, faces, proximity_threshold=threshold
        )
        
        # 统计相邻面数量
        face_set = set()
        for i, j in adjacent_pairs:
            face_set.add(i)
            face_set.add(j)
        
        print(f"\n使用阈值 {threshold}:")
        print(f"检测到{len(adjacent_pairs)}对相邻面片，涉及{len(face_set)}个面片")
        print(f"占总面片数的 {len(face_set)/len(faces)*100:.2f}%")
        print(f"执行时间: {execution_time:.4f}秒")
        
        # 如果是阈值0.1，分析几对相邻面片的情况
        if threshold == 0.1 and len(adjacent_pairs) > 0:
            print("\n分析几对在阈值0.1下被判定为相邻的面片:")
            
            # 随机选择5对相邻面片进行分析（如果有那么多）
            sample_count = min(5, len(adjacent_pairs))
            for idx in range(sample_count):
                i, j = adjacent_pairs[idx]
                
                # 计算两个面片的相邻性指标
                centroid_distance = np.linalg.norm(centroids[i] - centroids[j])
                min_avg_edge = min(avg_edge_lengths[i], avg_edge_lengths[j])
                proximity = centroid_distance / min_avg_edge
                
                print(f"\n相邻对 {idx+1}: 面片 {i} 和 面片 {j}")
                print(f"面片 {i} 平均边长: {avg_edge_lengths[i]:.4f}")
                print(f"面片 {j} 平均边长: {avg_edge_lengths[j]:.4f}")
                print(f"质心距离: {centroid_distance:.4f}")
                print(f"Proximity = {proximity:.4f} (应小于等于阈值 {threshold})")
                
                # 检查两个面片是否有共享边（即是否本身就相邻）
                face_i = faces[i]
                face_j = faces[j]
                shared_vertices = set(face_i).intersection(set(face_j))
                if len(shared_vertices) >= 2:
                    print(f"这两个面片共享一条边，实际上是拓扑相邻")
                elif len(shared_vertices) == 1:
                    print(f"这两个面片共享一个顶点")
                else:
                    print(f"这两个面片没有共享任何顶点")
                
    except Exception as e:
        print(f"检测失败: {e}")

# 可视化几对相邻面
if 'adjacent_pairs' in locals() and len(adjacent_pairs) > 0:
    print("\n可视化第一对相邻面片...")
    i, j = adjacent_pairs[0]
    
    # 获取两个三角形的顶点
    triangle1 = vertices[faces[i]]
    triangle2 = vertices[faces[j]]
    
    # 计算质心
    centroid1 = np.mean(triangle1, axis=0)
    centroid2 = np.mean(triangle2, axis=0)
    
    # 创建3D图
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # 绘制第一个三角形
    ax.plot_trisurf(triangle1[:,0], triangle1[:,1], triangle1[:,2], 
                   color='red', alpha=0.6)
    
    # 绘制第二个三角形
    ax.plot_trisurf(triangle2[:,0], triangle2[:,1], triangle2[:,2], 
                   color='blue', alpha=0.6)
    
    # 绘制两个质心并连线
    ax.scatter(centroid1[0], centroid1[1], centroid1[2], color='darkred', s=100)
    ax.scatter(centroid2[0], centroid2[1], centroid2[2], color='darkblue', s=100)
    ax.plot([centroid1[0], centroid2[0]], 
            [centroid1[1], centroid2[1]], 
            [centroid1[2], centroid2[2]], 'k--', linewidth=2)
    
    # 添加标注
    ax.text(centroid1[0], centroid1[1], centroid1[2], f"面片 {i}", color='black', fontsize=12)
    ax.text(centroid2[0], centroid2[1], centroid2[2], f"面片 {j}", color='black', fontsize=12)
    
    # 设置标题和坐标轴
    ax.set_title(f"相邻面片示例 (阈值={threshold})")
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    
    # 调整视角以便观察
    ax.view_init(elev=30, azim=45)
    
    plt.savefig('adjacent_faces_example.png')
    print("已保存可视化图片到 adjacent_faces_example.png")
    
print("\n分析完成") 