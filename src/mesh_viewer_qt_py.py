"""
基于PyQt5的网格查看器

这个模块提供了一个基于PyQt5的3D网格查看器，用于可视化和分析网格数据
"""

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QAction, QFileDialog, QMessageBox
from PyQt5.QtWidgets import QLabel, QToolBar, QPushButton, QComboBox, QSplitter
from PyQt5.QtCore import Qt, QSize

import numpy as np
import os
import sys

# 导入算法包中的所有算法
from algorithms import (
    BaseAlgorithm, AlgorithmUtils, FreeEdgesAlgorithm, OverlappingEdgesAlgorithm,
    PiercedFacesAlgorithm, SelfIntersectionAlgorithm, FaceQualityAlgorithm,
    OverlappingPointsAlgorithm
)

# 导入网格读取器
from mesh_reader import create_mesh_reader

class MeshViewerWidget(QMainWindow):
    """主网格查看器窗口类"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CFD网格查看器")
        self.resize(1200, 800)
        
        # 初始化状态变量
        self.mesh_data = None
        self.selection_mode = None
        self.selected_points = []
        self.selected_edges = []
        self.selected_triangles = []
        
        # 创建菜单栏和工具栏
        self._create_menu_bar()
        self._create_toolbar()
        
        # 创建状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪")
        
        # 创建主UI布局
        self._create_main_layout()
        
        # 创建3D视图
        self._create_3d_view()
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menu_bar = self.menuBar()
        
        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        
        open_action = QAction("打开", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        export_action = QAction("导出选中部分", self)
        export_action.triggered.connect(self.export_selection)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menu_bar.addMenu("视图")
        
        reset_view_action = QAction("重置视图", self)
        reset_view_action.triggered.connect(self.reset_view)
        view_menu.addAction(reset_view_action)
        
        # 工具菜单
        tools_menu = menu_bar.addMenu("工具")
        
        check_free_edges_action = QAction("检测自由边", self)
        check_free_edges_action.triggered.connect(self.run_free_edges_algorithm)
        tools_menu.addAction(check_free_edges_action)
        
        check_pierced_faces_action = QAction("检测穿透面", self)
        check_pierced_faces_action.triggered.connect(self.run_pierced_faces_algorithm)
        tools_menu.addAction(check_pierced_faces_action)
        
        check_overlapping_edges_action = QAction("检测重叠边", self)
        check_overlapping_edges_action.triggered.connect(self.run_overlapping_edges_algorithm)
        tools_menu.addAction(check_overlapping_edges_action)
        
        check_self_intersection_action = QAction("检测自相交", self)
        check_self_intersection_action.triggered.connect(self.run_self_intersection_algorithm)
        tools_menu.addAction(check_self_intersection_action)
        
        check_face_quality_action = QAction("分析面片质量", self)
        check_face_quality_action.triggered.connect(self.run_face_quality_algorithm)
        tools_menu.addAction(check_face_quality_action)
        
        check_overlapping_points_action = QAction("检测重叠点", self)
        check_overlapping_points_action.triggered.connect(self.run_overlapping_points_algorithm)
        tools_menu.addAction(check_overlapping_points_action)
        
        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def _create_toolbar(self):
        """创建工具栏"""
        self.toolbar = QToolBar("主工具栏")
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        
        # 文件操作按钮
        self.open_btn = QPushButton("打开")
        self.open_btn.clicked.connect(self.open_file)
        self.toolbar.addWidget(self.open_btn)
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_file)
        self.toolbar.addWidget(self.save_btn)
        
        # 添加一个分隔符
        self.toolbar.addSeparator()
        
        # 视图操作按钮
        self.reset_view_btn = QPushButton("重置视图")
        self.reset_view_btn.clicked.connect(self.reset_view)
        self.toolbar.addWidget(self.reset_view_btn)
        
        # 添加一个分隔符
        self.toolbar.addSeparator()
        
        # 检查网格质量按钮
        self.free_edges_btn = QPushButton("检测自由边")
        self.free_edges_btn.clicked.connect(self.run_free_edges_algorithm)
        self.toolbar.addWidget(self.free_edges_btn)
        
        self.pierced_faces_btn = QPushButton("检测穿透面")
        self.pierced_faces_btn.clicked.connect(self.run_pierced_faces_algorithm)
        self.toolbar.addWidget(self.pierced_faces_btn)
        
        self.overlapping_edges_btn = QPushButton("检测重叠边")
        self.overlapping_edges_btn.clicked.connect(self.run_overlapping_edges_algorithm)
        self.toolbar.addWidget(self.overlapping_edges_btn)
        
        self.self_intersection_btn = QPushButton("检测自相交")
        self.self_intersection_btn.clicked.connect(self.run_self_intersection_algorithm)
        self.toolbar.addWidget(self.self_intersection_btn)
        
        self.face_quality_btn = QPushButton("分析面片质量")
        self.face_quality_btn.clicked.connect(self.run_face_quality_algorithm)
        self.toolbar.addWidget(self.face_quality_btn)
        
        self.overlapping_points_btn = QPushButton("检测重叠点")
        self.overlapping_points_btn.clicked.connect(self.run_overlapping_points_algorithm)
        self.toolbar.addWidget(self.overlapping_points_btn)
        
        # 添加一个分隔符
        self.toolbar.addSeparator()
    
    def _create_main_layout(self):
        """创建主布局"""
        # 创建中心组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建分隔器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 创建3D视图区域容器
        self.viewer_container = QWidget()
        viewer_layout = QVBoxLayout(self.viewer_container)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(self.viewer_container)
        
        # 创建右侧信息面板
        info_panel = QWidget()
        info_layout = QVBoxLayout(info_panel)
        info_layout.setAlignment(Qt.AlignTop)
        
        # 添加网格信息标签
        self.mesh_info_label = QLabel("网格信息:")
        info_layout.addWidget(self.mesh_info_label)
        
        # 添加选择模式下拉框
        selection_layout = QHBoxLayout()
        selection_layout.addWidget(QLabel("选择模式:"))
        self.selection_mode_combo = QComboBox()
        self.selection_mode_combo.addItems(["无", "点", "边", "面"])
        self.selection_mode_combo.currentIndexChanged.connect(self.change_selection_mode)
        selection_layout.addWidget(self.selection_mode_combo)
        info_layout.addLayout(selection_layout)
        
        # 添加选择信息标签
        self.selection_info_label = QLabel("选择: 无")
        info_layout.addWidget(self.selection_info_label)
        
        # 将信息面板添加到分隔器
        splitter.addWidget(info_panel)
        
        # 设置分隔器的初始大小
        splitter.setSizes([800, 400])
    
    def _create_3d_view(self):
        """创建3D视图（此处需要实现实际的3D渲染）"""
        # 这里应该创建实际的3D视图控件，并添加到viewer_container中
        # 由于当前示例简化，我们只添加一个placeholder标签
        placeholder = QLabel("3D视图区域")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        layout = self.viewer_container.layout()
        layout.addWidget(placeholder)
    
    def update_selection_mode(self, mode):
        """
        更新选择模式
        
        参数:
        mode (str): 'points', 'edges' 或 'triangles'
        """
        self.selection_mode = mode
        
        # 更新下拉框
        if mode == "points":
            self.selection_mode_combo.setCurrentIndex(1)
            self.selection_info_label.setText(f"选择: {len(self.selected_points)} 个点")
        elif mode == "edges":
            self.selection_mode_combo.setCurrentIndex(2)
            self.selection_info_label.setText(f"选择: {len(self.selected_edges)} 条边")
        elif mode == "triangles":
            self.selection_mode_combo.setCurrentIndex(3)
            self.selection_info_label.setText(f"选择: {len(self.selected_triangles)} 个面")
        else:
            self.selection_mode_combo.setCurrentIndex(0)
            self.selection_info_label.setText("选择: 无")
    
    def change_selection_mode(self, index):
        """
        当用户从下拉框改变选择模式时调用
        
        参数:
        index (int): 下拉框的索引
        """
        modes = ["none", "points", "edges", "triangles"]
        if index > 0:
            self.update_selection_mode(modes[index])
        else:
            # 清除选择
            self.selection_mode = None
            self.selected_points = []
            self.selected_edges = []
            self.selected_triangles = []
            self.selection_info_label.setText("选择: 无")
            # 更新3D视图显示
            # self.update_3d_view()
    
    def open_file(self):
        """打开网格文件"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "打开网格文件", "", "NAS文件 (*.nas);;STL文件 (*.stl);;所有文件 (*.*)"
        )
        
        if file_name:
            try:
                # 使用create_mesh_reader来读取正确的文件类型
                reader = create_mesh_reader(file_name)
                self.mesh_data = reader.read(file_name)
                
                # 更新网格信息
                num_vertices = len(self.mesh_data['vertices'])
                num_faces = len(self.mesh_data['faces'])
                self.mesh_info_label.setText(f"网格信息: {num_vertices} 顶点, {num_faces} 面")
                
                # 重置选择
                self.selection_mode = None
                self.selected_points = []
                self.selected_edges = []
                self.selected_triangles = []
                self.selection_mode_combo.setCurrentIndex(0)
                self.selection_info_label.setText("选择: 无")
                
                # 更新状态栏
                self.status_bar.showMessage(f"已加载文件: {os.path.basename(file_name)}")
                
                # 更新3D视图
                # self.update_3d_view()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开文件: {str(e)}")
    
    def save_file(self):
        """保存网格文件"""
        if not self.mesh_data:
            QMessageBox.warning(self, "警告", "没有网格数据可保存")
            return
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "保存网格文件", "", "NAS文件 (*.nas);;STL文件 (*.stl);;所有文件 (*.*)"
        )
        
        if file_name:
            # 这里应该实现实际的保存逻辑
            self.status_bar.showMessage(f"已保存文件: {os.path.basename(file_name)}")
    
    def export_selection(self):
        """导出选中的部分"""
        if not self.mesh_data or not (self.selected_points or self.selected_edges or self.selected_triangles):
            QMessageBox.warning(self, "警告", "没有选中的数据可导出")
            return
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "导出选中部分", "", "NAS文件 (*.nas);;STL文件 (*.stl);;所有文件 (*.*)"
        )
        
        if file_name:
            # 这里应该实现实际的导出逻辑
            self.status_bar.showMessage(f"已导出选中部分到文件: {os.path.basename(file_name)}")
    
    def reset_view(self):
        """重置3D视图"""
        # 这里应该实现重置3D视图的逻辑
        self.status_bar.showMessage("已重置视图")
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于", "CFD网格查看器 v0.1.0\n\n一个用于CFD网格可视化和分析的工具")
    
    def run_free_edges_algorithm(self):
        """运行自由边检测算法"""
        if not self.mesh_data:
            QMessageBox.warning(self, "警告", "请先加载一个网格文件")
            return
        
        algorithm = FreeEdgesAlgorithm(self.mesh_data)
        result = algorithm.execute(self)
        
        if 'selected_edges' in result and result['selected_edges']:
            self.selected_edges = result['selected_edges']
            self.update_selection_mode("edges")
            self.status_bar.showMessage(f"检测到 {len(self.selected_edges)} 条自由边")
        else:
            self.status_bar.showMessage("未检测到自由边")
    
    def run_pierced_faces_algorithm(self):
        """运行穿透面检测算法"""
        if not self.mesh_data:
            QMessageBox.warning(self, "警告", "请先加载一个网格文件")
            return
        
        algorithm = PiercedFacesAlgorithm(self.mesh_data)
        result = algorithm.execute(self)
        
        if 'selected_faces' in result and result['selected_faces']:
            self.selected_triangles = result['selected_faces']
            self.update_selection_mode("triangles")
            self.status_bar.showMessage(f"检测到 {len(self.selected_triangles)} 个穿透面")
        else:
            self.status_bar.showMessage("未检测到穿透面")
    
    def run_overlapping_edges_algorithm(self):
        """运行重叠边检测算法"""
        if not self.mesh_data:
            QMessageBox.warning(self, "警告", "请先加载一个网格文件")
            return
        
        algorithm = OverlappingEdgesAlgorithm(self.mesh_data)
        result = algorithm.execute(self)
        
        if 'selected_edges' in result and result['selected_edges']:
            self.selected_edges = result['selected_edges']
            self.update_selection_mode("edges")
            self.status_bar.showMessage(f"检测到 {len(self.selected_edges)} 个重叠边")
        else:
            self.status_bar.showMessage("未检测到重叠边")
    
    def run_self_intersection_algorithm(self):
        """运行自相交检测算法"""
        if not self.mesh_data:
            QMessageBox.warning(self, "警告", "请先加载一个网格文件")
            return
        
        algorithm = SelfIntersectionAlgorithm(self.mesh_data)
        result = algorithm.execute(self)
        
        if 'selected_triangles' in result and result['selected_triangles']:
            self.selected_triangles = result['selected_triangles']
            self.update_selection_mode("triangles")
            self.status_bar.showMessage(f"检测到 {len(self.selected_triangles)} 个自相交面片")
        else:
            self.status_bar.showMessage("未检测到自相交面片")
    
    def run_face_quality_algorithm(self):
        """运行面片质量分析算法"""
        if not self.mesh_data:
            QMessageBox.warning(self, "警告", "请先加载一个网格文件")
            return
        
        algorithm = FaceQualityAlgorithm(self.mesh_data)
        result = algorithm.execute(self)
        
        if 'selected_faces' in result and result['selected_faces']:
            self.selected_triangles = result['selected_faces']
            self.update_selection_mode("triangles")
            self.status_bar.showMessage(f"检测到 {len(self.selected_triangles)} 个低质量面片")
        else:
            self.status_bar.showMessage("未检测到低质量面片")
    
    def run_overlapping_points_algorithm(self):
        """运行重叠点检测算法"""
        if not self.mesh_data:
            QMessageBox.warning(self, "警告", "请先加载一个网格文件")
            return
        
        algorithm = OverlappingPointsAlgorithm(self.mesh_data)
        result = algorithm.execute(self)
        
        if 'selected_points' in result and result['selected_points']:
            self.selected_points = result['selected_points']
            self.update_selection_mode("points")
            self.status_bar.showMessage(f"检测到 {len(self.selected_points)} 个重叠点")
        else:
            self.status_bar.showMessage("未检测到重叠点")

# 如果直接运行此脚本，则创建和显示应用程序
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建并显示主窗口
    viewer = MeshViewerWidget()
    viewer.show()
    
    # 运行应用程序
    sys.exit(app.exec_()) 