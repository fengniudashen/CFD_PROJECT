"""
基础算法接口
定义了所有检测算法共用的接口和方法
"""

import numpy as np
from PyQt5.QtWidgets import QProgressDialog, QMessageBox
from PyQt5.QtCore import Qt
import time

class BaseAlgorithm:
    """所有检测算法的基类"""
    
    def __init__(self, mesh_data=None):
        """
        初始化算法
        
        参数:
        mesh_data (dict): 包含顶点和面片数据的字典，包含'vertices'和'faces'键
        """
        self.mesh_data = mesh_data
        self.vertices = None
        self.faces = None
        self.result = {
            'selected_points': [],
            'selected_edges': [],
            'selected_faces': [],
        }
        self.message = ""
        self.progress_dialog = None
    
    def set_mesh_data(self, mesh_data):
        """
        设置要处理的网格数据
        
        参数:
        mesh_data (dict): 包含顶点和面片数据的字典
        """
        self.mesh_data = mesh_data
        if mesh_data and 'vertices' in mesh_data and 'faces' in mesh_data:
            self.vertices = np.array(mesh_data['vertices'])
            self.faces = np.array(mesh_data['faces'])
            return True
        return False
    
    def show_progress_dialog(self, parent, title, text, max_value=100):
        """
        显示进度对话框
        
        参数:
        parent: 父窗口
        title (str): 对话框标题
        text (str): 对话框文本
        max_value (int): 进度最大值
        """
        self.progress_dialog = QProgressDialog(text, "取消", 0, max_value, parent)
        self.progress_dialog.setWindowTitle(title)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.show()
        return self.progress_dialog
    
    def update_progress(self, value, text=None):
        """
        更新进度对话框
        
        参数:
        value (int): 当前进度值
        text (str): 进度文本，可选
        
        返回:
        bool: 是否取消
        """
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            if text:
                self.progress_dialog.setLabelText(text)
            return self.progress_dialog.wasCanceled()
        return False
    
    def close_progress_dialog(self):
        """关闭进度对话框"""
        if self.progress_dialog:
            self.progress_dialog.setValue(self.progress_dialog.maximum())
            self.progress_dialog = None
    
    def show_message(self, parent, title, text, icon=QMessageBox.Information):
        """
        显示消息对话框
        
        参数:
        parent: 父窗口
        title (str): 对话框标题
        text (str): 对话框文本
        icon: 对话框图标类型
        """
        QMessageBox(icon, title, text, QMessageBox.Ok, parent).exec_()
    
    def execute(self, parent=None):
        """
        执行算法(需要子类实现)
        
        参数:
        parent: 父窗口，用于显示界面元素
        
        返回:
        dict: 结果字典，包含selected_points, selected_edges, selected_faces等
        """
        raise NotImplementedError("子类必须实现execute方法")
    
    def get_result_message(self):
        """
        获取结果消息
        
        返回:
        str: 结果消息
        """
        return self.message 