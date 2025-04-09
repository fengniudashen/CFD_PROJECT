import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QFrame, QLabel, QLineEdit,
<<<<<<< HEAD
                           QGridLayout, QMessageBox, QStatusBar, QProgressDialog)
from PyQt5.QtGui import QFont, QIcon, QPainter, QPen, QColor, QPixmap
from PyQt5.QtCore import Qt, QSize
=======
                           QGridLayout, QMessageBox, QStatusBar)
>>>>>>> 61808a0fd45044b397c6488dce73d9e755b79762
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtkmodules.all as vtk
from typing import Dict

class StatusIndicator(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.setMaximumHeight(25)
        self.setMinimumWidth(80)
        self.setMaximumWidth(100)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(2)
        
        # 标题
        self.title_label = QLabel(title, self)  # 添加 self 作为父对象
        self.title_label.setFont(QFont('Arial', 8))
        layout.addWidget(self.title_label)
        
        # 数量
        self.count_label = QLabel('0', self)  # 添加 self 作为父对象
        self.count_label.setFont(QFont('Arial', 8))
        layout.addWidget(self.count_label)
        
        # 清除按钮
        self.clear_btn = QPushButton('×', self)  # 添加 self 作为父对象
        self.clear_btn.setMaximumWidth(15)
        self.clear_btn.setMaximumHeight(15)
        self.clear_btn.setFont(QFont('Arial', 8))
        self.clear_btn.clicked.connect(self.clear_clicked)
        layout.addWidget(self.clear_btn)
        
        self.setLayout(layout)
    
    def set_count(self, count):
        self.count_label.setText(str(count))
    
    def clear_clicked(self):
        pass

class MeshViewerQt(QMainWindow):
    def __init__(self, mesh_data: Dict):
        super().__init__()
        self.mesh_data = mesh_data
        self.selected_faces = []
        self.selected_points = []
        self.selected_edges = []
        self.temp_points = []
        self.selection_mode = 'point'
        
        # 添加拖动状态跟踪
        self.left_button_down = False
        self.moved_since_press = False
        self.press_pos = None
        
        # 创建 VTK 小部件
        self.vtk_widget = QVTKRenderWindowInteractor()
        
        # 创建渲染器和选择器
        self.renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.iren = self.vtk_widget.GetRenderWindow().GetInteractor()
        
        # 设置选择器
        self.cell_picker = vtk.vtkCellPicker()
        self.cell_picker.SetTolerance(0.001)
        self.iren.SetPicker(self.cell_picker)
        
        # 创建网格
        self.mesh = self.create_vtk_mesh()
        
        # 创建底部状态栏用于显示选择信息
        self.statusBar = self.statusBar()
        
        self.initUI()
    
    def initUI(self):
        """初始化UI"""
        self.setWindowTitle('Mesh Viewer')
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(main_widget)
        
        # 创建内容区域布局（控制面板和VTK窗口）
        content_layout = QHBoxLayout()
        
        # 创建左侧控制面板
        control_panel = QFrame()
        control_panel.setFrameStyle(QFrame.Panel | QFrame.Raised)
        control_panel.setMaximumWidth(300)
        control_layout = QVBoxLayout(control_panel)
        
        # 创建点坐标输入区域
        coord_group = QFrame()
        coord_layout = QGridLayout(coord_group)
        
        # X坐标输入
        coord_layout.addWidget(QLabel('X:'), 0, 0)
        self.x_input = QLineEdit()
        coord_layout.addWidget(self.x_input, 0, 1)
        
        # Y坐标输入
        coord_layout.addWidget(QLabel('Y:'), 1, 0)
        self.y_input = QLineEdit()
        coord_layout.addWidget(self.y_input, 1, 1)
        
        # Z坐标输入
        coord_layout.addWidget(QLabel('Z:'), 2, 0)
        self.z_input = QLineEdit()
        coord_layout.addWidget(self.z_input, 2, 1)
        
        # 创建点按钮
        create_point_btn = QPushButton('创建点')
        create_point_btn.clicked.connect(self.create_point)
        coord_layout.addWidget(create_point_btn, 3, 0, 1, 2)
        
        control_layout.addWidget(coord_group)
        
        # 创建面操作区域
        face_group = QFrame()
        face_layout = QVBoxLayout(face_group)
        
        # 从选中点创建面按钮
        create_face_btn = QPushButton('从选中点创建面')
        create_face_btn.clicked.connect(self.create_face)
        face_layout.addWidget(create_face_btn)
        
<<<<<<< HEAD
        # 删除选中面按钮
        delete_face_btn = QPushButton('删除选中面')
        delete_face_btn.clicked.connect(self.delete_selected_faces)
        face_layout.addWidget(delete_face_btn)
        
=======
>>>>>>> 61808a0fd45044b397c6488dce73d9e755b79762
        # 清除选择按钮
        clear_selection_btn = QPushButton('清除选择')
        clear_selection_btn.clicked.connect(self.clear_selection)
        face_layout.addWidget(clear_selection_btn)
        
        control_layout.addWidget(face_group)
        
        # 添加选择模式切换按钮
        mode_group = QFrame()
        mode_layout = QHBoxLayout(mode_group)
        
        self.point_mode_btn = QPushButton('点选择')
        self.edge_mode_btn = QPushButton('线选择')
        self.face_mode_btn = QPushButton('面选择')
        self.smart_mode_btn = QPushButton('智能选择')
        
        self.point_mode_btn.setCheckable(True)
        self.edge_mode_btn.setCheckable(True)
        self.face_mode_btn.setCheckable(True)
        self.smart_mode_btn.setCheckable(True)
        
        self.point_mode_btn.setChecked(True)
        
        mode_layout.addWidget(self.point_mode_btn)
        mode_layout.addWidget(self.edge_mode_btn)
        mode_layout.addWidget(self.face_mode_btn)
        mode_layout.addWidget(self.smart_mode_btn)
        
        control_layout.addWidget(mode_group)
        
        # 连接模式切换信号
        self.point_mode_btn.clicked.connect(lambda: self.set_selection_mode('point'))
        self.edge_mode_btn.clicked.connect(lambda: self.set_selection_mode('edge'))
        self.face_mode_btn.clicked.connect(lambda: self.set_selection_mode('face'))
        self.smart_mode_btn.clicked.connect(lambda: self.set_selection_mode('smart'))
        
        # 添加伸缩器
        control_layout.addStretch()
        
        # 设置控制面板布局
        control_panel.setLayout(control_layout)
        
        # 创建右侧VTK和状态指示器容器
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
<<<<<<< HEAD
        # 创建水平布局来放置VTK窗口和自由边按钮
        vtk_container = QHBoxLayout()
        
        # 创建VTK窗口容器（用于放置VTK窗口和自由边按钮）
        vtk_frame = QWidget()
        vtk_frame.setStyleSheet("background-color: transparent;")
        vtk_frame_layout = QHBoxLayout(vtk_frame)
        vtk_frame_layout.setContentsMargins(0, 0, 0, 0)
        vtk_frame_layout.addWidget(self.vtk_widget)
        
        # 创建Face intersection按钮图标
        intersection_icon = QIcon('src/icons/face_intersection.svg')
        
        # 创建快速交叉面按钮图标（复用交叉面图标）
        fast_intersection_icon = QIcon('src/icons/face_intersection.svg')

        # 创建Face quality按钮图标
        quality_icon = QIcon('src/icons/face_quality.svg')

        # 创建Face proximity按钮图标
        prox_icon = QIcon()
        prox_pixmap = QPixmap(32, 32)
        prox_pixmap.fill(Qt.transparent)
        prox_painter = QPainter(prox_pixmap)
        prox_painter.setRenderHint(QPainter.Antialiasing)
        prox_pen = QPen(QColor(0, 255, 0))
        prox_pen.setWidth(2)
        prox_painter.setPen(prox_pen)
        prox_painter.drawLine(8, 12, 24, 12)  # 上面的绿线
        prox_painter.drawLine(8, 20, 24, 20)  # 下面的绿线
        prox_painter.end()
        prox_icon.addPixmap(prox_pixmap)

        # 创建自由边按钮图标
        icon = QIcon()
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(0, 255, 0))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(8, 16, 24, 16)  # 只绘制一条水平的绿线
        painter.end()
        icon.addPixmap(pixmap)
        
        # 添加交叉面按钮（使用优化算法）
        fast_intersection_btn = QPushButton('交叉面')
        fast_intersection_btn.setIcon(fast_intersection_icon)
        fast_intersection_btn.setIconSize(QSize(20, 20))
        fast_intersection_btn.setFixedSize(100, 30)
        fast_intersection_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #999999;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #666666;
            }
        """)
        fast_intersection_btn.clicked.connect(self.detect_face_intersections)

        # 添加Face quality按钮
        face_quality_btn = QPushButton('面质量')
        face_quality_btn.setIcon(quality_icon)
        face_quality_btn.setIconSize(QSize(20, 20))
        face_quality_btn.setFixedSize(80, 30)
        face_quality_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #999999;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #666666;
            }
        """)
        face_quality_btn.clicked.connect(self.analyze_face_quality)

        # 添加Face proximity按钮
        face_prox_btn = QPushButton('相邻面')
        face_prox_btn.setIcon(prox_icon)
        face_prox_btn.setIconSize(QSize(20, 20))
        face_prox_btn.setFixedSize(80, 30)
        face_prox_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #999999;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #666666;
            }
        """)
        face_prox_btn.clicked.connect(self.select_adjacent_faces)

        # 创建重叠边按钮图标
        overlap_icon = QIcon()
        overlap_pixmap = QPixmap(32, 32)
        overlap_pixmap.fill(Qt.transparent)
        overlap_painter = QPainter(overlap_pixmap)
        overlap_painter.setRenderHint(QPainter.Antialiasing)
        overlap_pen = QPen(QColor(0, 255, 0))
        overlap_pen.setWidth(2)
        overlap_painter.setPen(overlap_pen)
        overlap_painter.drawLine(8, 14, 24, 14)  # 第一条线
        overlap_painter.drawLine(8, 18, 24, 18)  # 第二条线，与第一条线重叠
        overlap_painter.end()
        overlap_icon.addPixmap(overlap_pixmap)
        
        # 创建重叠点按钮图标
        overlap_point_icon = QIcon()
        overlap_point_pixmap = QPixmap(32, 32)
        overlap_point_pixmap.fill(Qt.transparent)
        overlap_point_painter = QPainter(overlap_point_pixmap)
        overlap_point_painter.setRenderHint(QPainter.Antialiasing)
        overlap_point_pen = QPen(QColor(0, 255, 0))
        overlap_point_pen.setWidth(2)
        overlap_point_painter.setPen(overlap_point_pen)
        # 绘制两个重叠的圆点
        overlap_point_painter.drawEllipse(10, 16, 6, 6)  # 第一个圆点
        overlap_point_painter.drawEllipse(14, 16, 6, 6)  # 第二个圆点，与第一个重叠
        overlap_point_painter.end()
        overlap_point_icon.addPixmap(overlap_point_pixmap)

        # 添加重叠边按钮
        overlap_edge_btn = QPushButton('重叠边')
        overlap_edge_btn.setIcon(overlap_icon)
        overlap_edge_btn.setIconSize(QSize(20, 20))
        overlap_edge_btn.setFixedSize(80, 30)
        overlap_edge_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #999999;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #666666;
            }
        """)
        overlap_edge_btn.clicked.connect(self.select_overlapping_edges)
        overlap_edge_btn.setParent(vtk_frame)
        
        # 添加重叠点按钮
        overlap_point_btn = QPushButton('重叠点')
        overlap_point_btn.setIcon(overlap_point_icon)
        overlap_point_btn.setIconSize(QSize(20, 20))
        overlap_point_btn.setFixedSize(80, 30)
        overlap_point_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #999999;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #666666;
            }
        """)
        overlap_point_btn.clicked.connect(self.select_overlapping_points)
        overlap_point_btn.setParent(vtk_frame)
        
        # 添加自由边选择按钮（放在渲染窗口内部的右侧中间）
        free_edge_btn = QPushButton('自由边')
        free_edge_btn.setIcon(icon)
        free_edge_btn.setIconSize(QSize(20, 20))
        free_edge_btn.setFixedSize(80, 30)
        free_edge_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #999999;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #666666;
            }
        """)
        free_edge_btn.clicked.connect(self.select_free_edges)
        
        # 创建一个绝对定位的容器来放置按钮
        vtk_frame.setLayout(vtk_frame_layout)
        vtk_container.addWidget(vtk_frame)
        
        # 将按钮添加到VTK窗口中，并设置为绝对定位
        fast_intersection_btn.setParent(vtk_frame)
        face_quality_btn.setParent(vtk_frame)
        face_prox_btn.setParent(vtk_frame)
        free_edge_btn.setParent(vtk_frame)
        
        # 设置按钮位置
        fast_intersection_btn.move(vtk_frame.width() - 90, int(vtk_frame.height() / 2 - 120))
        face_quality_btn.move(vtk_frame.width() - 90, int(vtk_frame.height() / 2 - 85))
        face_prox_btn.move(vtk_frame.width() - 90, int(vtk_frame.height() / 2 - 50))
        free_edge_btn.move(vtk_frame.width() - 90, int(vtk_frame.height() / 2 - 15))
        overlap_edge_btn.move(vtk_frame.width() - 90, int(vtk_frame.height() / 2 + 20))  # 重叠边按钮在自由边按钮下方
        overlap_point_btn.move(vtk_frame.width() - 90, int(vtk_frame.height() / 2 + 55))  # 重叠点按钮位置下移
        
        # 当VTK窗口大小改变时，更新按钮位置
        def update_button_positions(event):
            fast_intersection_btn.move(vtk_frame.width() - 90, int(vtk_frame.height() / 2 - 120))
            face_quality_btn.move(vtk_frame.width() - 90, int(vtk_frame.height() / 2 - 85))
            face_prox_btn.move(vtk_frame.width() - 90, int(vtk_frame.height() / 2 - 50))
            free_edge_btn.move(vtk_frame.width() - 90, int(vtk_frame.height() / 2 - 15))
            overlap_edge_btn.move(vtk_frame.width() - 90, int(vtk_frame.height() / 2 + 20))  # 重叠边按钮在自由边按钮下方
            overlap_point_btn.move(vtk_frame.width() - 90, int(vtk_frame.height() / 2 + 55))  # 重叠点按钮位置下移
        
        vtk_frame.resizeEvent = update_button_positions
        
        # 将水平布局添加到右侧容器
        right_layout.addLayout(vtk_container, stretch=1)
        
        # 注意：自由边按钮已经添加到vtk_frame中，不需要再添加到btn_container
