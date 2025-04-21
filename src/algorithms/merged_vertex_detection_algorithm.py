"""
重叠点检测算法
整合了overlapping_points_algorithm和non_manifold_vertices_algorithm的功能
用于检测网格中的重叠点/非流形顶点
"""

import numpy as np
import time
from .base_algorithm import BaseAlgorithm
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt
import sys
import os

# 尝试导入C++模块
try:
    import overlapping_points_cpp
    HAS_OVERLAPPING_POINTS_CPP = True
except ImportError:
    HAS_OVERLAPPING_POINTS_CPP = False

try:
    import non_manifold_vertices_cpp
    HAS_NON_MANIFOLD_VERTICES_CPP = True
except ImportError:
    HAS_NON_MANIFOLD_VERTICES_CPP = False

class MergedVertexDetectionAlgorithm(BaseAlgorithm):
    """
    合并的顶点检测算法类
    整合了重叠点检测和非流形顶点检测的功能
    """
    
    def __init__(self, mesh_data=None, tolerance=1e-6, detection_mode="overlapping"):
        """
        初始化顶点检测算法
        
        参数:
        mesh_data (dict): 包含顶点和面片数据的字典
        tolerance (float): 容差值，用于判断点是否重叠的阈值
        detection_mode (str): 检测模式，可选值: "overlapping"或"non_manifold"
        """
        super().__init__(mesh_data)
        self.tolerance = tolerance
        self.detection_mode = detection_mode
        
        # 初始化顶点和面片数据
        if mesh_data is not None:
            self.set_mesh_data(mesh_data)
        
        # 根据检测模式和可用模块决定使用哪个C++实现
        self.use_cpp = False
        if detection_mode == "overlapping" and HAS_OVERLAPPING_POINTS_CPP:
            self.use_cpp = True
            self.cpp_module = "overlapping_points_cpp"
        elif detection_mode == "non_manifold" and HAS_NON_MANIFOLD_VERTICES_CPP:
            self.use_cpp = True
            self.cpp_module = "non_manifold_vertices_cpp"
        elif HAS_NON_MANIFOLD_VERTICES_CPP:
            self.use_cpp = True
            self.cpp_module = "non_manifold_vertices_cpp"
        elif HAS_OVERLAPPING_POINTS_CPP:
            self.use_cpp = True
            self.cpp_module = "overlapping_points_cpp"
        
        # 初始化限制检测的顶点集
        self.target_vertices = None
    
    def execute(self, parent=None):
        """
        执行顶点检测
        
        参数:
        parent: 父窗口，用于显示界面元素
        
        返回:
        dict: 结果字典，包含selected_points或non_manifold_vertices
        """
        try:
            # 检查网格数据
            if not self.set_mesh_data(self.mesh_data):
                self.show_message(parent, "警告", "缺少有效的网格数据", icon="warning")
                return self.result
            
            # 显示进度对话框
            progress = self.show_progress_dialog(parent, "顶点检测", "正在检测重叠点...", 100)
            self.update_progress(10, "初始化检测...")
            
            start_time = time.time()
            detection_title = "重叠点检测" if self.detection_mode == "overlapping" else "非流形顶点检测"
            
            # 尝试使用C++实现
            if self.use_cpp:
                cpp_module_name = self.cpp_module
                self.update_progress(20, f"使用C++算法检测 ({cpp_module_name})...")
                
                if cpp_module_name == "overlapping_points_cpp" and HAS_OVERLAPPING_POINTS_CPP:
                    result, detection_time = overlapping_points_cpp.detect_overlapping_points_with_timing(
                        self.vertices, self.faces)
                    # 存储结果到两个位置以保持兼容性
                    self.result['selected_points'] = list(result)
                    self.mesh_data['non_manifold_vertices'] = list(result)
                    
                elif cpp_module_name == "non_manifold_vertices_cpp" and HAS_NON_MANIFOLD_VERTICES_CPP:
                    result, detection_time = non_manifold_vertices_cpp.detect_non_manifold_vertices_with_timing(
                        self.vertices, self.faces, self.tolerance)
                    # 存储结果到两个位置以保持兼容性
                    self.result['selected_points'] = list(result)
                    self.mesh_data['non_manifold_vertices'] = list(result)
                
                total_time = time.time() - start_time
                self.message = f"检测到{len(result)}个{detection_title}\nC++算法用时: {detection_time:.4f}秒 (总用时: {total_time:.4f}秒)"
            
            else:
                # 使用Python实现
                self.update_progress(20, "使用Python算法检测...")
                self.detect_overlapping_points_python()
                
                total_time = time.time() - start_time
                result_points = self.result.get('selected_points', [])
                # 确保两个位置都有结果
                self.mesh_data['non_manifold_vertices'] = result_points
                
                self.message = f"检测到{len(result_points)}个{detection_title}\nPython算法用时: {total_time:.4f}秒"
            
            self.update_progress(100)
            self.close_progress_dialog()
            
            if parent:
                self.show_message(parent, f"{detection_title}完成", self.message)
            
            return self.result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.close_progress_dialog()
            if parent:
                self.show_message(parent, "错误", f"{detection_title}失败: {str(e)}", icon="critical")
            return self.result
    
    def detect_overlapping_points_python(self):
        """
        使用Python算法检测重叠点/非流形顶点
        
        重叠点的定义：当一个点连接了4条或更多自由边时，该点被认为是重叠点
        """
        # 用于存储每个点连接的边
        point_edges = {i: [] for i in range(len(self.vertices))}
        
        # 用于存储边的出现次数
        edge_count = {}
        
        self.update_progress(20, "统计边的出现次数...")
        
        # 统计所有边的出现次数
        for face in self.faces:
            for i in range(len(face)):
                # 获取边的两个端点（按较小的点索引在前排序）
                p1, p2 = sorted([face[i], face[(i + 1) % len(face)]])
                edge = (p1, p2)
                edge_count[edge] = edge_count.get(edge, 0) + 1
                
                # 记录每个点连接的边
                point_edges[p1].append(edge)
                point_edges[p2].append(edge)
        
        self.update_progress(60, "找出自由边和重叠点...")
        
        # 找出自由边（只出现一次的边）
        free_edges = {edge for edge, count in edge_count.items() if count == 1}
        
        # 检查每个点连接的自由边数量
        overlapping_points = set()
        total_points = len(self.vertices)
        
        # 如果指定了target_vertices，则只检查这些顶点
        check_vertices = self.target_vertices if self.target_vertices is not None else range(total_points)
        
        for point_idx in check_vertices:
            if point_idx % 100 == 0:
                progress = 60 + int(35 * point_idx / total_points)
                self.update_progress(progress, f"检查点 {point_idx}/{total_points}")
                if self.progress_dialog and self.progress_dialog.wasCanceled():
                    break
            
            # 计算与该点相连的自由边数量
            free_edge_count = sum(1 for edge in point_edges.get(point_idx, []) if edge in free_edges)
            
            # 如果自由边数量大于等于4，则认为是重叠点
            if free_edge_count >= 4:
                overlapping_points.add(point_idx)
        
        self.update_progress(95, "整理结果...")
        
        # 更新结果
        self.result['selected_points'] = list(overlapping_points)
        return self.result 