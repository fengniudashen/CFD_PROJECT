"""
重叠边检测算法
"""

import numpy as np
from .base_algorithm import BaseAlgorithm
import time

try:
    import overlapping_edges_cpp
    HAS_CPP_MODULE = True
    print("已加载C++重叠边检测模块")
except ImportError:
    HAS_CPP_MODULE = False
    print("警告: 未找到C++重叠边检测模块，将使用Python算法")

class OverlappingEdgesAlgorithm(BaseAlgorithm):
    """重叠边检测算法类"""
    
    def __init__(self, mesh_data=None, tolerance=1e-5):
        """
        初始化重叠边检测算法
        
        参数:
        mesh_data (dict): 包含顶点和面片数据的字典
        tolerance (float): 判断重叠的容差值
        """
        super().__init__(mesh_data)
        self.tolerance = tolerance
        self.use_cpp = HAS_CPP_MODULE
        self.message_shown = False
    
    def execute(self, parent=None, tolerance=None):
        """
        执行重叠边检测
        
        参数:
        parent: 父窗口，用于显示界面元素
        tolerance (float): 重叠判断容差，可选
        
        返回:
        dict: 结果字典，包含selected_edges
        """
        if tolerance is not None:
            self.tolerance = tolerance
            
        if not self.set_mesh_data(self.mesh_data):
            self.show_message(parent, "警告", "缺少有效的网格数据", icon="warning")
            self.message_shown = True
            return self.result
        
        # 显示进度对话框
        progress = self.show_progress_dialog(parent, "重叠边检测", "正在检测重叠边...", 100)
        
        start_time = time.time()
        
        try:
            # 尝试使用C++实现
            if self.use_cpp and HAS_CPP_MODULE:
                self.update_progress(10, "使用C++算法检测重叠边...")
                
                # 确保顶点和面片数据是numpy数组
                vertices_array = np.array(self.vertices, dtype=np.float64)
                faces_array = np.array(self.faces, dtype=np.int32)
                
                overlapping_edges, detection_time = overlapping_edges_cpp.detect_overlapping_edges_with_timing(
                    vertices_array, faces_array, self.tolerance)
                
                # C++返回的是原始边数据，我们需要转换为元组列表
                self.result['selected_edges'] = [tuple(edge) for edge in overlapping_edges]
                
                total_time = time.time() - start_time
                self.message = f"检测到{len(overlapping_edges)}条重叠边\nC++算法用时: {detection_time:.4f}秒 (总用时: {total_time:.4f}秒)"
                
                # 打印性能对比提示
                print(f"C++重叠边检测用时: {detection_time:.4f}秒")
            else:
                # 使用Python算法
                self.update_progress(10, "使用Python算法检测重叠边...")
                python_start = time.time()
                self.detect_overlapping_edges_python()
                python_time = time.time() - python_start
                
                total_time = time.time() - start_time
                self.message = f"检测到{len(self.result['selected_edges'])}条重叠边\nPython算法用时: {python_time:.4f}秒 (总用时: {total_time:.4f}秒)"
                
                # 打印性能信息
                print(f"Python重叠边检测用时: {python_time:.4f}秒")
            
            self.update_progress(100)
            self.close_progress_dialog()
            
            if parent:
                self.show_message(parent, "重叠边检测完成", self.message)
                self.message_shown = True
            
            return self.result
            
        except Exception as e:
            self.close_progress_dialog()
            if parent:
                self.show_message(parent, "错误", f"重叠边检测失败: {str(e)}", icon="critical")
                self.message_shown = True
            return self.result
    
    def detect_overlapping_edges_python(self):
        """
        使用Python算法检测重叠边
        
        重叠边定义：同一条几何边被多个面片共享超过2次的情况
        """
        # 使用字典来存储边信息
        edge_count = {}  # 记录每条边出现的次数
        edge_indices = {}  # 存储每条边对应的原始顶点索引
        
        # 遍历所有面片，收集边信息
        for face in self.faces:
            # 获取面片的三条边
            edges = [
                (face[0], face[1]),
                (face[1], face[2]),
                (face[2], face[0])
            ]
            
            for i, (v1_idx, v2_idx) in enumerate(edges):
                # 获取顶点坐标
                v1 = self.vertices[v1_idx]
                v2 = self.vertices[v2_idx]
                
                # 确保边的方向一致（从小索引到大索引）
                if v1_idx > v2_idx:
                    v1_idx, v2_idx = v2_idx, v1_idx
                    v1, v2 = v2, v1
                
                # 创建边的几何键（使用顶点坐标的哈希）
                # 这样可以检测到共享相同几何位置但不共享顶点索引的边
                geo_key = self.get_edge_geo_key(v1, v2)
                
                # 更新边的计数和索引信息
                if geo_key in edge_count:
                    edge_count[geo_key] += 1
                else:
                    edge_count[geo_key] = 1
                    edge_indices[geo_key] = (v1_idx, v2_idx)
        
        # 找出出现超过2次的边（重叠边）
        overlapping_edges = [edge_indices[geo_key] for geo_key, count in edge_count.items() if count > 2]
        
        # 更新结果
        self.result['selected_edges'] = overlapping_edges
        return overlapping_edges
    
    def get_edge_geo_key(self, v1, v2):
        """
        根据顶点的几何位置创建边的唯一标识
        
        参数:
        v1, v2: 边的两个顶点坐标
        
        返回:
        tuple: 边的几何键
        """
        # 对坐标进行四舍五入，考虑容差
        precision = int(-np.log10(self.tolerance))
        v1_rounded = tuple(round(coord, precision) for coord in v1)
        v2_rounded = tuple(round(coord, precision) for coord in v2)
        
        # 确保返回的键是有序的
        if v1_rounded < v2_rounded:
            return (v1_rounded, v2_rounded)
        else:
            return (v2_rounded, v1_rounded) 