=======
        # 添加VTK窗口
        right_layout.addWidget(self.vtk_widget, stretch=1)
>>>>>>> 61808a0fd45044b397c6488dce73d9e755b79762
        
        # 创建状态指示器面板
        status_panel = QFrame()
        status_panel.setFrameStyle(QFrame.Panel | QFrame.Raised)
        status_panel.setMaximumHeight(40)
        status_layout = QHBoxLayout(status_panel)
        status_layout.setContentsMargins(10, 5, 10, 5)
        status_layout.setSpacing(20)
        
        # 创建状态指示器
        # 点状态
        point_status = QWidget()
        point_layout = QHBoxLayout(point_status)
        point_layout.setContentsMargins(5, 0, 5, 0)
        self.point_label = QLabel("点:")
        self.point_count = QLabel("0")
        point_clear = QPushButton("×")
        point_clear.setMaximumWidth(20)
        point_clear.clicked.connect(self.clear_points)
        point_layout.addWidget(self.point_label)
        point_layout.addWidget(self.point_count)
        point_layout.addWidget(point_clear)
        
        # 线状态
        edge_status = QWidget()
        edge_layout = QHBoxLayout(edge_status)
        edge_layout.setContentsMargins(5, 0, 5, 0)
        self.edge_label = QLabel("线:")
        self.edge_count = QLabel("0")
        edge_clear = QPushButton("×")
        edge_clear.setMaximumWidth(20)
        edge_clear.clicked.connect(self.clear_edges)
        edge_layout.addWidget(self.edge_label)
        edge_layout.addWidget(self.edge_count)
        edge_layout.addWidget(edge_clear)
        
        # 面状态
        face_status = QWidget()
        face_layout = QHBoxLayout(face_status)
        face_layout.setContentsMargins(5, 0, 5, 0)
        self.face_label = QLabel("面:")
        self.face_count = QLabel("0")
        face_clear = QPushButton("×")
        face_clear.setMaximumWidth(20)
        face_clear.clicked.connect(self.clear_faces)
        face_layout.addWidget(self.face_label)
        face_layout.addWidget(self.face_count)
        face_layout.addWidget(face_clear)
        
        # 添加状态指示器到状态面板
        status_layout.addStretch(1)
        status_layout.addWidget(point_status)
        status_layout.addWidget(edge_status)
        status_layout.addWidget(face_status)
        status_layout.addStretch(1)
        
        # 添加状态面板到右侧布局
        right_layout.addWidget(status_panel)
        
        # 添加一些底部空间
        spacer = QWidget()
        spacer.setMinimumHeight(20)
        right_layout.addWidget(spacer)
        
        # 添加到主布局
        content_layout.addWidget(control_panel)
        content_layout.addWidget(right_container)
        main_layout.addLayout(content_layout)
        
        # VTK相关初始化
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(1.0, 1.0, 1.0)
<<<<<<< HEAD
        
        # 获取渲染窗口并启用性能优化
        render_window = self.vtk_widget.GetRenderWindow()
        render_window.SetMultiSamples(0)  # 禁用多重采样以提高性能
        render_window.SetPointSmoothing(False)
        render_window.SetLineSmoothing(False)
        render_window.SetPolygonSmoothing(False)
        render_window.SetDoubleBuffer(True)  # 启用双缓冲
        
        # 启用硬件加速
        render_window.AddRenderer(self.renderer)
        self.iren = render_window.GetInteractor()
        
        # 设置交互器样式并优化相机操作
        style = vtk.vtkInteractorStyleTrackballCamera()
        style.SetMotionFactor(10.0)  # 增加相机移动速度
        style.SetAutoAdjustCameraClippingRange(True)  # 自动调整相机裁剪范围
        self.iren.SetInteractorStyle(style)
        
        # 设置渲染器的优化选项
        self.renderer.SetUseDepthPeeling(False)  # 禁用深度剥离
        self.renderer.SetUseFXAA(False)  # 禁用FXAA抗锯齿
        self.renderer.SetTwoSidedLighting(False)  # 禁用双面光照
        
