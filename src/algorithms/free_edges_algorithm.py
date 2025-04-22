"""
自由边检测算法
"""

import numpy as np
from .base_algorithm import BaseAlgorithm
import time

try:
    import free_edges_cpp
    HAS_CPP_MODULE = True
except ImportError:
    HAS_CPP_MODULE = False

class FreeEdgesAlgorithm(BaseAlgorithm):
    """自由边检测算法类"""
    
    def __init__(self, mesh_data=None):
        """
        初始化自由边检测算法
        
        参数:
        mesh_data (dict): 包含顶点和面片数据的字典
        """
        super().__init__(mesh_data)
        self.use_cpp = HAS_CPP_MODULE
    
    def execute(self, parent=None):
        """
        执行自由边检测
        
        参数:
        parent: 父窗口，用于显示界面元素
        
        返回:
        dict: 结果字典，包含selected_edges
        """
        if not self.set_mesh_data(self.mesh_data):
            # 仅在 parent 存在时显示警告
            if parent:
                self.show_message(parent, "警告", "缺少有效的网格数据", icon="warning")
            return self.result
        
        # 只有在 parent 不为 None 时才显示进度对话框
        progress = None
        if parent:
            progress = self.show_progress_dialog(parent, "自由边检测", "正在检测自由边...", 100)
        
        start_time = time.time()
        
        try:
            # 尝试使用C++实现
            if self.use_cpp and HAS_CPP_MODULE:
                if progress: self.update_progress(10, "使用C++算法检测自由边...")
                free_edges, detection_time = free_edges_cpp.detect_free_edges_with_timing(self.faces)
                # 确保 free_edges 是列表
                if not isinstance(free_edges, list):
                    free_edges = [] # 或者进行适当的转换
                self.result['selected_edges'] = free_edges
                
                total_time = time.time() - start_time
                self.message = f"检测到{len(free_edges)}条自由边\nC++算法用时: {detection_time:.4f}秒 (总用时: {total_time:.4f}秒)"
            else:
                # 使用Python算法
                if progress: self.update_progress(10, "使用Python算法检测自由边...")
                self.detect_free_edges_python(progress)
                
                total_time = time.time() - start_time
                num_edges = len(self.result.get('selected_edges', []))
                self.message = f"检测到{num_edges}条自由边\nPython算法用时: {total_time:.4f}秒"
            
            if progress: self.update_progress(100)
            if progress: self.close_progress_dialog()
            
            if parent:
                self.show_message(parent, "自由边检测完成", self.message)
            
            return self.result
            
        except Exception as e:
            if progress: self.close_progress_dialog()
            if parent:
                self.show_message(parent, "错误", f"自由边检测失败: {str(e)}", icon="critical")
            # 确保返回默认结果
            if self.result is None:
                 self.result = {'selected_edges': []}
            elif 'selected_edges' not in self.result:
                 self.result['selected_edges'] = []
            return self.result
    
    def detect_free_edges_python(self, progress=None):
        """
        使用Python算法检测自由边
        
        自由边定义：只被一个面片使用的边
        """
        # 使用字典来存储边信息
        edge_count = {}  # 用字典记录每条边出现的次数
        
        # 遍历所有面片，收集边信息
        total_faces = len(self.faces)
        if progress: self.update_progress(10, f"处理 {total_faces} 个面片...")
        
        for idx, face in enumerate(self.faces):
            # 更新进度 (仅在 progress 存在时)
            if progress and idx % 100 == 0: # 每处理100个面片更新一次
                progress_value = 10 + int(80 * idx / total_faces)
                self.update_progress(progress_value, f"处理面片 {idx+1}/{total_faces}")
            
            # 获取面片的三条边
            edge1 = tuple(sorted([face[0], face[1]]))
            edge2 = tuple(sorted([face[1], face[2]]))
            edge3 = tuple(sorted([face[2], face[0]]))
            
            # 更新边的计数
            edge_count[edge1] = edge_count.get(edge1, 0) + 1
            edge_count[edge2] = edge_count.get(edge2, 0) + 1
            edge_count[edge3] = edge_count.get(edge3, 0) + 1
        
        # 找出只出现一次的边（自由边）
        if progress: self.update_progress(90, "筛选自由边...")
        free_edges = [edge for edge, count in edge_count.items() if count == 1]
        
        # 更新结果 (确保 self.result 是字典)
        if self.result is None:
            self.result = {}
        self.result['selected_edges'] = free_edges
        
        if progress: self.update_progress(95, "完成")
        return free_edges 