#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
面片质量分析模块

该模块提供了基于STAR-CCM+方法的三角形面片质量分析算法，包括：
- 等角质量 (Equiangle skewness) 
- 面积周长比质量 (Area-perimeter ratio)
- 雅可比质量 (Cell Jacobian quality)

功能函数：
- analyze_face_quality: 分析三角形网格的面片质量
- generate_quality_report: 生成质量分析报告
"""

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk
import time


def analyze_face_quality(vertices, faces, threshold=0.5, progress_callback=None):
    """
    分析三角形网格的面片质量
    
    参数:
        vertices (numpy.ndarray): 顶点坐标数组，形状为(n_vertices, 3)
        faces (numpy.ndarray): 面片索引数组，形状为(n_faces, 3)
        threshold (float): 质量阈值，低于此值的面片将被标记为低质量
        progress_callback (callable): 进度回调函数，接收参数(percentage, message)
        
    返回:
        dict: 包含以下键的结果字典:
            - 'quality': 每个面片的质量分数 (0-1)
            - 'low_quality_faces': 低于阈值的面片索引列表
            - 'colors': VTK颜色数组，用于可视化
            - 'stats': 统计信息字典
    """
    start_time = time.time()
    
    # 创建面片质量数组
    n_faces = len(faces)
    face_quality = np.zeros(n_faces)
    
    # 初始化统计数据
    stats = {
        'total_faces': n_faces,
        'low_quality': 0,
        'min_quality': 1.0,
        'max_quality': 0.0,
        'avg_quality': 0.0,
        'threshold': threshold
    }
    
    # 报告初始进度
    if progress_callback:
        if not progress_callback(0, f"准备分析 {n_faces} 个面片..."):
            return None
    
    # 遍历计算每个面片的质量
    update_interval = max(1, n_faces // 100)  # 更新进度的间隔
    
    for i, face in enumerate(faces):
        # 检查是否取消
        if progress_callback and i % update_interval == 0:
            progress_percent = int(i / n_faces * 100)
            if not progress_callback(progress_percent, f"分析面片 {i}/{n_faces}..."):
                return None
        
        # 获取面片的三个顶点
        v1 = vertices[face[0]]
        v2 = vertices[face[1]]
        v3 = vertices[face[2]]

        # 计算边长
        e1 = np.linalg.norm(v2 - v1)
        e2 = np.linalg.norm(v3 - v2)
        e3 = np.linalg.norm(v1 - v3)

        # 计算边向量
        v12 = v2 - v1
        v23 = v3 - v2
        v31 = v1 - v3

        # 计算面积
        cross_product = np.cross(v12, -v31)
        area = 0.5 * np.linalg.norm(cross_product)

        # 对于接近零的面积，设置质量为0
        if area < 1e-10:
            quality = 0.0
            face_quality[i] = quality
            continue

        # 计算三角形周长
        perimeter = e1 + e2 + e3
        if perimeter < 1e-10:  # 防止除零错误
            quality = 0.0
            face_quality[i] = quality
            continue

        try:
            # 计算等边质量 (STAR-CCM+ Equiangle skewness)
            # 归一化向量
            u12 = v12 / e1 if e1 > 1e-10 else np.zeros(3)
            u23 = v23 / e2 if e2 > 1e-10 else np.zeros(3)
            u31 = v31 / e3 if e3 > 1e-10 else np.zeros(3)
            
            # 计算三个内角 (安全计算点积，避免数值误差)
            cos_angle1 = max(-1.0, min(1.0, np.dot(-u31, u12)))
            cos_angle2 = max(-1.0, min(1.0, np.dot(-u12, u23)))
            cos_angle3 = max(-1.0, min(1.0, np.dot(-u23, u31)))
            
            angle1 = np.arccos(cos_angle1)
            angle2 = np.arccos(cos_angle2)
            angle3 = np.arccos(cos_angle3)
            
            # 验证角度和是否接近π
            angle_sum = angle1 + angle2 + angle3
            if abs(angle_sum - np.pi) > 1e-3:
                # 角度计算有问题，可能是退化三角形
                equiangle_quality = 0.0
            else:
                # 计算角度偏差 (理想角度为60度)
                ideal_angle = np.pi / 3  # 60度
                max_deviation = max(
                    abs(angle1 - ideal_angle), 
                    abs(angle2 - ideal_angle), 
                    abs(angle3 - ideal_angle)
                )
                equiangle_quality = 1.0 - (max_deviation / (np.pi - ideal_angle))
                equiangle_quality = max(0.0, min(1.0, equiangle_quality))
        except:
            equiangle_quality = 0.0

        # 计算纵横比质量 (STAR-CCM+ Aspect Ratio Quality)
        # 使用面积与周长的关系，完美的等边三角形有最佳的面积周长比
        area_perimeter_quality = (4 * np.sqrt(3) * area) / (perimeter * perimeter)
        area_perimeter_quality = max(0.0, min(1.0, area_perimeter_quality))  # 归一化到[0,1]

        # 计算单元雅可比质量 (STAR-CCM+ Cell Jacobian Quality)
        # 对于三角形，使用最小高度与最大边长的比值
        min_height = 2 * area / max(e1, e2, e3)
        jacobian_quality = 0.0
        if max(e1, e2, e3) > 1e-10:
            # 归一化高宽比 (理想值为等边三角形的高宽比)
            ideal_height_ratio = np.sqrt(3) / 2
            jacobian_quality = (min_height / max(e1, e2, e3)) / ideal_height_ratio
            jacobian_quality = max(0.0, min(1.0, jacobian_quality))

        # 综合质量评分 (STAR-CCM+ 综合多个指标)
        # 权重可以根据具体需求调整
        quality = 0.4 * equiangle_quality + 0.4 * area_perimeter_quality + 0.2 * jacobian_quality
        
        # 最后的保护措施
        quality = max(0.0, min(1.0, quality))
        face_quality[i] = quality
    
    # 更新最终进度
    if progress_callback:
        if not progress_callback(99, "生成结果报告..."):
            return None
    
    # 计算统计信息
    stats['min_quality'] = np.min(face_quality)
    stats['max_quality'] = np.max(face_quality)
    stats['avg_quality'] = np.mean(face_quality)
    stats['low_quality'] = np.sum(face_quality < threshold)
    
    # 找出质量低于阈值的面片
    low_quality_faces = np.where(face_quality < threshold)[0].tolist()
    
    # 创建颜色映射 - 只标记低于阈值的面片
    colors = vtk.vtkUnsignedCharArray()
    colors.SetNumberOfComponents(3)
    colors.SetName('Colors')

    # 设置颜色 - 低于阈值的面片标记为红色，其他保持默认
    for q in face_quality:
        if q < threshold:  # 低质量（红色）
            colors.InsertNextTuple3(255, 0, 0)
        else:  # 其他面片（白色/默认色）
            colors.InsertNextTuple3(255, 255, 255)
    
    # 计算总时间
    elapsed_time = time.time() - start_time
    stats['elapsed_time'] = elapsed_time
    
    # 最终进度
    if progress_callback:
        progress_callback(100, f"分析完成，用时 {elapsed_time:.2f} 秒")
    
    # 返回结果
    return {
        'quality': face_quality,
        'low_quality_faces': low_quality_faces,
        'colors': colors,
        'stats': stats
    }


def generate_quality_report(stats):
    """
    生成面片质量分析报告
    
    参数:
        stats (dict): 统计信息字典
        
    返回:
        str: 格式化的质量报告文本
    """
    total_faces = stats['total_faces']
    low_quality = stats['low_quality']
    threshold = stats['threshold']
    
    report = f'面片质量分析结果:\n'
    report += f'低质量面片（红色）: {low_quality} ({low_quality/total_faces*100:.1f}%)\n'
    report += f'\n质量统计:\n'
    report += f'最小质量: {stats["min_quality"]:.4f}\n'
    report += f'最大质量: {stats["max_quality"]:.4f}\n'
    report += f'平均质量: {stats["avg_quality"]:.4f}\n'
    
    if 'elapsed_time' in stats:
        report += f'\n分析用时: {stats["elapsed_time"]:.2f} 秒\n'
    
    report += f'\n已选中 {low_quality} 个质量低于 {threshold} 的面片'
    
    return report


# 测试函数
def test():
    """测试面片质量分析功能"""
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    
    # 创建一些测试三角形
    vertices = np.array([
        [0, 0, 0],        # 0
        [1, 0, 0],        # 1
        [0.5, 0.866, 0],  # 2 - 等边三角形的顶点
        [0.1, 0.1, 0],    # 3 - 用于创建低质量三角形
        [2, 0, 0],        # 4
        [2, 1, 0],        # 5
    ], dtype=np.float32)
    
    faces = np.array([
        [0, 1, 2],       # 接近等边三角形（高质量）
        [0, 1, 3],       # 细长三角形（低质量）
        [1, 4, 5],       # 普通三角形（中等质量）
    ], dtype=np.int32)
    
    def progress(value, message):
        print(f"Progress: {value}% - {message}")
        return True
    
    # 运行分析
    results = analyze_face_quality(vertices, faces, 0.5, progress)
    
    # 打印结果
    print("\n质量分数:")
    for i, quality in enumerate(results['quality']):
        print(f"面片 {i}: {quality:.4f}")
    
    print("\n低质量面片:", results['low_quality_faces'])
    
    # 打印报告
    print("\n" + generate_quality_report(results['stats']))
    
    # 可视化三角形和质量
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # 绘制每个三角形
    for i, face in enumerate(faces):
        triangle = vertices[face]
        quality = results['quality'][i]
        
        # 设置颜色（低于阈值的为红色，其他为灰色）
        if quality < 0.5:  # 使用与analyze_face_quality相同的阈值
            color = 'red'
        else:
            color = 'lightgray'
        
        # 绘制三角形
        ax.plot_trisurf(triangle[:, 0], triangle[:, 1], triangle[:, 2], 
                        color=color, alpha=0.7)
        
        # 计算三角形中心并标记序号
        center = np.mean(triangle, axis=0)
        ax.text(center[0], center[1], center[2], f"{i} ({quality:.2f})", 
                fontsize=12, ha='center')
    
    # 设置坐标轴和标签
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('三角形面片质量分析')
    
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    test() 