=======
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.iren = self.vtk_widget.GetRenderWindow().GetInteractor()
        
        # 设置交互器样式
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(style)
        
>>>>>>> 61808a0fd45044b397c6488dce73d9e755b79762
        # 重新设置事件观察器
        self.iren.RemoveObservers("LeftButtonPressEvent")
        self.iren.RemoveObservers("MouseMoveEvent")
        self.iren.RemoveObservers("LeftButtonReleaseEvent")
        
        self.iren.AddObserver("LeftButtonPressEvent", self.on_left_button_press)
        self.iren.AddObserver("MouseMoveEvent", self.on_mouse_move)
        self.iren.AddObserver("LeftButtonReleaseEvent", self.on_left_button_release)
        
<<<<<<< HEAD
        # 设置交互器的性能优化选项
        self.iren.SetDesiredUpdateRate(30.0)  # 设置期望的更新率
        self.iren.SetStillUpdateRate(0.001)  # 静止时的更新率
        
=======
>>>>>>> 61808a0fd45044b397c6488dce73d9e755b79762
        # 初始化显示
        self.update_display()
        self.reset_camera()
        self.iren.Initialize()
        
        # 初始化选择模式
        self.selection_mode = 'point'
        self.selected_points = []  # 改用列表存储所有选中的点
        self.selected_edges = []
        self.selected_faces = []
        self.temp_points = []  # 仅用于创建面的临时点
    
    def set_selection_mode(self, mode):
        """设置选择模式"""
        self.selection_mode = mode
        
        # 更新按钮状态
        self.point_mode_btn.setChecked(mode == 'point')
        self.edge_mode_btn.setChecked(mode == 'edge')
        self.face_mode_btn.setChecked(mode == 'face')
        self.smart_mode_btn.setChecked(mode == 'smart')
    
    def on_left_button_press(self, obj, event):
        """处理鼠标左键按下事件"""
        self.left_button_down = True
        self.moved_since_press = False
        self.press_pos = self.iren.GetEventPosition()
        
        # 允许 VTK 继续处理事件
        self.iren.GetInteractorStyle().OnLeftButtonDown()
    
    def on_mouse_move(self, obj, event):
        """处理鼠标移动事件"""
        if self.left_button_down:
            current_pos = self.iren.GetEventPosition()
            if self.press_pos:
                dx = abs(current_pos[0] - self.press_pos[0])
                dy = abs(current_pos[1] - self.press_pos[1])
                if dx > 3 or dy > 3:
                    self.moved_since_press = True
        
        # 允许 VTK 继续处理事件
        self.iren.GetInteractorStyle().OnMouseMove()
    
    def on_left_button_release(self, obj, event):
        """处理鼠标左键释放事件"""
        if self.left_button_down and not self.moved_since_press:
            self.on_pick(obj, event)
        
        # 重置状态
        self.left_button_down = False
        self.moved_since_press = False
        self.press_pos = None
        
        # 允许 VTK 继续处理事件
        self.iren.GetInteractorStyle().OnLeftButtonUp()
    
    def on_pick(self, obj, event):
        """处理选择事件"""
        x, y = self.iren.GetEventPosition()
        
        # 获取点击位置的3D坐标
        self.cell_picker.Pick(x, y, 0, self.renderer)
        picked_position = np.array(self.cell_picker.GetPickPosition())
        cell_id = self.cell_picker.GetCellId()
        
        # 检查是否点击到任何对象
        hit_anything = False
        
        # 1. 首先检查是否点击到点（最高优先级）
        min_dist = float('inf')
        closest_point_id = -1
        
        for i, vertex in enumerate(self.mesh_data['vertices']):
            dist = np.linalg.norm(vertex - picked_position)
            if dist < min_dist:
                min_dist = dist
                closest_point_id = i
        
        # 如果足够接近某个点，且在点选择或智能选择模式下，优先选择点
        if min_dist < 2.0 and self.selection_mode in ['point', 'smart']:
            hit_anything = True
            if closest_point_id in self.selected_points:
                self.selected_points.remove(closest_point_id)
            else:
                self.selected_points.append(closest_point_id)
            
            vertex = self.mesh_data['vertices'][closest_point_id]
            self.statusBar.showMessage(
                f'选中点 {closest_point_id}: X={vertex[0]:.3f}, Y={vertex[1]:.3f}, Z={vertex[2]:.3f}'
            )
            self.update_display()
            return  # 如果选中了点，直接返回，不处理边和面
        
        # 2. 如果没有选中点，检查是否点击到边（次优先级）
        if cell_id != -1:
            cell = self.mesh.GetCell(cell_id)
            
            if cell and cell.GetNumberOfPoints() == 3:
                points = [self.mesh_data['vertices'][cell.GetPointId(i)] for i in range(3)]
                edges = [(cell.GetPointId(i), cell.GetPointId((i+1)%3)) for i in range(3)]
                
                min_edge_dist = float('inf')
                closest_edge = None
                
                for edge in edges:
                    p1 = self.mesh_data['vertices'][edge[0]]
                    p2 = self.mesh_data['vertices'][edge[1]]
                    
                    edge_vec = p2 - p1
                    edge_len = np.linalg.norm(edge_vec)
                    edge_dir = edge_vec / edge_len
                    
                    v = picked_position - p1
                    proj = np.dot(v, edge_dir)
                    
                    if 0 <= proj <= edge_len:
                        proj_point = p1 + proj * edge_dir
                        dist = np.linalg.norm(picked_position - proj_point)
                        
                        if dist < min_edge_dist:
                            min_edge_dist = dist
                            closest_edge = tuple(sorted([edge[0], edge[1]]))
                
                # 如果足够接近某条边，且在边选择或智能选择模式下
                if min_edge_dist < 2.0 and self.selection_mode in ['edge', 'smart']:
                    hit_anything = True
                    if closest_edge in self.selected_edges:
                        self.selected_edges.remove(closest_edge)
                    else:
                        self.selected_edges.append(closest_edge)
                    self.statusBar.showMessage(f'选中边: {closest_edge[0]}-{closest_edge[1]}')
                    self.update_display()
                    return  # 如果选中了边，直接返回，不处理面
                
                # 3. 如果没有选中点和边，且在面选择或智能选择模式下，选择面（最低优先级）
                elif self.selection_mode in ['face', 'smart']:
                    hit_anything = True
                    if cell_id in self.selected_faces:
                        self.selected_faces.remove(cell_id)
                    else:
                        self.selected_faces.append(cell_id)
                    self.statusBar.showMessage(f'选中面 {cell_id}')
        
        # 如果点击到空白区域，清除所有选择
        if not hit_anything:
            self.clear_all_selections()
            self.statusBar.showMessage('已清除所有选择')
        
        self.update_display()
    
    def create_point(self):
        """通过坐标创建点"""
        try:
            x = float(self.x_input.text() or '0.0')
            y = float(self.y_input.text() or '0.0')
            z = float(self.z_input.text() or '0.0')
            
            # 添加新点到顶点列表
            new_point = np.array([x, y, z])
            new_point_id = len(self.mesh_data['vertices'])
            self.mesh_data['vertices'] = np.vstack([self.mesh_data['vertices'], new_point])
            
            # 选中新创建的点
            self.selected_points.append(new_point_id)
            
            # 清空输入框
            self.x_input.clear()
            self.y_input.clear()
            self.z_input.clear()
            
            print(f"创建点: ({x}, {y}, {z})")
            self.statusBar.showMessage(f'创建新点: X={x:.3f}, Y={y:.3f}, Z={z:.3f}')
            self.update_display()
            
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的数值坐标")
    
    def create_vtk_mesh(self):
        """从网格数据创建VTK网格"""
        points = vtk.vtkPoints()
        for vertex in self.mesh_data['vertices']:
            points.InsertNextPoint(vertex)
        
        cells = vtk.vtkCellArray()
        for face in self.mesh_data['faces']:
            triangle = vtk.vtkTriangle()
            for i, vertex_id in enumerate(face):
                triangle.GetPointIds().SetId(i, int(vertex_id))
            cells.InsertNextCell(triangle)
        
        mesh = vtk.vtkPolyData()
        mesh.SetPoints(points)
        mesh.SetPolys(cells)
        mesh.Modified()
        
        # 保存网格引用
        self.mesh = mesh
        
        return mesh
    
    def update_status_counts(self):
        """更新状态计数"""
        self.point_count.setText(str(len(self.selected_points)))
        self.edge_count.setText(str(len(self.selected_edges)))
        self.face_count.setText(str(len(self.selected_faces)))

    def update_display(self):
        """更新显示"""
        self.renderer.RemoveAllViewProps()
        
        # 保存当前相机状态
        camera = self.renderer.GetActiveCamera()
        old_position = camera.GetPosition()
        old_focal_point = camera.GetFocalPoint()
        old_view_up = camera.GetViewUp()
        
        # 创建基础网格
        mesh = self.create_vtk_mesh()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(mesh)
        mapper.Update()
        
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.8, 0.8, 0.8)  # 浅灰色
        actor.GetProperty().SetEdgeVisibility(True)
        actor.GetProperty().SetLineWidth(1.0)
        
        self.renderer.AddActor(actor)
        
        # 显示选中的面
        if self.selected_faces:
            selected_mesh = vtk.vtkPolyData()
            selected_mesh.SetPoints(mesh.GetPoints())
            
            selected_cells = vtk.vtkCellArray()
            for face_id in self.selected_faces:
                selected_cells.InsertNextCell(mesh.GetCell(face_id))
            
            selected_mesh.SetPolys(selected_cells)
            
            selected_mapper = vtk.vtkPolyDataMapper()
            selected_mapper.SetInputData(selected_mesh)
            selected_mapper.SetResolveCoincidentTopologyToPolygonOffset()
            selected_mapper.SetResolveCoincidentTopologyPolygonOffsetParameters(1.0, 1.0)
            
            selected_actor = vtk.vtkActor()
            selected_actor.SetMapper(selected_mapper)
            selected_actor.GetProperty().SetColor(1.0, 0.0, 0.0)  # 红色
            selected_actor.GetProperty().SetOpacity(1.0)
            selected_actor.GetProperty().SetLineWidth(2.0)
            selected_actor.GetProperty().SetEdgeVisibility(True)
            
            self.renderer.AddActor(selected_actor)
        
        # 显示选中的边
        if self.selected_edges:
            edge_points = vtk.vtkPoints()
            edge_lines = vtk.vtkCellArray()
            
            for i, (p1_id, p2_id) in enumerate(self.selected_edges):
                edge_points.InsertNextPoint(self.mesh_data['vertices'][p1_id])
                edge_points.InsertNextPoint(self.mesh_data['vertices'][p2_id])
                
                line = vtk.vtkLine()
                line.GetPointIds().SetId(0, i*2)
                line.GetPointIds().SetId(1, i*2+1)
                edge_lines.InsertNextCell(line)
            
            edge_data = vtk.vtkPolyData()
            edge_data.SetPoints(edge_points)
            edge_data.SetLines(edge_lines)
            
            edge_mapper = vtk.vtkPolyDataMapper()
            edge_mapper.SetInputData(edge_data)
            
            edge_actor = vtk.vtkActor()
            edge_actor.SetMapper(edge_mapper)
            edge_actor.GetProperty().SetColor(0.0, 1.0, 0.0)  # 绿色
            edge_actor.GetProperty().SetLineWidth(3.0)
            edge_actor.GetProperty().SetRenderLinesAsTubes(True)
            
            self.renderer.AddActor(edge_actor)
        
        # 显示所有点
        for i, point in enumerate(self.mesh_data['vertices']):
            sphere = vtk.vtkSphereSource()
            sphere.SetCenter(point)
            sphere.SetRadius(0.5)
            sphere.SetPhiResolution(16)
            sphere.SetThetaResolution(16)
            
            sphereMapper = vtk.vtkPolyDataMapper()
            sphereMapper.SetInputConnection(sphere.GetOutputPort())
            
            sphereActor = vtk.vtkActor()
            sphereActor.SetMapper(sphereMapper)
            
            if i in self.selected_points:
                sphereActor.GetProperty().SetColor(1.0, 0.0, 0.0)  # 红色
                sphereActor.GetProperty().SetOpacity(1.0)
            else:
                sphereActor.GetProperty().SetColor(0.3, 0.3, 0.3)  # 深灰色
                sphereActor.GetProperty().SetOpacity(0.8)
            
            # 确保点始终显示在最前面
            sphereActor.GetProperty().SetAmbient(1.0)
            sphereActor.GetProperty().SetDiffuse(0.0)
            sphereActor.GetProperty().SetSpecular(0.0)
            
            self.renderer.AddActor(sphereActor)
        
        # 更新状态计数
        self.update_status_counts()
        
        # 恢复相机状态（仅在第一次渲染时重置相机）
        if hasattr(self, '_first_render'):
            camera.SetPosition(old_position)
            camera.SetFocalPoint(old_focal_point)
            camera.SetViewUp(old_view_up)
        else:
            self.renderer.ResetCamera()
            self._first_render = True
        
        # 设置渲染器属性
        self.renderer.GetRenderWindow().SetMultiSamples(8)  # 启用抗锯齿
        self.vtk_widget.GetRenderWindow().Render()
    
    def delete_selected_faces(self):
        """删除选中的面"""
        if not self.selected_faces:
            print("没有选中的面可删除")
            return
        
<<<<<<< HEAD
        # 创建面片的mask
        face_mask = np.ones(len(self.mesh_data['faces']), dtype=bool)
        face_mask[self.selected_faces] = False
        
        # 更新面片数组
        self.mesh_data['faces'] = self.mesh_data['faces'][face_mask]
        
        # 如果存在法向量，重新计算顶点法向量
        if 'normals' in self.mesh_data:
            # 对于球体，法向量就是归一化的顶点坐标
            self.mesh_data['normals'] = self.mesh_data['vertices'] / np.linalg.norm(self.mesh_data['vertices'], axis=1)[:, np.newaxis]
=======
        mask = np.ones(len(self.mesh_data['faces']), dtype=bool)
        mask[self.selected_faces] = False
        
        self.mesh_data['faces'] = self.mesh_data['faces'][mask]
        if 'normals' in self.mesh_data:
            self.mesh_data['normals'] = self.mesh_data['normals'][mask]
>>>>>>> 61808a0fd45044b397c6488dce73d9e755b79762
        
        self.selected_faces = []
        print("已删除选中的面")
        self.update_display()
    
    def create_face(self):
        """从选中的点创建面"""
        if len(self.selected_points) != 3:
            QMessageBox.warning(self, '创建面', '需要选择3个点才能创建面')
            return
        
        # 使用选中的点创建新面
        new_face = np.array([self.selected_points])  # 创建新的面数组
        self.mesh_data['faces'] = np.vstack([self.mesh_data['faces'], new_face])  # 垂直堆叠数组
        
        # 清除选中的点
        self.selected_points = []
        
        # 更新显示
        self.update_display()
        print(f"创建了新面: {new_face}")
    
    def clear_selection(self):
        """清除所有选择"""
        self.selected_points = []
        self.selected_edges = []
        self.selected_faces = []
        self.update_display()
        print("已清除选择")
    
    def clear_points(self):
        """清除选中的点"""
        self.selected_points = []
        self.update_display()
    
    def clear_edges(self):
        """清除选中的边"""
        self.selected_edges = []
        self.update_display()
    
    def clear_faces(self):
        """清除选中的面"""
        self.selected_faces = []
        self.update_display()
    
    def reset_camera(self):
        """重置相机位置以显示整个模型"""
        self.renderer.ResetCamera()
        camera = self.renderer.GetActiveCamera()
        
        # 获取模型的边界框
        bounds = self.mesh.GetBounds()
        center = [(bounds[1] + bounds[0])/2, 
                 (bounds[3] + bounds[2])/2, 
                 (bounds[5] + bounds[4])/2]
        
        # 计算合适的相机距离
        diagonal = np.sqrt((bounds[1]-bounds[0])**2 + 
                          (bounds[3]-bounds[2])**2 + 
                          (bounds[5]-bounds[4])**2)
        camera.SetPosition(center[0], center[1], center[2] + diagonal)
        camera.SetFocalPoint(center[0], center[1], center[2])
        camera.SetViewUp(0, 1, 0)
        
        self.renderer.ResetCameraClippingRange()
        self.vtk_widget.GetRenderWindow().Render()
    
    def clear_all_selections(self):
        """清除所有选择"""
        self.selected_points = []
        self.selected_edges = []
        self.selected_faces = []
        self.update_display()
<<<<<<< HEAD
        print("已清除所有选择") 

    def select_free_edges(self):
        """选择自由边"""
        # 获取所有边的端点
        edges = set()  # 使用集合来存储边，每条边由两个端点的元组表示
        edge_count = {}  # 用字典记录每条边出现的次数
        
        # 遍历所有面片，收集边信息
        for face in self.mesh_data['faces']:
            # 获取面片的三条边
            edge1 = tuple(sorted([face[0], face[1]]))
            edge2 = tuple(sorted([face[1], face[2]]))
            edge3 = tuple(sorted([face[2], face[0]]))
            
            # 更新边的计数
            edge_count[edge1] = edge_count.get(edge1, 0) + 1
            edge_count[edge2] = edge_count.get(edge2, 0) + 1
            edge_count[edge3] = edge_count.get(edge3, 0) + 1
        
        # 找出只出现一次的边（自由边）
        free_edges = [edge for edge, count in edge_count.items() if count == 1]
        
        # 清除之前的选择
        self.selected_edges = []
        
        # 添加自由边到选择列表
        self.selected_edges.extend(free_edges)
        
        # 更新显示
        self.update_display()
        
        # 更新状态栏显示
        self.edge_count.setText(str(len(self.selected_edges)))
        self.statusBar.showMessage(f'已选择 {len(self.selected_edges)} 条自由边')

    def select_overlapping_edges(self):
        """检测并选择重叠边"""
        # 清除之前的选择
        self.clear_selection()
        
        # 获取所有边的端点
        edges = {}
        for face in self.mesh_data['faces']:
            for i in range(len(face)):
                # 获取边的两个端点
                p1 = face[i]
                p2 = face[(i + 1) % len(face)]
                
                # 确保边的方向一致（较小的点索引在前）
                edge = tuple(sorted([p1, p2]))
                
                # 记录边的出现次数
                if edge in edges:
                    edges[edge] += 1
                else:
                    edges[edge] = 1
        
        # 找出重叠边（出现次数大于2的边）
        overlapping_edges = [edge for edge, count in edges.items() if count > 2]
        
        # 选择重叠边
        self.selected_edges = overlapping_edges
        
        # 更新显示
        self.update_display()
        
        # 更新状态栏显示
        self.edge_count.setText(str(len(self.selected_edges)))
        self.statusBar.showMessage(f'找到 {len(self.selected_edges)} 条重叠边')

    def create_octree(self, faces, vertices, max_depth=10, min_faces=10):
        """创建八叉树空间分区"""
        # 计算所有面片的包围盒
        face_vertices = vertices[faces]
        min_bounds = np.min(face_vertices.reshape(-1, 3), axis=0)
        max_bounds = np.max(face_vertices.reshape(-1, 3), axis=0)
        center = (min_bounds + max_bounds) / 2
        size = max(max_bounds - min_bounds) * 1.01  # 稍微扩大一点以确保包含所有面片

        class OctreeNode:
            def __init__(self, center, size, depth):
                self.center = center
                self.size = size
                self.depth = depth
                self.faces = []
                self.children = None

            def get_octant(self, point):
                """确定点属于哪个八分区"""
                return ((point[0] > self.center[0]) << 2 |
                        (point[1] > self.center[1]) << 1 |
                        (point[2] > self.center[2]))

        def build_octree(node, face_indices):
            if len(face_indices) <= min_faces or node.depth >= max_depth:
                node.faces = face_indices
                return

            # 创建子节点
            node.children = [None] * 8
            child_faces = [[] for _ in range(8)]
            half_size = node.size / 2

            # 分配面片到子节点
            for face_idx in face_indices:
                face_center = np.mean(vertices[faces[face_idx]], axis=0)
                octant = node.get_octant(face_center)
                child_faces[octant].append(face_idx)

            # 递归构建子节点
            for i in range(8):
                if child_faces[i]:
                    offset = np.array([(i & 4) > 0, (i & 2) > 0, (i & 1) > 0]) * half_size - half_size/2
                    child_center = node.center + offset
                    node.children[i] = OctreeNode(child_center, half_size, node.depth + 1)
                    build_octree(node.children[i], child_faces[i])

        # 创建根节点并构建八叉树
        root = OctreeNode(center, size, 0)
        build_octree(root, list(range(len(faces))))
        return root

    def check_triangle_intersection(self, tri1_verts, tri2_verts):
        """优化的分离轴定理(SAT)检查两个三角形是否相交"""
        # 快速共面检测 - 如果两个三角形近似共面且不重叠，可以快速排除
        def get_normal(tri):
            v1 = tri[1] - tri[0]
            v2 = tri[2] - tri[0]
            normal = np.cross(v1, v2)
            norm = np.linalg.norm(normal)
            if norm < 1e-10:  # 处理退化三角形
                return np.zeros(3)
            return normal / norm
        
        # 获取三角形的边
        def get_edges(tri):
            return [tri[1] - tri[0], tri[2] - tri[1], tri[0] - tri[2]]
        
        # 投影三角形到轴上
        def project_triangle(tri, axis):
            dots = [np.dot(v, axis) for v in tri]
            return min(dots), max(dots)
        
        # 检查在给定轴上是否分离
        def check_separation(tri1, tri2, axis):
            if np.all(np.abs(axis) < 1e-10):  # 避免零向量
                return False
            p1_min, p1_max = project_triangle(tri1, axis)
            p2_min, p2_max = project_triangle(tri2, axis)
            return p1_max < p2_min or p2_max < p1_min
        
        # 1. 检查面法向量轴
        normal1 = get_normal(tri1_verts)
        normal2 = get_normal(tri2_verts)
        
        if not np.all(np.abs(normal1) < 1e-10) and check_separation(tri1_verts, tri2_verts, normal1):
            return False
        
        if not np.all(np.abs(normal2) < 1e-10) and check_separation(tri1_verts, tri2_verts, normal2):
            return False
        
        # 2. 检查边叉积轴
        edges1 = get_edges(tri1_verts)
        edges2 = get_edges(tri2_verts)
        
        for e1 in edges1:
            for e2 in edges2:
                cross = np.cross(e1, e2)
                if np.any(np.abs(cross) > 1e-10):  # 避免接近零的叉积
                    axis = cross / np.linalg.norm(cross)
                    if check_separation(tri1_verts, tri2_verts, axis):
                        return False
        
        # 没有找到分离轴，三角形相交
        return True

    def detect_face_intersections(self):
        """使用八叉树空间分区优化的相交面检测算法"""
        if not self.mesh_data['faces'].size:
            QMessageBox.warning(self, '警告', '没有可分析的面片')
            return

        # 清除之前的选择
        self.clear_all_selections()

        # 获取所有面片的顶点坐标
        faces = self.mesh_data['faces']
        vertices = self.mesh_data['vertices']
        
        # 计算每个面片的AABB包围盒和中心点
        face_bboxes = []
        face_centers = []
        for face_idx in range(len(faces)):
            face_verts = vertices[faces[face_idx]]
            min_coords = np.min(face_verts, axis=0)
            max_coords = np.max(face_verts, axis=0)
            face_bboxes.append((min_coords, max_coords))
            face_centers.append(np.mean(face_verts, axis=0))
        
        # 创建八叉树进行空间分区
        octree = self.create_octree(faces, vertices, max_depth=8, min_faces=20)
        
        # 用于存储相交的面片
        intersecting_faces = set()
        
        # 创建进度对话框
        total_faces = len(faces)
        progress = QProgressDialog("检测相交面...", "取消", 0, total_faces, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        
        # 用于提前终止的标志
        cancelled = False
        
        # 递归查询八叉树
        def query_octree(node, face_idx):
            nonlocal cancelled
            
            # 检查是否取消
            if progress.wasCanceled():
                cancelled = True
                return
            
            # 如果节点为空，直接返回
            if not node or cancelled:
                return
            
            # 如果节点是叶子节点，检查所有面片
            if not node.children:
                face1_verts = vertices[faces[face_idx]]
                min1, max1 = face_bboxes[face_idx]
                
                for other_idx in node.faces:
                    # 跳过自身
                    if other_idx == face_idx:
                        continue
                    
                    # 快速AABB包围盒检测
                    min2, max2 = face_bboxes[other_idx]
                    if np.all(max1 >= min2) and np.all(max2 >= min1):
                        face2_verts = vertices[faces[other_idx]]
                        # 只有当两个面片不共享顶点时才检查相交
                        if not set(faces[face_idx]).intersection(set(faces[other_idx])):
                            if self.check_triangle_intersection(face1_verts, face2_verts):
                                intersecting_faces.add(face_idx)
                                intersecting_faces.add(other_idx)
                return
            
            # 否则，递归查询子节点
            face_min, face_max = face_bboxes[face_idx]
            for i, child in enumerate(node.children):
                if child:
                    # 计算子节点的包围盒
                    half_size = child.size / 2
                    child_min = child.center - half_size
                    child_max = child.center + half_size
                    
                    # 检查面片的包围盒是否与子节点的包围盒相交
                    if np.all(face_max >= child_min) and np.all(child_max >= face_min):
                        query_octree(child, face_idx)
        
        try:
            # 对每个面片，在八叉树中查询可能相交的面片
            for face_idx in range(total_faces):
                if cancelled:
                    break
                
                # 在八叉树中查询
                query_octree(octree, face_idx)
                
                # 更新进度
                progress.setValue(face_idx + 1)
                QApplication.processEvents()  # 确保UI响应
            
            # 更新选中的面片
            self.selected_faces = list(intersecting_faces)
            
            # 更新显示
            self.update_display()
            
            # 更新状态栏信息
            if cancelled:
                self.statusBar.showMessage('交叉面检测已取消')
            elif self.selected_faces:
                self.statusBar.showMessage(f'检测到 {len(self.selected_faces)} 个相交面片')
            else:
                self.statusBar.showMessage('未检测到相交面片')
                
        finally:
            progress.close()


    def analyze_face_quality(self):
        """分析面片质量"""
        import numpy as np
        from vtk.util.numpy_support import numpy_to_vtk

        # 创建面片质量数组
        face_quality = np.zeros(len(self.mesh_data['faces']))
        vertices = self.mesh_data['vertices']

        # 遍历所有面片计算质量指标
        for i, face in enumerate(self.mesh_data['faces']):
            # 获取面片的三个顶点
            v1 = vertices[face[0]]
            v2 = vertices[face[1]]
            v3 = vertices[face[2]]

            # 计算边长
            e1 = np.linalg.norm(v2 - v1)
            e2 = np.linalg.norm(v3 - v2)
            e3 = np.linalg.norm(v1 - v3)

            # 计算面积
            s = (e1 + e2 + e3) / 2  # 半周长
            area = np.sqrt(s * (s - e1) * (s - e2) * (s - e3))  # 海伦公式

            # 计算纵横比（最长边与最短边的比值）
            aspect_ratio = max(e1, e2, e3) / min(e1, e2, e3)

            # 计算扭曲度（最小角度与60度的偏差）
            v12 = v2 - v1
            v23 = v3 - v2
            v31 = v1 - v3
            angle1 = np.arccos(np.dot(-v31, v12) / (np.linalg.norm(v31) * np.linalg.norm(v12)))
            angle2 = np.arccos(np.dot(-v12, v23) / (np.linalg.norm(v12) * np.linalg.norm(v23)))
            angle3 = np.arccos(np.dot(-v23, v31) / (np.linalg.norm(v23) * np.linalg.norm(v31)))
            min_angle = min(angle1, angle2, angle3)
            skewness = abs(min_angle - np.pi/3) / (np.pi/3)

            # 综合质量评分（0-1之间，1为最好）
            quality = 1.0 / (1.0 + aspect_ratio + skewness)
            face_quality[i] = quality

        # 创建颜色映射
        colors = vtk.vtkUnsignedCharArray()
        colors.SetNumberOfComponents(3)
        colors.SetName('Colors')

        # 设置颜色范围（红色到绿色）
        for q in face_quality:
            if q > 0.8:  # 高质量（绿色）
                colors.InsertNextTuple3(0, 255, 0)
            elif q > 0.5:  # 中等质量（黄色）
                colors.InsertNextTuple3(255, 255, 0)
            else:  # 低质量（红色）
                colors.InsertNextTuple3(255, 0, 0)

        # 更新网格显示
        self.mesh.GetCellData().SetScalars(colors)
        self.vtk_widget.GetRenderWindow().Render()

        # 显示统计信息
        high_quality = np.sum(face_quality > 0.8)
        medium_quality = np.sum((face_quality <= 0.8) & (face_quality > 0.5))
        low_quality = np.sum(face_quality <= 0.5)
        total_faces = len(face_quality)

        quality_info = f'面片质量分析结果:\n'
        quality_info += f'高质量面片（绿色）: {high_quality} ({high_quality/total_faces*100:.1f}%)\n'
        quality_info += f'中等质量面片（黄色）: {medium_quality} ({medium_quality/total_faces*100:.1f}%)\n'
        quality_info += f'低质量面片（红色）: {low_quality} ({low_quality/total_faces*100:.1f}%)'

        QMessageBox.information(self, '面片质量分析', quality_info)

    def select_adjacent_faces(self):
        """选择与当前选中面片相邻的所有面片"""
        if not self.selected_faces:
            self.statusBar.showMessage('请先选择一个面片')
            return

        # 创建面片邻接关系字典
        face_adjacency = {}
        for i, face1 in enumerate(self.mesh_data['faces']):
            face_adjacency[i] = set()
            # 获取当前面片的三条边
            edges1 = [
                tuple(sorted([face1[j], face1[(j+1)%3]]))
                for j in range(3)
            ]
            
            # 检查其他面片是否与当前面片共享边
            for j, face2 in enumerate(self.mesh_data['faces']):
                if i != j:
                    edges2 = [
                        tuple(sorted([face2[k], face2[(k+1)%3]]))
                        for k in range(3)
                    ]
                    # 如果两个面片共享至少一条边，则它们相邻
                    if any(edge in edges2 for edge in edges1):
                        face_adjacency[i].add(j)

        # 获取所有相邻面片
        adjacent_faces = set()
        for face_id in self.selected_faces:
            if face_id in face_adjacency:
                adjacent_faces.update(face_adjacency[face_id])

        # 更新选中的面片（添加相邻面片）
        self.selected_faces = list(set(self.selected_faces) | adjacent_faces)

        # 更新状态栏信息
        self.statusBar.showMessage(f'已选择 {len(self.selected_faces)} 个面片')

        # 更新显示
        self.update_display()
        
    def select_overlapping_points(self):
        """检测并选择重叠点
        重叠点的定义：当一个点连接的自由边数量为4或更大的偶数时，该点被认为是重叠点
        """
        # 清除之前的选择
        self.clear_selection()
        
        # 获取所有面和顶点
        faces = self.mesh_data['faces']
        vertices = self.mesh_data['vertices']
        
        # 创建进度对话框
        progress = QProgressDialog("检测重叠点...", "取消", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        progress.setValue(10)
        
        try:
            # 用于存储每个点连接的边
            point_edges = {i: [] for i in range(len(vertices))}
            
            # 用于存储边的出现次数
            edge_count = {}
            
            # 统计所有边的出现次数
            progress.setValue(30)
            for face in faces:
                for i in range(len(face)):
                    # 获取边的两个端点（按较小的点索引在前排序）
                    p1, p2 = sorted([face[i], face[(i + 1) % len(face)]])
                    edge = (p1, p2)
                    edge_count[edge] = edge_count.get(edge, 0) + 1
                    
                    # 记录每个点连接的边
                    point_edges[p1].append(edge)
                    point_edges[p2].append(edge)
            
            # 找出自由边（只出现一次的边）
            progress.setValue(60)
            free_edges = {edge for edge, count in edge_count.items() if count == 1}
            
            # 检查每个点连接的自由边数量
            overlapping_points = set()
            progress.setValue(80)
            
            for point_idx, edges in point_edges.items():
                if progress.wasCanceled():
                    break
                    
                # 计算与该点相连的自由边数量
                free_edge_count = sum(1 for edge in edges if edge in free_edges)
                
                # 如果自由边数量大于等于4且为偶数，则认为是重叠点
                if free_edge_count >= 4 and free_edge_count % 2 == 0:
                    overlapping_points.add(point_idx)
            
            # 更新选中的点
            self.selected_points = list(overlapping_points)
            
            # 更新显示
            progress.setValue(100)
            self.update_display()
            
            # 更新状态栏
            if progress.wasCanceled():
                self.statusBar.showMessage('重叠点检测已取消')
            elif len(overlapping_points) > 0:
                self.statusBar.showMessage(f'找到 {len(overlapping_points)} 个重叠点')
            else:
                self.statusBar.showMessage('未找到重叠点')
                
        finally:
            progress.close()
=======
        print("已清除所有选择") 
>>>>>>> 61808a0fd45044b397c6488dce73d9e755b79762
