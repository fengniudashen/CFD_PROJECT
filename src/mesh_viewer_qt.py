import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QFrame, QLabel, QLineEdit,
                           QGridLayout, QMessageBox, QStatusBar, QProgressDialog, QInputDialog,
                           QTabWidget, QShortcut, QMenu, QAction, QRadioButton, QCheckBox)
from PyQt5.QtGui import QFont, QIcon, QPainter, QPen, QColor, QPixmap, QImage, qRgb, QCursor
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtkmodules.all as vtk
from typing import Dict
import time
import gc  # 用于垃圾回收
from PyQt5.QtGui import QKeySequence
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import traceback

# 导入算法包中的所有算法
from algorithms import (
    BaseAlgorithm, AlgorithmUtils, FreeEdgesAlgorithm, OverlappingEdgesAlgorithm,
    FaceQualityAlgorithm, CombinedIntersectionAlgorithm, MergedVertexDetectionAlgorithm
)

try:
    import non_manifold_vertices_cpp
    HAS_NON_MANIFOLD_VERTICES_CPP = True
    print("已加载非流形顶点检测C++模块")
except ImportError:
    HAS_NON_MANIFOLD_VERTICES_CPP = False
    print("未找到非流形顶点检测C++模块，将使用Python实现")

# 添加导入model_change_tracker模块
from model_change_tracker import ModelChangeTracker

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
        """初始化Qt Mesh Viewer"""
        super().__init__()
        
        # 初始化成员变量
        self.mesh_data = mesh_data
        self.selected_points = []
        self.selected_edges = []
        self.selected_faces = []
        self.temp_points = []
        self.selection_mode = 'smart'
        
        # 面相交关系映射 - 储存每个面与哪些面相交
        self.face_intersection_map = {}
        
        # 添加切换按钮的初始化
        self.toggle_buttons = []
        self.toggle_states = [False] * 6  # 存储6个切换按钮的状态
        
        # 添加导航按钮的初始化
        self.nav_buttons = []
        
        # 添加新功能按钮的初始化
        self.function_buttons = []
        self.function_button_states = [False, False]  # 记录两个按钮的状态
        
        # 添加拖动状态跟踪
        self.left_button_down = False
        self.moved_since_press = False
        self.press_pos = None
        
        # 性能优化：添加帧率控制
        self.fps_timer = QTimer(self)
        self.fps_timer.setInterval(33)  # 约30fps
        self.fps_timer.timeout.connect(self.on_fps_timer)
        self.is_interacting = False
        self.needs_high_res_render = True
        
        # 性能优化：点显示缓存
        self.point_glyph_source = None
        self.cached_mesh = None
        self.last_selection_state = None
        
        # 性能优化：自适应LOD（细节层次）控制
        self.large_model_threshold = 50000  # 面片数量阈值
        self.point_threshold = 1000  # 点数量阈值
        self.is_large_model = False  # 是否是大模型
        
        # 性能模式切换
        self.high_performance_mode = True  # 默认使用高性能模式
        
        # 添加检测按钮缓存结果字典
        self.detection_cache = {
            'face_intersections': None,  # 交叉面
            'face_intersection_map': None,  # 交叉面关系映射
            'face_quality': None,        # 面质量 
            'adjacent_faces': None,      # 相邻面
            'free_edges': None,          # 自由边
            'overlapping_edges': None,   # 重叠边
            'overlapping_points': None   # 重叠点
        }
        # 用于追踪模型是否发生变化的标记
        self.model_modified = False
        
        # 初始化模型变更追踪器
        self.model_tracker = ModelChangeTracker(self)
        
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
        
        # 存储视图
        self.views = {}  # 存储的视图
        self.view_counter = 0  # 视图计数器
        
        # 检查C++扩展模块是否可用
        self.has_cpp_extensions = self.check_cpp_extensions()
        
        # 初始化UI
        self.initUI()
        
        # 显示状态栏信息
        if not self.has_cpp_extensions:
            self.statusBar.showMessage("提示: 安装C++模块可显著提高性能")
        
        # 缓存和标志
        self.cached_mesh = None
        self.needs_high_res_render = False
        self.is_interacting = False
        self.is_large_model = len(mesh_data['vertices']) > 5000
        
        # 初始化选中和状态
        self.selection_mode = 'smart'
        self.selected_points = []
        self.selected_edges = []
        self.selected_faces = []
        self.edge_selection_source = 'manual'  # 新增边选择来源标志: 'manual' 表示手动选择，'auto' 表示按钮自动选择
    
    def check_cpp_extensions(self):
        """检查C++扩展模块是否可用"""
        cpp_modules_available = True
        
        # 检查各个C++扩展模块
        try:
            import self_intersection_cpp
            print("已加载 self_intersection_cpp 模块")
        except ImportError:
            cpp_modules_available = False
            print("未找到 self_intersection_cpp 模块")
            
        try:
            import pierced_faces_cpp
            # 检查是否为新版模块(支持相交映射)
            try:
                # 使用一个极小的测试网格测试新功能
                test_verts = np.array([[0,0,0],[1,0,0],[0,1,0]], dtype=np.float64)
                test_faces = np.array([[0,1,2]], dtype=np.int32)
                _, test_map, _ = pierced_faces_cpp.detect_pierced_faces_with_timing(test_faces, test_verts)
                print("已加载增强版 pierced_faces_cpp 模块 (支持相交映射)")
                self.has_enhanced_pierced_faces = True
            except ValueError:
                print("已加载基础版 pierced_faces_cpp 模块 (不支持相交映射)")
                self.has_enhanced_pierced_faces = False
        except ImportError:
            cpp_modules_available = False
            self.has_enhanced_pierced_faces = False
            print("未找到 pierced_faces_cpp 模块")
            
        try:
            import non_manifold_vertices_cpp
            print("已加载 non_manifold_vertices_cpp 模块")
        except ImportError:
            cpp_modules_available = False
            print("未找到 non_manifold_vertices_cpp 模块")
            
        try:
            import overlapping_points_cpp
            print("已加载 overlapping_points_cpp 模块")
        except ImportError:
            cpp_modules_available = False
            # 静默失败，不打印信息
            
        try:
            import face_quality_cpp
            print("已加载 face_quality_cpp 模块")
        except ImportError:
            cpp_modules_available = False
            print("未找到 face_quality_cpp 模块")
        
        return cpp_modules_available
    
    def initUI(self):
        """初始化UI"""
        # 设置窗口标题，包含性能模式信息
        mode_name = "高性能模式" if self.high_performance_mode else "高质量模式"
        self.setWindowTitle(f'Mesh Viewer - {mode_name}')
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(main_widget)
        
        # 创建顶部按钮栏
        top_button_bar = QFrame()
        top_button_bar.setFrameStyle(QFrame.Panel | QFrame.Raised)
        top_button_bar.setMaximumHeight(40)
        top_button_layout = QHBoxLayout(top_button_bar)
        top_button_layout.setContentsMargins(5, 5, 5, 5)
        top_button_layout.setSpacing(0)  # 将间距设为0，让按钮紧挨在一起
        top_button_layout.addStretch(1)  # 添加弹性空间，将按钮靠右对齐
        
        # 创建27个按钮
        for i in range(1, 28):
            btn = QPushButton(str(i))
            btn.setFixedSize(40, 30)  # 设置按钮大小
            btn.setStyleSheet("""
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
            
            # 为按钮1添加特殊功能
            if i == 1:
                # 创建重置视图图标
                reset_icon = QIcon()
                reset_pixmap = QPixmap(32, 32)
                reset_pixmap.fill(Qt.transparent)
                reset_painter = QPainter(reset_pixmap)
                reset_painter.setRenderHint(QPainter.Antialiasing)
                
                # 绘制四个方向的箭头
                reset_pen = QPen(QColor(0, 0, 0))
                reset_pen.setWidth(2)
                reset_painter.setPen(reset_pen)
                
                # 绘制左上箭头
                reset_painter.drawLine(8, 8, 16, 16)  # 主线段
                reset_painter.drawLine(8, 8, 12, 8)   # 上箭头
                reset_painter.drawLine(8, 8, 8, 12)   # 左箭头
                
                # 绘制右上箭头
                reset_painter.drawLine(24, 8, 16, 16)  # 主线段
                reset_painter.drawLine(24, 8, 20, 8)   # 上箭头
                reset_painter.drawLine(24, 8, 24, 12)  # 右箭头
                
                # 绘制左下箭头
                reset_painter.drawLine(8, 24, 16, 16)  # 主线段
                reset_painter.drawLine(8, 24, 12, 24)  # 下箭头
                reset_painter.drawLine(8, 24, 8, 20)   # 左箭头
                
                # 绘制右下箭头
                reset_painter.drawLine(24, 24, 16, 16)  # 主线段
                reset_painter.drawLine(24, 24, 20, 24)  # 下箭头
                reset_painter.drawLine(24, 24, 24, 20)  # 右箭头
                
                reset_painter.end()
                reset_icon.addPixmap(reset_pixmap)
                
                # 设置按钮属性
                btn.setIcon(reset_icon)
                btn.setIconSize(QSize(20, 20))
                btn.setToolTip("重置视图")
                btn.clicked.connect(self.reset_camera)
            
            # 为按钮2添加相机图标和下拉菜单
            elif i == 2:
                # 创建相机图标
                camera_icon = QIcon()
                camera_pixmap = QPixmap(32, 32)
                camera_pixmap.fill(Qt.transparent)
                camera_painter = QPainter(camera_pixmap)
                camera_painter.setRenderHint(QPainter.Antialiasing)
                
                # 绘制相机主体
                camera_pen = QPen(QColor(0, 0, 0))
                camera_pen.setWidth(2)
                camera_painter.setPen(camera_pen)
                
                # 绘制相机主体（矩形）
                camera_painter.drawRect(8, 8, 16, 12)
                
                # 绘制镜头（圆形）
                camera_painter.drawEllipse(12, 10, 8, 8)
                
                # 绘制闪光灯（小矩形）
                camera_painter.drawRect(20, 6, 4, 2)
                
                camera_painter.end()
                camera_icon.addPixmap(camera_pixmap)
                
                # 设置按钮属性
                btn.setIcon(camera_icon)
                btn.setIconSize(QSize(20, 20))
                btn.setToolTip("视图选项")
                
                # 创建下拉菜单
                view_menu = QMenu(btn)
                
                # 添加菜单项
                store_view_action = view_menu.addAction("Store Current View")
                restore_view_menu = view_menu.addMenu("Restore View")
                view_menu.addSeparator()
                projection_menu = view_menu.addMenu("Projection Mode")
                view_menu.addSeparator()
                view_menu.addAction("View")
                standard_views_menu = view_menu.addMenu("Standard Views")
                view_menu.addSeparator()
                view_menu.addAction("View Coordinate System")
                
                # 添加投影模式子菜单
                perspective_action = projection_menu.addAction("Perspective")
                parallel_action = projection_menu.addAction("Parallel")
                
                # 添加标准视图子菜单
                front_action = standard_views_menu.addAction("Front")
                back_action = standard_views_menu.addAction("Back")
                left_action = standard_views_menu.addAction("Left")
                right_action = standard_views_menu.addAction("Right")
                top_action = standard_views_menu.addAction("Top")
                bottom_action = standard_views_menu.addAction("Bottom")
                isometric_action = standard_views_menu.addAction("Isometric")
                
                # 连接标准视图菜单项信号
                front_action.triggered.connect(lambda: self.set_standard_view("front"))
                back_action.triggered.connect(lambda: self.set_standard_view("back"))
                left_action.triggered.connect(lambda: self.set_standard_view("left"))
                right_action.triggered.connect(lambda: self.set_standard_view("right"))
                top_action.triggered.connect(lambda: self.set_standard_view("top"))
                bottom_action.triggered.connect(lambda: self.set_standard_view("bottom"))
                isometric_action.triggered.connect(lambda: self.set_standard_view("isometric"))
                
                # 初始化存储的视图列表
                self.stored_views = []
                self.view_counter = 0
                
                # 连接菜单项信号
                store_view_action.triggered.connect(lambda: self.store_current_view(restore_view_menu))
                perspective_action.triggered.connect(lambda: self.set_projection_mode("perspective"))
                parallel_action.triggered.connect(lambda: self.set_projection_mode("parallel"))
                
                # 设置按钮点击事件
                btn.setMenu(view_menu)
            
            top_button_layout.addWidget(btn)
        
        # 将顶部按钮栏添加到主布局
        main_layout.addWidget(top_button_bar)
        
        # 创建内容区域布局（控制面板和VTK窗口）
        content_layout = QHBoxLayout()
        
        # 创建左侧控制面板（使用标签页）
        control_panel = QFrame()
        control_panel.setFrameStyle(QFrame.Panel | QFrame.Raised)
        control_panel.setMaximumWidth(300)
        control_layout = QVBoxLayout(control_panel)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        control_layout.addWidget(self.tab_widget)
        
        # 创建"修复"标签页
        fix_tab = QWidget()
        fix_layout = QVBoxLayout(fix_tab)
        
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
        
        fix_layout.addWidget(coord_group)
        
        # 创建面操作区域
        face_group = QFrame()
        face_layout = QVBoxLayout(face_group)
        
        # 从选中点创建面按钮
        create_face_btn = QPushButton('从选中点创建面')
        create_face_btn.clicked.connect(self.create_face)
        face_layout.addWidget(create_face_btn)
        
        # 清除选择按钮
        clear_selection_btn = QPushButton('清除选择')
        clear_selection_btn.clicked.connect(self.clear_selection)
        face_layout.addWidget(clear_selection_btn)
        
        # 添加删除选定面按钮
        delete_faces_btn = QPushButton('删除选定面 (D)')
        delete_faces_btn.clicked.connect(self.delete_selected_faces)
        delete_faces_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: 1px solid #cc0000;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #ff6666;
                border-color: #ff0000;
            }
        """)
        face_layout.addWidget(delete_faces_btn)
        
        fix_layout.addWidget(face_group)
        
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
        
        fix_layout.addWidget(mode_group)
        
        # 连接模式切换信号
        self.point_mode_btn.clicked.connect(lambda: self.set_selection_mode('point'))
        self.edge_mode_btn.clicked.connect(lambda: self.set_selection_mode('edge'))
        self.face_mode_btn.clicked.connect(lambda: self.set_selection_mode('face'))
        self.smart_mode_btn.clicked.connect(lambda: self.set_selection_mode('smart'))
        
        # 添加伸缩器
        fix_layout.addStretch()
        
        # 创建Global标签页（暂时为空）
        global_tab = QWidget()
        global_layout = QVBoxLayout(global_tab)
        global_layout.addWidget(QLabel("Global功能将在此处实现"))
        global_layout.addStretch()
        
        # 创建Query标签页（暂时为空）
        query_tab = QWidget()
        query_layout = QVBoxLayout(query_tab)
        query_layout.addWidget(QLabel("Query功能将在此处实现"))
        query_layout.addStretch()
        
        # 创建Organize标签页（暂时为空）
        organize_tab = QWidget()
        organize_layout = QVBoxLayout(organize_tab)
        organize_layout.addWidget(QLabel("Organize功能将在此处实现"))
        organize_layout.addStretch()
        
        # 将标签页添加到标签页控件
        self.tab_widget.addTab(fix_tab, "修复")
        self.tab_widget.addTab(global_tab, "Global")
        self.tab_widget.addTab(query_tab, "Query")
        self.tab_widget.addTab(organize_tab, "Organize")
        
        # 设置控制面板布局
        control_panel.setLayout(control_layout)
        
        # 创建右侧VTK和状态指示器容器
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建水平布局来放置VTK窗口和自由边按钮
        vtk_container = QHBoxLayout()
        
        # 创建VTK窗口容器（用于放置VTK窗口和自由边按钮）
        vtk_frame = QWidget()
        vtk_frame.setStyleSheet("background-color: transparent;")
        vtk_frame_layout = QHBoxLayout(vtk_frame)
        vtk_frame_layout.setContentsMargins(0, 0, 0, 0)
        vtk_frame_layout.addWidget(self.vtk_widget)
        
        # 创建Face intersection按钮图标（程序化绘制，替换SVG文件）
        intersection_icon = QIcon()
        intersection_pixmap = QPixmap(32, 32)
        intersection_pixmap.fill(Qt.transparent)
        intersection_painter = QPainter(intersection_pixmap)
        intersection_painter.setRenderHint(QPainter.Antialiasing)
        intersection_pen = QPen(QColor(255, 0, 0))
        intersection_pen.setWidth(2)
        intersection_painter.setPen(intersection_pen)
        # 绘制两条相交的线
        intersection_painter.drawLine(8, 8, 24, 24)  # 从左上到右下的线
        intersection_painter.drawLine(24, 8, 8, 24)  # 从右上到左下的线
        intersection_painter.end()
        intersection_icon.addPixmap(intersection_pixmap)
        
        # 复用交叉面图标
        fast_intersection_icon = intersection_icon

        # 创建Face quality按钮图标（程序化绘制，替换SVG文件）
        quality_icon = QIcon()
        quality_pixmap = QPixmap(32, 32)
        quality_pixmap.fill(Qt.transparent)
        quality_painter = QPainter(quality_pixmap)
        quality_painter.setRenderHint(QPainter.Antialiasing)
        quality_pen = QPen(QColor(0, 128, 255))
        quality_pen.setWidth(2)
        quality_painter.setPen(quality_pen)
        # 绘制一个三角形
        quality_painter.drawLine(16, 8, 8, 24)   # 左边线
        quality_painter.drawLine(16, 8, 24, 24)  # 右边线
        quality_painter.drawLine(8, 24, 24, 24)  # 底边线
        quality_painter.end()
        quality_icon.addPixmap(quality_pixmap)

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
        fast_intersection_btn.setFixedSize(80, 30)
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
        
        # 创建左侧9个按钮
        left_btns = []
        for i in range(9):
            left_btn = QPushButton(f"按钮{i+1}")
            left_btn.setFixedSize(80, 30)
            left_btn.setStyleSheet("""
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
            left_btn.setParent(vtk_frame)
            left_btns.append(left_btn)
        
        # 创建顶部8个按钮
        top_btns = []
        for i in range(8):
            top_btn = QPushButton(f"按钮{i+1}")
            top_btn.setFixedSize(30, 30)  # 将按钮改为30x30的正方形
            top_btn.setStyleSheet("""
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
            top_btn.setParent(vtk_frame)
            top_btns.append(top_btn)
        
        # 设置按钮位置
        # 设置右侧按钮位置，紧挨在一起没有缝隙
        button_height = 30  # 按钮高度
        total_right_buttons = 6  # 右侧按钮总数
        right_start_y = int(vtk_frame.height() / 2) - ((total_right_buttons * button_height) // 2)  # 让按钮组居中
        
        # 创建右侧六个按钮的标签位置
        self.intersection_count = QLabel("未分析", vtk_frame)
        self.quality_count = QLabel("未分析", vtk_frame)
        self.proximity_count = QLabel("未分析", vtk_frame)
        self.free_edge_count = QLabel("未分析", vtk_frame)
        self.overlap_edge_count = QLabel("未分析", vtk_frame)
        self.overlap_point_count = QLabel("未分析", vtk_frame)

        # 设置标签样式
        label_style = """
            QLabel {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #999999;
                border-radius: 4px;
                padding: 2px;
                min-width: 50px;
                max-width: 50px;
                qproperty-alignment: AlignCenter;
            }
        """
        
        # 应用样式到所有标签
        for label in [self.intersection_count, self.quality_count, self.proximity_count,
                     self.free_edge_count, self.overlap_edge_count, self.overlap_point_count]:
            label.setStyleSheet(label_style)
            label.setFixedSize(50, 30)
            # 设置基础字体
            font = QFont('Arial', 9)
            font.setBold(True)
            label.setFont(font)
            
        # 添加自动调整字体大小的方法
        def adjust_font_size(label, text):
            # 如果是数字，根据长度调整字体大小
            if text.isdigit():
                # 获取当前字体
                font = label.font()
                # 根据数字位数调整字体大小
                length = len(text)
                if length <= 1:
                    font.setPointSize(12)  # 1位数字使用最大字体
                elif length == 2:
                    font.setPointSize(11)
                elif length == 3:
                    font.setPointSize(10)
                elif length == 4:
                    font.setPointSize(9)
                elif length == 5:
                    font.setPointSize(8)
                elif length == 6:
                    font.setPointSize(7)
                else:  # 7位或更多
                    font.setPointSize(6)  # 7位数字使用最小字体
                
                # 设置新字体
                label.setFont(font)
            else:
                # 非数字文本（如"未分析"）使用固定字体大小
                font = QFont('Arial', 9)
                font.setBold(True)
                label.setFont(font)
                
            # 更新文本
            label.setText(text)
            
        # 保存方法供后续使用
        self.adjust_font_size = adjust_font_size
        
        # 添加重置标签方法
        def reset_label(label):
            font = QFont('Arial', 9)
            font.setBold(True)
            label.setFont(font)
            label.setText("未分析")
            
        # 保存重置方法供后续使用
        self.reset_label = reset_label
        
        # 设置按钮和标签位置
        fast_intersection_btn.move(vtk_frame.width() - 130, right_start_y)
        self.intersection_count.move(vtk_frame.width() - 50, right_start_y)
        
        face_quality_btn.move(vtk_frame.width() - 130, right_start_y + button_height)
        self.quality_count.move(vtk_frame.width() - 50, right_start_y + button_height)
        
        face_prox_btn.move(vtk_frame.width() - 130, right_start_y + button_height * 2)
        self.proximity_count.move(vtk_frame.width() - 50, right_start_y + button_height * 2)
        
        free_edge_btn.move(vtk_frame.width() - 130, right_start_y + button_height * 3)
        self.free_edge_count.move(vtk_frame.width() - 50, right_start_y + button_height * 3)
        
        overlap_edge_btn.move(vtk_frame.width() - 130, right_start_y + button_height * 4)
        self.overlap_edge_count.move(vtk_frame.width() - 50, right_start_y + button_height * 4)
        
        overlap_point_btn.move(vtk_frame.width() - 130, right_start_y + button_height * 5)
        self.overlap_point_count.move(vtk_frame.width() - 50, right_start_y + button_height * 5)
        
        # 定位左侧9个按钮（紧挨在一起无缝隙）
        for i, btn in enumerate(left_btns):
            btn.move(10, int(vtk_frame.height() / 2 - 135 + i * 30))  # 从中间位置开始，每个按钮高度30px
        
        # 定位顶部8个按钮（紧挨在一起无缝隙）
        total_width = 30 * 8  # 8个按钮的总宽度 (30px每个)
        start_x = (vtk_frame.width() - total_width) // 2  # 计算起始位置使按钮在中间
        for i, btn in enumerate(top_btns):
            btn.move(start_x + i * 30, 10)  # 顶部位置，水平排列
        
        # 创建性能模式切换按钮
        perf_mode_btn = QPushButton('切换性能模式')
        perf_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #333333;
                border: 1px solid #999999;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
                border-color: #666666;
            }
        """)
        perf_mode_btn.clicked.connect(self.toggle_performance_mode)
        perf_mode_btn.setFixedSize(120, 30)
        perf_mode_btn.setParent(vtk_frame)
        perf_mode_btn.move(20, 20)  # 位于左上角
        
        # 当VTK窗口大小改变时，更新按钮位置
        def update_button_positions(event=None):
            # 更新右侧按钮位置，紧挨在一起没有缝隙
            button_height = 30  # 按钮高度
            total_right_buttons = 6  # 右侧按钮总数
            right_start_y = int(vtk_frame.height() / 2) - ((total_right_buttons * button_height) // 2)  # 让按钮组居中
            
            # 更新按钮和标签位置
            fast_intersection_btn.move(vtk_frame.width() - 130, right_start_y)
            self.intersection_count.move(vtk_frame.width() - 50, right_start_y)
            
            face_quality_btn.move(vtk_frame.width() - 130, right_start_y + button_height)
            self.quality_count.move(vtk_frame.width() - 50, right_start_y + button_height)
            
            face_prox_btn.move(vtk_frame.width() - 130, right_start_y + button_height * 2)
            self.proximity_count.move(vtk_frame.width() - 50, right_start_y + button_height * 2)
            
            free_edge_btn.move(vtk_frame.width() - 130, right_start_y + button_height * 3)
            self.free_edge_count.move(vtk_frame.width() - 50, right_start_y + button_height * 3)
            
            overlap_edge_btn.move(vtk_frame.width() - 130, right_start_y + button_height * 4)
            self.overlap_edge_count.move(vtk_frame.width() - 50, right_start_y + button_height * 4)
            
            overlap_point_btn.move(vtk_frame.width() - 130, right_start_y + button_height * 5)
            self.overlap_point_count.move(vtk_frame.width() - 50, right_start_y + button_height * 5)
            
            # 更新切换按钮位置 - 放在右侧按钮的左侧
            for i, btn in enumerate(self.toggle_buttons):
                btn.move(vtk_frame.width() - 150, right_start_y + button_height * i)
            
            # 保持性能模式按钮在左上角
            perf_mode_btn.move(20, 20)
            
            # 更新左侧9个按钮位置
            for i, btn in enumerate(left_btns):
                btn.move(10, int(vtk_frame.height() / 2 - 135 + i * 30))
            
            # 更新顶部8个按钮位置
            total_width = 30 * 8  # 8个按钮的总宽度 (30px每个)
            start_x = (vtk_frame.width() - total_width) // 2  # 重新计算起始位置
            for i, btn in enumerate(top_btns):
                btn.move(start_x + i * 30, 10)
            
            # 更新导航按钮位置（四个新增的按钮）
            nav_btn_y = right_start_y + button_height * 6  # 位于六个按钮下方，紧挨着
            
            # 左对齐与打勾框（toggle按钮）
            nav_left = vtk_frame.width() - 150  # 与toggle按钮左侧对齐
            
            # 右对齐与数字框（count标签）
            nav_right = vtk_frame.width()  # 数字框右边界
            
            # 计算四个按钮的总宽度
            nav_total_width = nav_right - nav_left  # 从toggle按钮左侧到count标签右侧的总宽度
            
            # 计算每个导航按钮的宽度
            nav_btn_width = nav_total_width // 4
            
            # 放置导航按钮
            for i, btn in enumerate(self.nav_buttons):
                btn.setFixedSize(nav_btn_width, 30)  # 更新按钮大小
                btn.move(nav_left + i * nav_btn_width, nav_btn_y)
                
            # 更新功能按钮位置（两个功能按钮，位于导航按钮下方）
            func_btn_width = nav_total_width  # 按钮宽度为导航按钮的总宽度
            func_btn_y_start = nav_btn_y + button_height  # 导航按钮下方，紧挨着
            
            for i, btn in enumerate(self.function_buttons):
                btn.setFixedSize(func_btn_width, 30)  # 更新按钮大小
                btn.move(nav_left, func_btn_y_start + i * button_height)  # 垂直排列，紧挨着
        
        vtk_frame.resizeEvent = update_button_positions
        
        # 初始调用一次更新按钮位置，设置初始状态
        update_button_positions()
        
        # 将水平布局添加到右侧容器
        right_layout.addLayout(vtk_container, stretch=1)
        
        # 注意：自由边按钮已经添加到vtk_frame中，不需要再添加到btn_container
        
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
        # self.renderer = vtk.vtkRenderer()  # 删除这一行，因为在前面已经创建了renderer
        # self.renderer.SetBackground(1.0, 1.0, 1.0)  # 删除这一行，因为在前面已经设置了背景
        
        # 性能优化：启用双缓冲减少闪烁，设置渲染窗口属性
        render_window = self.vtk_widget.GetRenderWindow()
        render_window.SetDoubleBuffer(1)
        render_window.SetDesiredUpdateRate(30.0)  # 目标帧率设置为30fps
        
        # 判断模型大小，动态调整渲染参数
        if len(self.mesh_data['faces']) > self.large_model_threshold:
            render_window.SetMultiSamples(0)  # 关闭抗锯齿提高性能
            self.is_large_model = True
            # 性能优化: 大型模型时启用多种渲染优化
            self.renderer = vtk.vtkRenderer()
            self.renderer.SetUseDepthPeeling(0)  # 禁用深度剥离提高性能
            self.renderer.SetUseFXAA(0)  # 禁用FXAA抗锯齿
            # 某些版本的VTK可能不支持SetUseSSAO
            try:
                self.renderer.SetUseSSAO(0)  # 禁用环境光遮蔽
            except AttributeError:
                pass  # 忽略不支持的方法
            self.renderer.SetBackground(1.0, 1.0, 1.0)
            print(f"大型模型检测: {len(self.mesh_data['faces'])}面, 关闭抗锯齿并应用性能优化")
        else:
            render_window.SetMultiSamples(4)  # 适度的抗锯齿
            # 正常模型使用标准设置
            self.renderer = vtk.vtkRenderer()
            self.renderer.SetBackground(1.0, 1.0, 1.0)
            print(f"普通模型检测: {len(self.mesh_data['faces'])}面, 应用标准渲染设置")
        
        render_window.AddRenderer(self.renderer)
        
        self.iren = render_window.GetInteractor()
        
        # 设置交互器样式
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(style)
        
        # 重新设置事件观察器
        self.iren.RemoveObservers("LeftButtonPressEvent")
        self.iren.RemoveObservers("MouseMoveEvent")
        self.iren.RemoveObservers("LeftButtonReleaseEvent")
        
        self.iren.AddObserver("LeftButtonPressEvent", self.on_left_button_press)
        self.iren.AddObserver("MouseMoveEvent", self.on_mouse_move)
        self.iren.AddObserver("LeftButtonReleaseEvent", self.on_left_button_release)
        
        # 初始化显示
        self.update_display()
        self.reset_camera()
        self.iren.Initialize()
        
        # 启动帧率控制定时器
        self.fps_timer.start()
        
        # 添加方向指示器（坐标轴）
        self.add_orientation_marker()
        
        # 初始化选择模式
        self.selection_mode = 'smart'
        self.selected_points = []
        self.selected_edges = []
        self.selected_faces = []
        self.temp_points = []  # 仅用于创建面的临时点
        
        # 添加快捷键
        self.setFocusPolicy(Qt.StrongFocus)
        
        # 添加快捷键
        self.shortcut_delete = QShortcut(QKeySequence(Qt.Key_D), self)
        self.shortcut_delete.activated.connect(self.delete_selected_faces)
        
        self.shortcut_performance = QShortcut(QKeySequence(Qt.Key_P), self)
        self.shortcut_performance.activated.connect(self.toggle_performance_mode)
        
        self.shortcut_axes = QShortcut(QKeySequence(Qt.Key_A), self)
        self.shortcut_axes.activated.connect(self.toggle_axes_visibility)
    
        # 创建6个小的切换按钮 - 放在右侧按钮左侧
        self.toggle_buttons = []
        for i in range(6):
            toggle_btn = QPushButton("", vtk_frame)
            toggle_btn.setFixedSize(20, 30)  # 小按钮，高度与右侧按钮一致
            toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    color: #333333;
                    border: 1px solid #999999;
                    border-radius: 4px;
                    padding: 0px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                    border-color: #666666;
                }
            """)
            # 使用lambda创建闭包，确保每个按钮能获取正确的索引
            toggle_btn.clicked.connect(lambda checked, idx=i: self.toggle_checkbox(idx))
            self.toggle_buttons.append(toggle_btn)
            toggle_btn.setParent(vtk_frame)
        
        # 创建四个导航按钮（第一个、上一个、下一个、最后一个）
        self.nav_buttons = []
        nav_btn_names = ["首个", "上一个", "下一个", "末个"]
        
        for i in range(4):
            nav_btn = QPushButton("", vtk_frame)
            # 不在这里设置固定大小，由update_button_positions动态设置
            # nav_btn.setFixedSize(40, 30)  # 设置按钮大小
            
            # 设置导航按钮基本样式
            nav_btn.setStyleSheet("""
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
                QPushButton:pressed {
                    background-color: #c0c0c0;
                    border-color: #555555;
                }
            """)
            
            # 创建按钮图标
            icon_pixmap = QPixmap(32, 32)
            icon_pixmap.fill(Qt.transparent)
            painter = QPainter(icon_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor(0, 0, 0))
            pen.setWidth(2)
            painter.setPen(pen)
            
            # 根据按钮类型绘制不同图标
            if i == 0:  # 第一个按钮 - 向左双箭头带竖线
                # 竖线
                painter.drawLine(8, 8, 8, 24)
                # 第一个左箭头箭身
                painter.drawLine(16, 16, 8, 16)
                # 第一个左箭头箭头
                painter.drawLine(12, 12, 8, 16)
                painter.drawLine(12, 20, 8, 16)
                # 第二个左箭头箭身
                painter.drawLine(24, 16, 16, 16)
                # 第二个左箭头箭头
                painter.drawLine(20, 12, 16, 16)
                painter.drawLine(20, 20, 16, 16)
            elif i == 1:  # 上一个按钮 - 向左箭头
                # 画左箭头
                painter.drawLine(20, 16, 12, 16)
                painter.drawLine(16, 12, 12, 16)
                painter.drawLine(16, 20, 12, 16)
            elif i == 2:  # 下一个按钮 - 向右箭头
                # 画右箭头
                painter.drawLine(12, 16, 20, 16)
                painter.drawLine(16, 12, 20, 16)
                painter.drawLine(16, 20, 20, 16)
            elif i == 3:  # 最后一个按钮 - 向右双箭头带竖线
                # 竖线
                painter.drawLine(24, 8, 24, 24)
                # 第一个右箭头箭身
                painter.drawLine(8, 16, 16, 16)
                # 第一个右箭头箭头
                painter.drawLine(12, 12, 16, 16)
                painter.drawLine(12, 20, 16, 16)
                # 第二个右箭头箭身
                painter.drawLine(16, 16, 24, 16)
                # 第二个右箭头箭头
                painter.drawLine(20, 12, 24, 16)
                painter.drawLine(20, 20, 24, 16)
            
            painter.end()
            
            # 设置图标
            btn_icon = QIcon()
            btn_icon.addPixmap(icon_pixmap)
            nav_btn.setIcon(btn_icon)
            nav_btn.setIconSize(QSize(24, 24))
            
            # 设置提示文本
            nav_btn.setToolTip(nav_btn_names[i])
            
            # 添加点击事件处理
            nav_btn.clicked.connect(lambda checked, idx=i: self.handle_nav_button(idx))
            
            self.nav_buttons.append(nav_btn)
            nav_btn.setParent(vtk_frame)
            
        # 创建两个功能按钮
        self.function_buttons = []
        function_btn_names = ["Reset View", "Rest Displayed"]
        
        for i in range(2):
            func_btn = QPushButton(function_btn_names[i], vtk_frame)
            
            # 设置按钮基本样式（灰色，未激活状态）
            func_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;  /* 浅灰色 */
                    color: #333333;  /* 深灰色文字 */
                    border: 1px solid #999999;  /* 灰色边框 */
                    border-radius: 4px;
                    padding: 2px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;  /* 稍深灰色悬停 */
                    border-color: #666666;
                }
            """)
            
            # 添加点击事件处理
            func_btn.clicked.connect(lambda checked, idx=i: self.toggle_function_button(idx))
            
            self.function_buttons.append(func_btn)
            func_btn.setParent(vtk_frame)
    
    def add_orientation_marker(self):
        """添加随视角变化的坐标轴方向指示器"""
        # 创建坐标轴
        axes = vtk.vtkAxesActor()
        
        # 设置坐标轴标签
        axes.SetXAxisLabelText("X")
        axes.SetYAxisLabelText("Y")
        axes.SetZAxisLabelText("Z")
        
        # 设置坐标轴的粗细
        axes.SetShaftTypeToCylinder()
        axes.SetCylinderRadius(0.02)
        axes.SetConeRadius(0.15)
        
        # 设置坐标轴长度
        axes.SetTotalLength(1.0, 1.0, 1.0)
        
        # 设置轴颜色
        axes.GetXAxisTipProperty().SetColor(1, 0, 0)  # X轴: 红色
        axes.GetYAxisTipProperty().SetColor(0, 1, 0)  # Y轴: 绿色
        axes.GetZAxisTipProperty().SetColor(0, 0, 1)  # Z轴: 蓝色
        
        axes.GetXAxisShaftProperty().SetColor(1, 0, 0)
        axes.GetYAxisShaftProperty().SetColor(0, 1, 0)
        axes.GetZAxisShaftProperty().SetColor(0, 0, 1)
        
        # 设置标签属性
        for label_idx, label in enumerate([axes.GetXAxisCaptionActor2D(), 
                                         axes.GetYAxisCaptionActor2D(), 
                                         axes.GetZAxisCaptionActor2D()]):
            # 设置标签的字体大小和样式
            label_prop = label.GetCaptionTextProperty()
            label_prop.SetFontSize(12)
            label_prop.SetBold(True)
            
            # 设置标签颜色
            if label_idx == 0:    # X轴
                label_prop.SetColor(1, 0, 0)
            elif label_idx == 1:  # Y轴
                label_prop.SetColor(0, 1, 0)
            else:                 # Z轴
                label_prop.SetColor(0, 0, 1)
        
        # 创建方向指示器部件
        self.orientation_marker = vtk.vtkOrientationMarkerWidget()
        self.orientation_marker.SetOrientationMarker(axes)
        self.orientation_marker.SetInteractor(self.iren)
        
        # 设置方向指示器的位置和大小 (右下角)
        self.orientation_marker.SetViewport(0.80, 0.02, 0.98, 0.2)
        
        # 设置边框属性
        self.orientation_marker.SetOutlineColor(0.93, 0.57, 0.13)  # 橙色边框
        self.orientation_marker.SetEnabled(1)
        
        # 启用方向指示器但禁用拖动交互
        self.orientation_marker.InteractiveOff()
        
        # 直接将坐标轴设置为指示器内容 (确保这行存在且有效)
        self.orientation_marker.SetOrientationMarker(axes)
    
    def set_selection_mode(self, mode):
        """设置选择模式"""
        self.selection_mode = mode
        
        # 更新按钮状态
        self.point_mode_btn.setChecked(mode == 'point')
        self.edge_mode_btn.setChecked(mode == 'edge')
        self.face_mode_btn.setChecked(mode == 'face')
        self.smart_mode_btn.setChecked(mode == 'smart')
    
    def on_fps_timer(self):
        """帧率控制定时器回调"""
        # 只有在需要时才进行高分辨率渲染
        if self.needs_high_res_render and not self.is_interacting:
            render_window = self.vtk_widget.GetRenderWindow()
            # 为大模型使用更低的渲染质量
            if self.is_large_model:
                render_window.SetDesiredUpdateRate(0.001)  # 大模型使用更低的质量
            else:
                render_window.SetDesiredUpdateRate(0.0001)  # 小模型使用高质量
            render_window.Render()
            self.needs_high_res_render = False
            
            # 调试信息
            #print("高质量渲染完成")
            
            # 触发垃圾回收
            gc.collect()
    
    def on_left_button_press(self, obj, event):
        """处理鼠标左键按下事件"""
        # 记录按下状态
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
        
        # 性能优化：交互时保持较低的渲染质量
        if self.left_button_down:
            self.is_interacting = True
            self.vtk_widget.GetRenderWindow().SetDesiredUpdateRate(30.0)
        
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
        
        # 性能优化：交互结束后，标记为需要高质量渲染
        self.is_interacting = False
        self.needs_high_res_render = True
        
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
        
        # 检查是否按住右键 - 显示上下文菜单
        # 首先检查event是否是有效的VTK事件对象(具有GetModifiers方法)
        has_right_button_modifier = False
        try:
            if hasattr(event, 'GetModifiers'):
                has_right_button_modifier = event.GetModifiers() & vtk.vtkRenderWindowInteractor.RightButtonModifier
        except (AttributeError, TypeError):
            pass  # 如果event不是预期的VTK事件对象，则跳过
            
        if has_right_button_modifier and cell_id != -1:
            # 创建右键菜单
            context_menu = QMenu(self)
            
            # 根据当前选择模式添加菜单项
            if self.selection_mode == 'face':
                if cell_id in self.selected_faces:
                    remove_action = context_menu.addAction("取消选择此面")
                    remove_action.triggered.connect(lambda: self.toggle_face_selection(cell_id))
                else:
                    add_action = context_menu.addAction("选择此面")
                    add_action.triggered.connect(lambda: self.toggle_face_selection(cell_id))
                
                # 如果面相交关系映射存在数据
                if hasattr(self, 'face_intersection_map') and self.face_intersection_map:
                    # 如果当前面在相交映射中
                    if cell_id in self.face_intersection_map and self.face_intersection_map[cell_id]:
                        show_intersections = context_menu.addAction(f"显示此面的相交关系 ({len(self.face_intersection_map[cell_id])}个)")
                        show_intersections.triggered.connect(lambda: self.show_face_intersections(cell_id))
            
            # 添加删除选项
            context_menu.addSeparator()
            if self.selection_mode == 'face':
                delete_action = context_menu.addAction("删除此面")
                delete_action.triggered.connect(lambda: self.delete_face(cell_id))
            
            # 在点击位置显示上下文菜单
            global_pos = QCursor.pos()
            context_menu.exec_(global_pos)
            hit_anything = True
            return
        
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
                    self.edge_selection_source = 'manual'  # 设置为手动选择
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
            
            # 标记模型已经修改，并追踪新点ID
            self.mark_model_modified()
            if hasattr(self, 'model_tracker'):
                self.model_tracker.track_modification('points', [new_point_id])
            
            # 由于模型已改变，重新进行检测
            self.update_model_analysis()
            
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的数值坐标")
    
    def create_vtk_mesh(self):
        """从网格数据创建VTK网格，带优化的性能"""
        # 检查是否可以重用缓存的网格
        if self.cached_mesh is not None:
            # 如果顶点和面的数量没有变化，可以重用缓存
            if (len(self.mesh_data['vertices']) == self.cached_mesh.GetNumberOfPoints() and 
                len(self.mesh_data['faces']) == self.cached_mesh.GetNumberOfCells()):
                return self.cached_mesh
        
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
        
        # 性能优化：仅在首次创建网格时计算法线
        if self.cached_mesh is None:
            normals = vtk.vtkPolyDataNormals()
            normals.SetInputData(mesh)
            normals.ComputePointNormalsOn()
            normals.ComputeCellNormalsOn()
            
            # 性能优化：大型模型减少法线计算精度
            if self.is_large_model:
                normals.SetSplitting(0)  # 禁用分裂以提高性能
                normals.SetFeatureAngle(60)  # 增加特征角度，减少法线计算
                normals.SetConsistency(1)  # 保持法线一致性
            
            normals.Update()
            mesh = normals.GetOutput()
        
        # 缓存网格以便重用
        self.cached_mesh = mesh
        self.mesh = mesh
        
        return mesh
    
    def create_point_glyph_source(self):
        """创建点的显示源，仅需创建一次"""
        if self.point_glyph_source is None:
            # 为大型模型使用更简单的点表示
            if self.is_large_model:
                # 使用简单的立方体代替球体，渲染更快
                cube = vtk.vtkCubeSource()
                cube.SetXLength(0.8)
                cube.SetYLength(0.8)
                cube.SetZLength(0.8)
                cube.Update()
                self.point_glyph_source = cube.GetOutput()
            else:
                # 小型模型仍使用球体表示点
                sphere = vtk.vtkSphereSource()
                sphere.SetRadius(0.5)
                
                # 根据模型大小自适应调整点的细节级别
                if self.is_large_model:
                    sphere.SetPhiResolution(6)    # 大模型使用更低的细节
                    sphere.SetThetaResolution(6)
                else:
                    sphere.SetPhiResolution(8)    # 小模型使用标准细节
                    sphere.SetThetaResolution(8)
                    
                sphere.Update()
                self.point_glyph_source = sphere.GetOutput()
                
        return self.point_glyph_source
    
    def update_status_counts(self):
        """更新状态计数"""
        self.point_count.setText(str(len(self.selected_points)))
        self.edge_count.setText(str(len(self.selected_edges)))
        self.face_count.setText(str(len(self.selected_faces)))

    def update_display(self):
        """更新显示，使用优化的点显示方法"""
        # 检查选择状态是否变化
        current_selection = {
            'points': set(self.selected_points),
            'edges': set(tuple(edge) for edge in self.selected_edges),
            'faces': set(self.selected_faces)
        }
        
        # 如果选择状态没有变化且我们不是在交互中，可以跳过重新渲染
        if (self.last_selection_state == current_selection and 
            not self.is_interacting and 
            not self.needs_high_res_render and
            hasattr(self, '_first_render')):
            #print("跳过不必要的渲染")
            return
        
        # 记录渲染时间
        start_time = time.time()
        
        self.last_selection_state = current_selection
        
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
        
        # 性能优化：根据模型大小设置渲染参数
        # mapper.SetImmediateModeRendering(0)  # 移除不兼容的方法调用
        
        # 大模型额外优化
        if self.is_large_model:
            # 减少细节级别优化
            mapper.SetResolveCoincidentTopologyToPolygonOffset()
            mapper.SetScalarVisibility(0)
            # 关闭不必要的控制以获得更好的性能
            mapper.ScalarVisibilityOff()
            mapper.SetColorModeToDefault()
            
            # 指定渲染策略
            if hasattr(mapper, 'SetScalarMaterialMode'):
                mapper.SetScalarMaterialMode(0)
        
        mapper.Update()
        
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.8, 0.8, 0.8)  # 浅灰色
        
        # 大模型减少边的显示
        if not self.is_large_model or len(self.selected_faces) > 0:
            actor.GetProperty().SetEdgeVisibility(True)
            actor.GetProperty().SetLineWidth(1.0)
        else:
            actor.GetProperty().SetEdgeVisibility(False)  # 大模型默认不显示边
        
        # 优化渲染属性
        if self.is_large_model:
            actor.GetProperty().SetSpecular(0)  # 关闭高光效果
            actor.GetProperty().SetSpecularPower(1)
            actor.GetProperty().SetDiffuse(0.8)
            actor.GetProperty().SetAmbient(0.2)
        
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
            # selected_mapper.SetImmediateModeRendering(0)  # 移除不兼容的方法调用
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
            # edge_mapper.SetImmediateModeRendering(0)  # 移除不兼容的方法调用
            
            edge_actor = vtk.vtkActor()
            edge_actor.SetMapper(edge_mapper)
            # 根据边选择来源决定颜色
            if hasattr(self, 'edge_selection_source') and self.edge_selection_source == 'auto':
                edge_actor.GetProperty().SetColor(0.0, 1.0, 0.0)  # 自动选择的边为绿色
            else:
                edge_actor.GetProperty().SetColor(1.0, 0.0, 0.0)  # 手动选择的边为红色
            edge_actor.GetProperty().SetLineWidth(3.0)
            
            # 大模型时不使用线条管道渲染以提高性能
            if not self.is_large_model:
                edge_actor.GetProperty().SetRenderLinesAsTubes(True)
            
            self.renderer.AddActor(edge_actor)
        
        # 显示点 - 性能优化：智能显示点，减少渲染负担
        total_points = len(self.mesh_data['vertices'])
        
        # 根据模型大小动态调整点阈值
        point_threshold = self.point_threshold
        if self.is_large_model:
            point_threshold = 200  # 大模型使用更小的阈值
        
        # 确定要显示哪些点
        points_to_display = []
        
        # 选择性显示点
        if total_points <= point_threshold or self.selected_points: # 移除 'and not self.is_interacting' 以允许交互时显示选中点
            # 交互过程中不显示太多点，除非特别选中了点
            if self.is_interacting and not self.selected_points:
                # 交互时如果没有选中的点，则不显示任何点以提高性能
                pass
            else: # 执行渲染逻辑（如果非交互，或者交互中但有选中点）
                # 如果点数少于阈值，显示所有点
                if total_points <= point_threshold:
                    for i, point in enumerate(self.mesh_data['vertices']):
                        is_selected = i in self.selected_points
                        points_to_display.append((i, is_selected))
                else:
                    # 否则只显示选中的点
                    for i in self.selected_points:
                        points_to_display.append((i, True))

                if points_to_display:
                    # 创建点的VTK表示
                    pts = vtk.vtkPoints()
                    vertex_data = vtk.vtkPolyData()
                    
                    # 创建颜色标量数组
                    colors = vtk.vtkUnsignedCharArray()
                    colors.SetNumberOfComponents(3)
                    colors.SetName("Colors")
                    
                    # 创建大小标量数组 - 用于控制点的大小
                    sizes = vtk.vtkFloatArray()
                    sizes.SetNumberOfComponents(1)
                    sizes.SetName("Sizes")

                    for idx, (i, is_selected) in enumerate(points_to_display):
                        pts.InsertNextPoint(self.mesh_data['vertices'][i])
                        if is_selected:
                            colors.InsertNextTuple3(255, 0, 0)  # 红色
                            sizes.InsertNextValue(1.5)  # 选中的点放大 1.5 倍
                        else:
                            colors.InsertNextTuple3(77, 77, 77)  # 深灰色
                            sizes.InsertNextValue(1.0)  # 未选中的点保持原始大小

                    vertex_data.SetPoints(pts)
                    # 将颜色和大小标量关联到 *输入* 点数据
                    vertex_data.GetPointData().SetScalars(colors)
                    vertex_data.GetPointData().AddArray(sizes)

                    # 创建或获取点的Glyph源
                    point_source = self.create_point_glyph_source()

                    # 使用Glyph3D为每个点创建一个球体
                    glyph = vtk.vtkGlyph3D()
                    glyph.SetSourceData(point_source)
                    glyph.SetInputData(vertex_data)
                    # glyph.ScalingOff() # 移除禁用缩放的设置
                    
                    # 配置 Glyph3D 使用输入标量进行着色和缩放
                    glyph.SetColorModeToColorByScalar()
                    # 启用基于标量的缩放
                    glyph.SetScaleModeToScaleByScalar()
                    glyph.SetScaleFactor(1.0)  # 基础缩放因子
                    # 指定用哪个数组控制缩放
                    glyph.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, "Sizes")

                    # 大型模型额外优化 - 移除可能冲突的设置
                    # if self.is_large_model:
                    #     if hasattr(glyph, 'SetColorModeToColorByScalar'):
                    #         glyph.SetColorModeToColorByScalar() # <--- 注释掉

                    glyph.Update()

                    # 为每个点着色 - 这行不再需要，颜色已在 Glyph3D 内部处理
                    glyph_data = glyph.GetOutput()
                    # glyph_data.GetPointData().SetScalars(colors) # <--- 移除或注释掉

                    # 创建mapper和actor
                    glyph_mapper = vtk.vtkPolyDataMapper()
                    glyph_mapper.SetInputData(glyph_data)
                    # 设置 Mapper 直接使用顶点标量作为颜色，不再通过 LUT 映射
                    glyph_mapper.SetScalarModeToUsePointData()
                    # glyph_mapper.SetColorModeToMapScalars()    # <--- 移除或注释掉，不再需要 LUT 映射
                    glyph_mapper.ScalarVisibilityOn()         # 确保标量可见性开启
                    # glyph_mapper.ScalarVisibilityOff()         # <--- 移除或注释掉这行，因为它与 ScalarVisibilityOn 冲突
                    # glyph_mapper.SetImmediateModeRendering(0)  # 移除不兼容的方法调用

                    glyph_actor = vtk.vtkActor()
                    glyph_actor.SetMapper(glyph_mapper)
                    glyph_actor.GetProperty().SetAmbient(1.0)
                    glyph_actor.GetProperty().SetDiffuse(0.0)
                    glyph_actor.GetProperty().SetSpecular(0.0)

                    # 大型模型优化点的渲染属性 - 移除强制渲染为点
                    if self.is_large_model:
                        # glyph_actor.GetProperty().SetRepresentationToPoints() # <--- 注释掉
                        glyph_actor.GetProperty().SetPointSize(3) # 保留点大小设置，以防万一

                    self.renderer.AddActor(glyph_actor)
        
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
        
        # 标记为需要高质量渲染
        self.needs_high_res_render = True
        
        # 设置渲染器属性
        if self.is_interacting:
            update_rate = 30.0  # 交互期间使用高帧率
            if self.is_large_model:
                update_rate = 15.0  # 大模型使用更低的帧率
            self.vtk_widget.GetRenderWindow().SetDesiredUpdateRate(update_rate)
        else:
            update_rate = 0.0001  # 静态渲染使用高质量
            if self.is_large_model:
                update_rate = 0.001  # 大模型使用稍低的质量
            self.vtk_widget.GetRenderWindow().SetDesiredUpdateRate(update_rate)
        
        # 更新坐标轴方向指示器 - vtkOrientationMarkerWidget没有UpdateMarkerOrientation方法
        # 方向标记器会自动跟随相机方向
        
        self.vtk_widget.GetRenderWindow().Render()
        
        # 输出渲染性能调试信息
        end_time = time.time()
        #print(f"渲染耗时: {(end_time - start_time)*1000:.1f}ms")
    
    def delete_selected_faces(self):
        """删除选中的面"""
        if not self.selected_faces:
            QMessageBox.warning(self, '删除面', '请先选择要删除的面')
            return
            
        # 记录将要删除的面ID用于追踪
        deleted_face_ids = self.selected_faces.copy()
        
        # 创建一个布尔掩码，初始设置为全True
        mask = np.ones(len(self.mesh_data['faces']), dtype=bool)
        
        # 将选中的面对应的布尔值设置为False
        for face_id in self.selected_faces:
            mask[face_id] = False
        
        # 使用布尔掩码选择未被删除的面
        self.mesh_data['faces'] = self.mesh_data['faces'][mask]
        
        # 更新法线数组（如果存在）
        if 'normals' in self.mesh_data:
            if len(self.mesh_data['normals']) == len(mask):
                self.mesh_data['normals'] = self.mesh_data['normals'][mask]
            else:
                # 如果大小不匹配，删除法线数组
                del self.mesh_data['normals']
        
        self.selected_faces = []
        print("已删除选中的面")
        self.update_display()
        
        # 标记模型已经修改，追踪删除的面
        self.model_modified = True
        self.detection_cache = {k: None for k in self.detection_cache}
        if hasattr(self, 'model_tracker'):
            self.model_tracker.track_modification('faces', deleted_face_ids)
        
        # 由于模型已改变，重新进行检测
        self.update_model_analysis()
        self.statusBar.showMessage(f'已删除 {len(self.mesh_data["faces"])} 个面片')
    
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
        
        # 标记模型已经修改，清除缓存
        self.model_modified = True
        self.detection_cache = {k: None for k in self.detection_cache}
        
        # 由于模型已改变，重新进行检测
        self.update_model_analysis()
    
    def clear_selection(self):
        """清除当前选择"""
        if self.selection_mode == 'point':
            self.selected_points = []
        elif self.selection_mode == 'edge':
            self.selected_edges = []
            self.edge_selection_source = 'manual' # 重置边选择来源
        elif self.selection_mode == 'face':
            self.selected_faces = []
        # 更新显示
        self.update_display()
        # 不重置数字标签，只更新状态栏
        self.update_status_counts()
    
    def clear_points(self):
        """清除选中的点"""
        self.selected_points = []
        self.update_display()
        # 不重置点数量标签，只更新状态栏
        self.update_status_counts()
    
    def clear_edges(self):
        """清除所有选中的边"""
        self.selected_edges = []
        self.edge_selection_source = 'manual'  # 重置为手动选择模式
        self.update_display()
    
    def clear_faces(self):
        """清除选中的面"""
        self.selected_faces = []
        self.update_display()
        # 不重置面数量标签，只更新状态栏
        self.update_status_counts()
    
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
        
        # 性能优化：避免不必要的全分辨率渲染
        self.vtk_widget.GetRenderWindow().GetInteractor().SetDesiredUpdateRate(30.0)
        self.vtk_widget.GetRenderWindow().Render()
        
        # 方向指示器会自动跟随相机方向，不需要手动更新
    
    def clear_all_selections(self):
        """清除所有选择"""
        self.selected_faces = []
        self.selected_edges = []
        self.selected_points = []
        self.update_display()
        
        # 不重置数字标签，保持之前的分析结果
        # 只更新状态栏
        self.update_status_counts()
        self.statusBar.showMessage('已清除所有选择')

    def select_free_edges(self):
        """选择自由边"""
        try:
            # 检查是否有缓存结果且模型未修改
            if not self.model_modified and self.detection_cache['free_edges'] is not None:
                # 直接使用缓存结果 - 加载前先清空，并使用副本
                self.selected_edges = [] 
                self.selected_edges = self.detection_cache['free_edges'].copy() # 使用 .copy()
                self.edge_selection_source = 'auto'  # 设置为自动选择
                self.adjust_font_size(self.free_edge_count, str(len(self.selected_edges))) # 更新按钮旁边的标签
                self.update_display()
                print("使用缓存：自由边检测 (已选择 " + str(len(self.selected_edges)) + " 条边)")
                return
                
            # 显示进度对话框
            progress = QProgressDialog("检测自由边...", "取消", 0, 100, self)
            progress.setWindowTitle("自由边检测")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            progress.setValue(10)
            
            # 创建并执行自由边检测算法
            algorithm = FreeEdgesAlgorithm(self.mesh_data)
            # 注意：FreeEdgesAlgorithm的execute方法接受parent参数，不是progress_callback
            result = algorithm.execute(parent=self)
            
            # 更新选择
            if 'selected_edges' in result and result['selected_edges']:
                self.selected_edges = result['selected_edges']
                self.edge_selection_source = 'auto'  # 设置为自动选择
                # 缓存结果
                self.detection_cache['free_edges'] = self.selected_edges.copy()
                
                self.update_display()
                self.adjust_font_size(self.free_edge_count, str(len(self.selected_edges)))
                # 消息框由算法内部显示，无需在这里显示
            else:
                self.clear_edges()
                self.adjust_font_size(self.free_edge_count, "0")
                # 缓存结果（空列表）
                self.detection_cache['free_edges'] = []
                
                # 如果算法内部没有显示消息，则在这里显示
                if not hasattr(algorithm, 'message_shown') or not algorithm.message_shown:
                    QMessageBox.information(self, "检测完成", "未检测到自由边。")
            
            progress.setValue(100)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"自由边检测失败: {str(e)}")

    def select_overlapping_edges(self):
        """检测并选择重叠边"""
        try:
            # 检查是否有缓存结果且模型未修改
            if not self.model_modified and self.detection_cache['overlapping_edges'] is not None:
                # 直接使用缓存结果 - 加载前先清空，并使用副本
                self.selected_edges = []
                self.selected_edges = self.detection_cache['overlapping_edges'].copy() # 使用 .copy()
                self.edge_selection_source = 'auto'  # 设置为自动选择
                self.adjust_font_size(self.overlap_edge_count, str(len(self.selected_edges))) # 更新按钮旁边的标签
                self.update_display()
                print("使用缓存：重叠边检测 (已选择 " + str(len(self.selected_edges)) + " 条边)")
                return
                
            # 显示进度对话框
            progress = QProgressDialog("检测重叠边...", "取消", 0, 100, self)
            progress.setWindowTitle("重叠边检测")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            progress.setValue(10)
            
            # 创建并执行重叠边检测算法
            algorithm = OverlappingEdgesAlgorithm(self.mesh_data)
            result = algorithm.execute(parent=self)
            
            # 更新选择
            if 'selected_edges' in result and result['selected_edges']:
                self.selected_edges = result['selected_edges']
                self.edge_selection_source = 'auto'  # 设置为自动选择
                # 缓存结果
                self.detection_cache['overlapping_edges'] = self.selected_edges.copy()
                
                self.update_display()
                self.adjust_font_size(self.overlap_edge_count, str(len(self.selected_edges)))
                # 消息框由算法内部显示，无需在这里显示
            else:
                self.clear_edges()
                self.adjust_font_size(self.overlap_edge_count, "0")
                # 缓存结果（空列表）
                self.detection_cache['overlapping_edges'] = []
                
                # 如果算法内部没有显示消息，则在这里显示
                if not hasattr(algorithm, 'message_shown') or not algorithm.message_shown:
                    QMessageBox.information(self, "检测完成", "未检测到重叠边。")
                
            progress.setValue(100)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"重叠边检测失败: {str(e)}")

    def detect_face_intersections(self):
        """检测面片交叉"""
        try:
            # 检查是否有缓存结果且模型未修改
            if not self.model_modified and self.detection_cache['face_intersections'] is not None:
                # 直接使用缓存结果 - 使用副本并更新标签
                self.selected_faces = self.detection_cache['face_intersections'].copy() # 使用 .copy()
                # 如果缓存中有相交映射关系，也一并恢复
                if 'face_intersection_map' in self.detection_cache and self.detection_cache['face_intersection_map'] is not None:
                    self.face_intersection_map = self.detection_cache['face_intersection_map'].copy() # 使用 .copy()
                else:
                    self.face_intersection_map = {} # 确保如果缓存中没有map，则初始化为空
                self.adjust_font_size(self.intersection_count, str(len(self.selected_faces))) # 更新按钮旁边的标签
                self.update_display()
                print("使用缓存：交叉面检测 (已选择 " + str(len(self.selected_faces)) + " 个面)")
                return
                
            # 显示进度对话框
            progress = QProgressDialog("检测穿刺面...", "取消", 0, 100, self)
            progress.setWindowTitle("穿刺面检测")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            progress.setValue(10)
            
            # 设置增强CPP优先的配置
            cpp_preference = {
                "use_cpp": True,
                "force_enhanced": hasattr(self, 'has_enhanced_pierced_faces') and self.has_enhanced_pierced_faces
            }
            
            # 创建并执行穿刺面检测算法 - 使用新的合并算法，设置detection_mode="pierced"
            from algorithms.combined_intersection_algorithm import CombinedIntersectionAlgorithm
            algorithm = CombinedIntersectionAlgorithm(self.mesh_data, detection_mode="pierced")
            
            # 如果存在增强模块，设置增强标志
            if hasattr(self, 'has_enhanced_pierced_faces'):
                algorithm.enhanced_cpp_available = self.has_enhanced_pierced_faces
            
            result = algorithm.execute(parent=self)
            
            # 获取运行时间信息
            detection_time = result.get('detection_time', 0)
            total_time = result.get('total_time', 0)
            
            # 更新选择和相交关系
            if 'selected_faces' in result and result['selected_faces']:
                self.selected_faces = result['selected_faces']
                # 保存相交映射关系
                if 'intersection_map' in result:
                    self.face_intersection_map = {int(k): v for k, v in result['intersection_map'].items()}
                else:
                    self.face_intersection_map = {}
                
                # 缓存结果
                self.detection_cache['face_intersections'] = self.selected_faces.copy()
                self.detection_cache['face_intersection_map'] = self.face_intersection_map.copy() if hasattr(self, 'face_intersection_map') else {}
                
                # 获取相交关系总数
                total_intersections = result.get('total_intersections', 0)
                
                self.update_display()
                self.adjust_font_size(self.intersection_count, str(len(self.selected_faces)))
                
                # 显示更详细的相交信息
                if not hasattr(algorithm, 'message_shown') or not algorithm.message_shown:
                    relation_info = f"发现{len(self.selected_faces)}个穿刺面，共有{total_intersections}对相交关系。"
                    cpp_info = ""
                    
                    # 添加关于使用的模块信息
                    if hasattr(algorithm, 'used_enhanced_cpp') and algorithm.used_enhanced_cpp:
                        cpp_info = "\n已使用增强版C++模块(支持完整相交关系映射)"
                    elif hasattr(algorithm, 'use_cpp') and algorithm.use_cpp:
                        cpp_info = "\n已使用基础版C++模块"
                        
                    QMessageBox.information(self, "检测完成", relation_info + cpp_info)
                    
            else:
                self.clear_faces()
                self.face_intersection_map = {}
                self.adjust_font_size(self.intersection_count, "0")
                # 缓存结果（空列表）
                self.detection_cache['face_intersections'] = []
                self.detection_cache['face_intersection_map'] = {}
                
                # 如果算法内部没有显示消息，则在这里显示
                if not hasattr(algorithm, 'message_shown') or not algorithm.message_shown:
                    QMessageBox.information(self, "检测完成", f"未检测到穿刺面。\n检测用时: {detection_time:.4f}秒\n总用时: {total_time:.4f}秒")
                
            progress.setValue(100)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"穿刺面检测失败: {str(e)}")

    def analyze_face_quality(self):
        """分析面片质量"""
        try:
            # 检查是否有缓存结果且模型未修改
            if not self.model_modified and self.detection_cache['face_quality'] is not None:
                # 直接使用缓存结果 - 使用副本并更新标签
                self.selected_faces = self.detection_cache['face_quality'].copy() # 使用 .copy()
                self.adjust_font_size(self.quality_count, str(len(self.selected_faces))) # 更新按钮旁边的标签
                self.update_display()
                print("使用缓存：面片质量分析 (已选择 " + str(len(self.selected_faces)) + " 个面)")
                return
                
            # 获取用户输入的质量阈值
            threshold, ok = QInputDialog.getDouble(
                self, "设置面片质量阈值", 
                "请输入质量阈值 (0.1-0.5)，较小的值检测更严格:", 
                0.3, 0.1, 0.5, 2)
            
            if not ok:
                return
                
            # 显示进度对话框
            progress = QProgressDialog("准备分析面片质量...", "取消", 0, 100, self)
            progress.setWindowTitle("面片质量分析")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            progress.setValue(5)
            
            # 检查是否可以使用C++实现
            try:
                import face_quality_cpp
                has_cpp = True
                progress.setLabelText("使用C++算法分析面片质量（高性能模式）...")
            except ImportError:
                has_cpp = False
                progress.setLabelText("使用Python算法分析面片质量（未找到C++模块）...")
                # 显示推荐安装C++模块的提示
                self.statusBar.showMessage("提示: 安装C++模块可显著提高性能")
            
            progress.setValue(10)
            
            # 创建并执行面片质量分析算法，明确设置use_cpp=True
            algorithm = FaceQualityAlgorithm(self.mesh_data, threshold=threshold)
            algorithm.use_cpp = has_cpp  # 明确设置是否使用C++
            
            # 执行算法
            result = algorithm.execute(parent=self)
            
            # 更新选择
            if 'selected_faces' in result and result['selected_faces']:
                self.selected_faces = result['selected_faces']
                # 缓存结果
                self.detection_cache['face_quality'] = self.selected_faces.copy()
                
                self.update_display()
                self.adjust_font_size(self.quality_count, str(len(self.selected_faces)))
                
                # 显示质量报告
                if 'report' in result and not hasattr(algorithm, 'message_shown'):
                    QMessageBox.information(
                        self, "质量分析完成", 
                        f"找到 {len(self.selected_faces)} 个低质量面片。\n\n{result['report']}"
                    )
                
                # 在状态栏显示结果
                if has_cpp:
                    self.statusBar.showMessage(f"检测到 {len(self.selected_faces)} 个低质量面片 (C++算法，阈值 < {threshold})")
                else:
                    self.statusBar.showMessage(f"检测到 {len(self.selected_faces)} 个低质量面片 (Python算法，阈值 < {threshold})")
            else:
                self.clear_faces()
                self.adjust_font_size(self.quality_count, "0")
                # 缓存结果（空列表）
                self.detection_cache['face_quality'] = []
                
                if not hasattr(algorithm, 'message_shown') or not algorithm.message_shown:
                    QMessageBox.information(self, "质量分析完成", "未检测到低质量面片。")
                
                # 在状态栏显示结果
                if has_cpp:
                    self.statusBar.showMessage(f"未检测到低质量面片 (C++算法，阈值 < {threshold})")
                else:
                    self.statusBar.showMessage(f"未检测到低质量面片 (Python算法，阈值 < {threshold})")
                
            progress.setValue(100)
            
        except Exception as e:
            import traceback
            error_msg = f"面片质量分析失败: {str(e)}\n{traceback.format_exc()}"
            QMessageBox.critical(self, "错误", error_msg)
            self.statusBar.showMessage("面片质量分析失败")

    def select_adjacent_faces(self):
        """分析面片邻近性，使用C++实现"""
        try:
            # 检查是否有缓存结果且模型未修改
            if not self.model_modified and self.detection_cache['adjacent_faces'] is not None:
                # 直接使用缓存结果
                self.selected_faces = self.detection_cache['adjacent_faces']
                self.update_display()
                print("使用缓存：相邻面分析 (已选择 " + str(len(self.selected_faces)) + " 个面)")
                return
                
            # 检查mesh_data是否有效
            if not self.mesh_data or 'vertices' not in self.mesh_data or 'faces' not in self.mesh_data:
                QMessageBox.warning(self, "数据错误", "无效的网格数据，请先加载有效的3D模型。")
                self.statusBar.showMessage("邻近性分析失败：无效的网格数据")
                return
                
            # 检查顶点和面片数据
            if len(self.mesh_data['vertices']) == 0 or len(self.mesh_data['faces']) == 0:
                QMessageBox.warning(self, "数据错误", "模型没有顶点或面片数据。")
                self.statusBar.showMessage("邻近性分析失败：模型没有有效数据")
                return
            
            # 获取用户输入的邻近阈值
            threshold, ok = QInputDialog.getDouble(
                self, "设置面片邻近性阈值", 
                "请输入邻近性阈值 (0-1)，较小的值检测更严格:", 
                0.1, 0.0, 1.0, 2)
            
            if not ok:
                return
                
            # 显示进度对话框
            progress = QProgressDialog("分析面片邻近性...", "取消", 0, 100, self)
            progress.setWindowTitle("面片邻近性分析")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            # 使用adjacent_faces_cpp模块（专用C++实现）
            try:
                # 使用绝对导入路径以确保找到正确的模块
                import sys
                import os
                # 添加当前工作目录到路径中，确保可以找到正确的模块
                current_dir = os.getcwd()
                if current_dir not in sys.path:
                    sys.path.insert(0, current_dir)
                # 同时尝试添加src目录到路径中
                src_dir = os.path.join(current_dir, "src")
                if os.path.exists(src_dir) and src_dir not in sys.path:
                    sys.path.insert(0, src_dir)
                
                # 重新导入模块
                if 'adjacent_faces_cpp' in sys.modules:
                    del sys.modules['adjacent_faces_cpp']
                import adjacent_faces_cpp
                
                progress.setLabelText("使用C++专用算法检测相邻面...")
                print(f"成功导入模块，可用函数: {[f for f in dir(adjacent_faces_cpp) if not f.startswith('__')]}")
                
                # 检查模块是否包含expected方法
                if not hasattr(adjacent_faces_cpp, 'detect_adjacent_faces_with_timing'):
                    raise AttributeError("导入的C++模块缺少必要的函数：detect_adjacent_faces_with_timing")
            except ImportError as e:
                QMessageBox.critical(self, "错误", f"无法导入adjacent_faces_cpp模块: {e}\n请确保已正确编译C++扩展。")
                self.statusBar.showMessage("邻近性分析失败：未找到C++模块")
                progress.close()
                return
            except AttributeError as e:
                QMessageBox.critical(self, "错误", str(e))
                self.statusBar.showMessage("邻近性分析失败：C++模块不完整")
                progress.close()
                return
            
            progress.setValue(20)
            
            # 转换数据为numpy数组
            import numpy as np
            vertices_np = np.array(self.mesh_data['vertices'], dtype=np.float32)
            faces_np = np.array(self.mesh_data['faces'], dtype=np.int32)
            
            # 调用C++模块
            start_time = time.time()
            
            try:
                # 调用C++扩展模块的函数
                print(f"准备调用C++函数，传递参数: vertices形状={vertices_np.shape}, faces形状={faces_np.shape}, threshold={threshold}")
                adjacent_pairs, execution_time = adjacent_faces_cpp.detect_adjacent_faces_with_timing(
                    vertices_np, faces_np, proximity_threshold=float(threshold)
                )
                
                print(f"C++函数返回类型: 相邻对={type(adjacent_pairs)}, 执行时间={type(execution_time)}")
                
                progress.setValue(80)
                
                # 将相邻面对转换为选中面片列表
                face_set = set()
                # 确保adjacent_pairs是可迭代的
                if adjacent_pairs is not None:
                    for pair in adjacent_pairs:
                        if isinstance(pair, tuple) or isinstance(pair, list):
                            i, j = pair
                            face_set.add(int(i))
                            face_set.add(int(j))
                        else:
                            print(f"警告: 意外的相邻对格式: {type(pair)}")
                
                selected_faces = list(face_set)
                
                end_time = time.time()
                total_time = end_time - start_time
                
                print(f"已使用C++算法检测到{len(selected_faces)}个相邻面")
                print(f"C++内部执行时间: {execution_time:.4f}秒")
                print(f"总处理时间: {total_time:.4f}秒")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"调用C++模块失败: {str(e)}")
                self.statusBar.showMessage("邻近性分析失败：C++模块执行错误")
                progress.close()
                return
            
            # 更新选择
            if selected_faces:
                self.selected_faces = selected_faces
                # 缓存结果
                self.detection_cache['adjacent_faces'] = self.selected_faces.copy()
                
                self.update_display()
                self.adjust_font_size(self.proximity_count, str(len(self.selected_faces)))
                
                # 显示结果 (修复缩进错误)
                total_faces = len(self.mesh_data['faces'])
                percentage = len(self.selected_faces) / total_faces * 100 if total_faces > 0 else 0
                QMessageBox.information(
                    self, "邻近性分析完成", 
                    f"检测到 {len(self.selected_faces)} 个邻近面片 (根据定义: 相交或邻近度 <= {threshold:.2f})，占总面片数的 {percentage:.2f}%。\n"
                    f"C++执行时间: {execution_time:.4f}秒"
                )
                
                # 在状态栏显示结果
                self.statusBar.showMessage(f"检测到 {len(self.selected_faces)} 个邻近面片 (阈值={threshold:.2f}, C++实现)")
            else:
                self.clear_faces()
                self.adjust_font_size(self.proximity_count, "0")
                # 缓存结果（空列表）
                self.detection_cache['adjacent_faces'] = []
                
                # 显示结果
                QMessageBox.information(
                    self, "邻近性分析完成", 
                    f"未检测到邻近面片 (阈值={threshold:.2f})。\nC++执行时间: {execution_time:.4f}秒"
                )
                
                # 在状态栏显示结果
                self.statusBar.showMessage(f"未检测到邻近面片 (阈值={threshold:.2f}, C++实现)")
                
            progress.setValue(100)
            
        except Exception as e:
            import traceback
            error_msg = f"邻近性分析失败: {str(e)}\n{traceback.format_exc()}"
            QMessageBox.critical(self, "错误", error_msg)
            self.statusBar.showMessage("邻近性分析失败")

    def select_overlapping_points(self):
        """检测并选择重叠点"""
        try:
            # 检查是否有缓存结果且模型未修改
            if not self.model_modified and self.detection_cache['overlapping_points'] is not None:
                # 直接使用缓存结果 - 使用副本并更新标签
                self.selected_points = self.detection_cache['overlapping_points'].copy() # 使用 .copy()
                self.adjust_font_size(self.overlap_point_count, str(len(self.selected_points))) # 更新按钮旁边的标签
                self.update_display()
                print("使用缓存：重叠点检测 (已选择 " + str(len(self.selected_points)) + " 个点)")
                return
                  
            # 显示进度对话框
            progress = QProgressDialog("检测重叠点...", "取消", 0, 100, self)
            progress.setWindowTitle("重叠点检测")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            progress.setValue(10)
            
            # 检查可用的C++模块
            has_cpp = False
            try:
                import non_manifold_vertices_cpp
                has_cpp = True
                progress.setLabelText("使用C++算法检测重叠点（non_manifold_vertices_cpp模块）...")
            except ImportError:
                try:
                    import overlapping_points_cpp
                    has_cpp = True
                    progress.setLabelText("使用C++算法检测重叠点（overlapping_points_cpp模块）...")
                except ImportError:
                    has_cpp = False
                    progress.setLabelText("使用Python算法检测重叠点...")
                    print("警告：未找到C++模块，将使用较慢的Python实现")
            
            # 使用合并后的顶点检测算法
            from algorithms.merged_vertex_detection_algorithm import MergedVertexDetectionAlgorithm
            algorithm = MergedVertexDetectionAlgorithm(self.mesh_data, detection_mode="overlapping")
            
            # 强制使用C++实现（如果可用）
            algorithm.use_cpp = has_cpp
            
            # 执行算法
            result = algorithm.execute(parent=self)
            
            # 更新选择
            if 'selected_points' in result and result['selected_points']:
                self.selected_points = result['selected_points']
                # 同时确保mesh_data中有相同的结果
                self.mesh_data['non_manifold_vertices'] = self.selected_points.copy()
                
                # 缓存结果
                self.detection_cache['overlapping_points'] = self.selected_points.copy()
                
                # 更新显示
                self.update_display()
                self.adjust_font_size(self.overlap_point_count, str(len(self.selected_points)))
                
                # 显示结果
                if not hasattr(algorithm, 'message_shown') or not algorithm.message_shown:
                    total_points = len(self.mesh_data['vertices'])
                    percentage = len(self.selected_points) / total_points * 100 if total_points > 0 else 0
                    
                    # 显示不同的消息，取决于使用的是哪种实现
                    cpp_info = "C++算法" if algorithm.use_cpp else "Python算法"
                    QMessageBox.information(
                        self, "重叠点检测完成", 
                        f"检测到 {len(self.selected_points)} 个重叠点，占总点数的 {percentage:.2f}%。\n已使用{cpp_info}"
                    )
                
                # 在状态栏显示结果
                cpp_info = "C++算法" if algorithm.use_cpp else "Python算法"
                self.statusBar.showMessage(f"检测到 {len(self.selected_points)} 个重叠点 ({cpp_info})")
            else:
                self.clear_points()
                self.adjust_font_size(self.overlap_point_count, "0")
                
                # 缓存结果（空列表）
                self.detection_cache['overlapping_points'] = []
                
                if not hasattr(algorithm, 'message_shown') or not algorithm.message_shown:
                    cpp_info = "C++算法" if algorithm.use_cpp else "Python算法"
                    QMessageBox.information(self, "重叠点检测完成", f"未检测到重叠点。\n已使用{cpp_info}")
                
                # 在状态栏显示结果
                cpp_info = "C++算法" if algorithm.use_cpp else "Python算法"
                self.statusBar.showMessage(f"未检测到重叠点 ({cpp_info})")
                
            progress.setValue(100)
            
        except Exception as e:
            import traceback
            error_msg = f"重叠点检测失败: {str(e)}\n{traceback.format_exc()}"
            QMessageBox.critical(self, "错误", error_msg)
            self.statusBar.showMessage("重叠点检测失败")

    def toggle_performance_mode(self):
        """切换性能模式，在高性能和高质量模式之间切换"""
        self.high_performance_mode = not self.high_performance_mode
        
        # 更新窗口标题
        mode_name = "高性能模式" if self.high_performance_mode else "高质量模式"
        self.setWindowTitle(f'Mesh Viewer - {mode_name}')
        
        # 更新状态栏
        self.statusBar.showMessage(f"已切换为{mode_name}")
        
        # 更新渲染设置
        self.update_display()

    def keyPressEvent(self, event):
        """处理键盘事件"""
        # 各种选择模式的快捷键
        if event.key() == Qt.Key_V:
            self.set_selection_mode('point')
        elif event.key() == Qt.Key_E:
            self.set_selection_mode('edge')
        elif event.key() == Qt.Key_F:
            self.set_selection_mode('face')
            
        # 清除选择的快捷键
        elif event.key() == Qt.Key_Escape:
            self.clear_selection()
            
        # 删除选中面片的快捷键
        elif event.key() == Qt.Key_Delete:
            self.delete_selected_faces()
        
        # 高性能/高质量模式切换
        elif event.key() == Qt.Key_P:
            self.toggle_performance_mode()
        
        # 坐标轴显示切换
        elif event.key() == Qt.Key_A:
            self.toggle_axes_visibility()
            
        # 使用I键查看当前选中面片的相交关系
        elif event.key() == Qt.Key_I:
            if self.selection_mode == 'face' and len(self.selected_faces) == 1:
                self.show_face_intersections(self.selected_faces[0])
            elif self.selection_mode == 'face' and len(self.selected_faces) > 1:
                QMessageBox.information(self, "信息", "请仅选择一个面片来查看其相交关系。")
            else:
                QMessageBox.information(self, "信息", "请先选择一个面片。")
        
        # 其他键保持默认处理
        else:
            super().keyPressEvent(event)

    def toggle_axes_visibility(self):
        """切换坐标轴方向指示器的显示/隐藏"""
        if hasattr(self, 'orientation_marker') and self.orientation_marker is not None:
            # 切换坐标轴的可见性
            is_visible = self.orientation_marker.GetEnabled()
            self.orientation_marker.SetEnabled(not is_visible)
            
            # 更新状态栏信息
            if not is_visible:
                self.statusBar.showMessage('已显示坐标轴方向指示器')
            else:
                self.statusBar.showMessage('已隐藏坐标轴方向指示器')
            
            # 强制重新渲染
            self.vtk_widget.GetRenderWindow().Render()

    def store_current_view(self, restore_view_menu):
        """存储当前视图并生成截图"""
        # 获取当前视图的相机参数
        camera = self.renderer.GetActiveCamera()
        view_data = {
            'position': camera.GetPosition(),
            'focal_point': camera.GetFocalPoint(),
            'view_up': camera.GetViewUp(),
            'view_angle': camera.GetViewAngle(),
            'parallel_scale': camera.GetParallelScale()
        }
        
        # 生成小截图
        render_window = self.vtk_widget.GetRenderWindow()
        render_window.Render()
        
        # 获取渲染窗口的图像
        w2if = vtk.vtkWindowToImageFilter()
        w2if.SetInput(render_window)
        w2if.SetScale(1)  # 保持原始大小
        w2if.Update()
        
        # 将VTK图像转换为QImage
        vtk_image = w2if.GetOutput()
        width = vtk_image.GetDimensions()[0]
        height = vtk_image.GetDimensions()[1]
        
        # 创建QImage
        qimage = QImage(width, height, QImage.Format_RGB888)
        
        # 将VTK图像数据复制到QImage
        for y in range(height):
            for x in range(width):
                pixel = vtk_image.GetScalarComponentAsFloat(x, y, 0, 0)
                r = int(pixel * 255)
                g = int(vtk_image.GetScalarComponentAsFloat(x, y, 0, 1) * 255)
                b = int(vtk_image.GetScalarComponentAsFloat(x, y, 0, 2) * 255)
                qimage.setPixel(x, y, qRgb(r, g, b))
        
        # 缩放图像为小图标大小
        thumbnail = qimage.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # 创建图标
        icon = QIcon(QPixmap.fromImage(thumbnail))
        
        # 增加计数器
        self.view_counter += 1
        
        # 创建新的菜单项
        view_name = f"View {self.view_counter}"
        view_action = QAction(icon, view_name, self)
        
        # 存储视图数据
        self.stored_views.append({
            'data': view_data,
            'action': view_action
        })
        
        # 将新视图添加到菜单的最前面
        restore_view_menu.insertAction(restore_view_menu.actions()[0] if restore_view_menu.actions() else None, view_action)
        
        # 连接恢复视图的信号
        view_action.triggered.connect(lambda: self.restore_specific_view(view_data))
        
        # 显示状态消息
        self.statusBar.showMessage(f'已存储视图 {self.view_counter}')
    
    def restore_specific_view(self, view_data):
        """恢复特定的存储视图"""
        camera = self.renderer.GetActiveCamera()
        camera.SetPosition(view_data['position'])
        camera.SetFocalPoint(view_data['focal_point'])
        camera.SetViewUp(view_data['view_up'])
        camera.SetViewAngle(view_data['view_angle'])
        camera.SetParallelScale(view_data['parallel_scale'])
        self.vtk_widget.GetRenderWindow().Render()
        self.statusBar.showMessage('已恢复存储的视图')

    def set_projection_mode(self, mode):
        """设置投影模式"""
        camera = self.renderer.GetActiveCamera()
        if mode == "perspective":
            camera.SetParallelProjection(False)
            self.statusBar.showMessage('已切换到透视投影模式')
        else:  # parallel
            camera.SetParallelProjection(True)
            self.statusBar.showMessage('已切换到平行投影模式')
        self.vtk_widget.GetRenderWindow().Render()

    def set_standard_view(self, view_type):
        """设置标准视图"""
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
        
        # 根据视图类型设置相机位置和方向
        if view_type == "front":
            camera.SetPosition(center[0], center[1], center[2] + diagonal)
            camera.SetFocalPoint(center[0], center[1], center[2])
            camera.SetViewUp(0, 1, 0)
            self.statusBar.showMessage('已切换到前视图')
            
        elif view_type == "back":
            camera.SetPosition(center[0], center[1], center[2] - diagonal)
            camera.SetFocalPoint(center[0], center[1], center[2])
            camera.SetViewUp(0, 1, 0)
            self.statusBar.showMessage('已切换到后视图')
            
        elif view_type == "left":
            camera.SetPosition(center[0] - diagonal, center[1], center[2])
            camera.SetFocalPoint(center[0], center[1], center[2])
            camera.SetViewUp(0, 1, 0)
            self.statusBar.showMessage('已切换到左视图')
            
        elif view_type == "right":
            camera.SetPosition(center[0] + diagonal, center[1], center[2])
            camera.SetFocalPoint(center[0], center[1], center[2])
            camera.SetViewUp(0, 1, 0)
            self.statusBar.showMessage('已切换到右视图')
            
        elif view_type == "top":
            camera.SetPosition(center[0], center[1] + diagonal, center[2])
            camera.SetFocalPoint(center[0], center[1], center[2])
            camera.SetViewUp(0, 0, -1)
            self.statusBar.showMessage('已切换到顶视图')
            
        elif view_type == "bottom":
            camera.SetPosition(center[0], center[1] - diagonal, center[2])
            camera.SetFocalPoint(center[0], center[1], center[2])
            camera.SetViewUp(0, 0, 1)
            self.statusBar.showMessage('已切换到底视图')
            
        elif view_type == "isometric":
            # 等轴测视图：从45度角观察
            distance = diagonal * 1.5
            camera.SetPosition(center[0] + distance, center[1] + distance, center[2] + distance)
            camera.SetFocalPoint(center[0], center[1], center[2])
            camera.SetViewUp(0, 0, 1)
            self.statusBar.showMessage('已切换到等轴测视图')
        
        # 更新渲染
        self.renderer.ResetCameraClippingRange()
        self.vtk_widget.GetRenderWindow().Render()

    def update_model_analysis(self):
        """更新模型分析"""
        # 使用新的局部检测优化算法
        if hasattr(self, 'model_tracker'):
            # 如果是初次分析，先初始化缓存
            if self.model_modified:
                self.model_tracker.initialize_cache()
            
            # 执行增量更新
            updates = self.model_tracker.update_analysis()
            
            # 根据更新结果调整界面显示
            if updates:
                if hasattr(self, 'intersection_count') and '交叉面' in updates:
                    count = self.model_tracker.get_button_counts()['交叉面']
                    self.adjust_font_size(self.intersection_count, str(count))
                
                if hasattr(self, 'quality_count') and '面质量' in updates:
                    count = self.model_tracker.get_button_counts()['面质量']
                    self.adjust_font_size(self.quality_count, str(count))
                
                if hasattr(self, 'free_edge_count') and '自由边' in updates:
                    count = self.model_tracker.get_button_counts()['自由边']
                    self.adjust_font_size(self.free_edge_count, str(count))
                
                if hasattr(self, 'overlap_edge_count') and '重叠边' in updates:
                    count = self.model_tracker.get_button_counts()['重叠边']
                    self.adjust_font_size(self.overlap_edge_count, str(count))
                
                if hasattr(self, 'overlap_point_count') and '重叠点' in updates:
                    count = self.model_tracker.get_button_counts()['重叠点']
                    self.adjust_font_size(self.overlap_point_count, str(count))
                
                # 更新界面显示
                self.update_display()
            
            # 清除模型修改标记
            self.model_modified = False
            
            # 在状态栏显示性能统计
            stats = self.model_tracker.get_performance_stats()
            self.statusBar.showMessage(f"分析完成: 局部更新 {stats['local_updates']} 次, 全局更新 {stats['full_updates']} 次, 估计节省时间 {stats['time_saved']:.2f} 秒")
            
            return
            
        # 旧的全局检测算法（仅在模型变更追踪器不可用时使用）
        # 重置模型修改状态，表示此次分析之后模型处于未修改状态
        self.model_modified = False
        
        # 检查模型是否足够小以便进行分析
        if not self.mesh_data or 'faces' not in self.mesh_data or len(self.mesh_data['faces']) > 100000:
            # 模型太大，不进行自动分析
            return
        
        # 静默运行各种检测，而不显示进度条和结果消息
        had_free_edge_analysis = hasattr(self, 'free_edge_count')
        had_overlap_edge_analysis = hasattr(self, 'overlap_edge_count')
        had_intersection_analysis = hasattr(self, 'intersection_count')
        had_quality_analysis = hasattr(self, 'quality_count')
        had_proximity_analysis = hasattr(self, 'proximity_count')
        had_overlap_point_analysis = hasattr(self, 'overlap_point_count')
        
        # 根据先前的分析结果，决定要运行哪些分析
        if had_free_edge_analysis:
            # 静默运行自由边检测
            self.run_silent_detection(self.select_free_edges, "自由边")
        
        if had_overlap_edge_analysis:
            # 静默运行重叠边检测
            self.run_silent_detection(self.select_overlapping_edges, "重叠边")
        
        if had_intersection_analysis:
            # 静默运行交叉面检测
            self.run_silent_detection(self.detect_face_intersections, "交叉面")
        
        if had_quality_analysis:
            # 静默运行面片质量分析
            self.run_silent_detection(self.analyze_face_quality, "面质量")
        
        if had_proximity_analysis:
            # 静默运行相邻面分析
            self.run_silent_detection(self.select_adjacent_faces, "相邻面")
        
        if had_overlap_point_analysis:
            # 静默运行重叠点检测
            self.run_silent_detection(self.select_overlapping_points, "重叠点")
    
    def run_silent_detection(self, detection_func, detection_type):
        """静默运行检测函数（不显示进度条和消息）"""
        try:
            # 备份当前选择状态
            temp_faces = self.selected_faces.copy() if self.selected_faces else []
            temp_edges = self.selected_edges.copy() if self.selected_edges else []
            temp_points = self.selected_points.copy() if self.selected_points else []
            
            # 根据检测类型创建并执行相应的算法
            if detection_type == "自由边":
                algorithm = FreeEdgesAlgorithm(self.mesh_data)
                # 使用None作为parent参数，避免显示消息对话框
                result = algorithm.execute(parent=None)
                if 'selected_edges' in result:
                    selection = result['selected_edges']
                    self.adjust_font_size(self.free_edge_count, str(len(selection)))
            
            elif detection_type == "重叠边":
                algorithm = OverlappingEdgesAlgorithm(self.mesh_data)
                result = algorithm.execute(parent=None)
                if 'selected_edges' in result:
                    selection = result['selected_edges']
                    self.adjust_font_size(self.overlap_edge_count, str(len(selection)))
            
            elif detection_type == "交叉面":
                algorithm = CombinedIntersectionAlgorithm(self.mesh_data)
                result = algorithm.execute(parent=None)
                if 'selected_faces' in result:
                    selection = result['selected_faces']
                    self.adjust_font_size(self.intersection_count, str(len(selection)))
            
            elif detection_type == "面质量":
                # 尝试导入并使用C++模块
                try:
                    import face_quality_cpp
                    has_cpp = True
                except ImportError:
                    has_cpp = False
                
                # 创建算法实例并明确设置是否使用C++
                algorithm = FaceQualityAlgorithm(self.mesh_data)
                algorithm.use_cpp = has_cpp  # 明确设置使用C++
                
                # 执行算法
                result = algorithm.execute(parent=None)
                
                # 更新界面显示
                if 'selected_faces' in result:
                    selection = result['selected_faces']
                    self.adjust_font_size(self.quality_count, str(len(selection)))
                    
                    # 在状态栏显示使用的算法类型
                    if has_cpp:
                        self.statusBar.showMessage(f"面质量检测完成 (C++算法)")
                    else:
                        self.statusBar.showMessage(f"面质量检测完成 (Python算法)")
            
            elif detection_type == "相邻面":
                # 检查可用的C++模块
                has_cpp = False
                try:
                    import self_intersection_cpp
                    has_cpp = True
                except ImportError:
                    has_cpp = False
                    print("警告：静默检测未找到相邻面检测C++模块，将使用较慢的Python实现")
                
                # 创建算法并强制使用C++实现（如果可用）
                algorithm = CombinedIntersectionAlgorithm(self.mesh_data, detection_mode="adjacent")
                algorithm.use_cpp = has_cpp  # 强制使用C++实现（如果可用）
                
                result = algorithm.execute(parent=None)
                if 'selected_faces' in result:
                    selection = result['selected_faces']
                    self.adjust_font_size(self.proximity_count, str(len(selection)))
                    
                    # 在状态栏显示使用的算法类型
                    if has_cpp:
                        self.statusBar.showMessage(f"相邻面检测完成 (C++高性能算法)")
                    else:
                        self.statusBar.showMessage(f"相邻面检测完成 (Python算法)")
            
            elif detection_type == "重叠点":
                # 检查可用的C++模块
                has_cpp = False
                try:
                    import non_manifold_vertices_cpp
                    has_cpp = True
                except ImportError:
                    try:
                        import overlapping_points_cpp
                        has_cpp = True
                    except ImportError:
                        has_cpp = False
                        print("警告：静默检测未找到C++模块，将使用较慢的Python实现")
                
                # 使用合并后的顶点检测算法
                from algorithms.merged_vertex_detection_algorithm import MergedVertexDetectionAlgorithm
                algorithm = MergedVertexDetectionAlgorithm(self.mesh_data, detection_mode="overlapping")
                
                # 强制使用C++实现（如果可用）
                algorithm.use_cpp = has_cpp
                
                # 执行算法
                result = algorithm.execute(parent=None)
                
                # 获取检测结果
                if 'selected_points' in result and result['selected_points']:
                    selection = result['selected_points']
                    self.adjust_font_size(self.overlap_point_count, str(len(selection)))
            
            # 还原之前的选择状态
            self.selected_faces = temp_faces
            self.selected_edges = temp_edges
            self.selected_points = temp_points
            self.update_display()
                
        except Exception as e:
            # 静默捕获异常，不显示错误消息
            print(f"静默检测时发生错误: {detection_type} - {str(e)}")

    def mark_model_modified(self):
        """标记模型已修改，并追踪变更"""
        self.model_modified = True
        self.detection_cache = {k: None for k in self.detection_cache}
        
        # 如果有模型变更追踪器，则记录当前修改的元素
        if hasattr(self, 'model_tracker'):
            # 从当前选择中获取修改的元素ID
            if self.selected_points:
                self.model_tracker.track_modification('points', self.selected_points)
            if self.selected_edges:
                self.model_tracker.track_modification('edges', self.selected_edges)
            if self.selected_faces:
                self.model_tracker.track_modification('faces', self.selected_faces)
        
        print("模型已修改，检测缓存已清除")

    def toggle_checkbox(self, index):
        """切换复选框状态"""
        self.toggle_states[index] = not self.toggle_states[index]
        # 更新按钮外观
        sender = self.sender()
        if self.toggle_states[index]:
            sender.setText("✓")
        else:
            sender.setText("")
        
        # 这里只是切换状态，后续可以添加实际功能
        print(f"切换按钮 {index} 状态变为: {self.toggle_states[index]}")

    def handle_nav_button(self, index):
        """处理导航按钮点击"""
        # 导航按钮名称列表，用于输出信息
        nav_names = ["首个", "上一个", "下一个", "末个"]
        
        # 临时变色反馈，然后恢复原色
        sender = self.sender()
        original_style = sender.styleSheet()
        
        # 设置点击反馈样式（临时变色）
        sender.setStyleSheet("""
            QPushButton {
                background-color: #aaddff;
                color: #333333;
                border: 1px solid #3399ff;
                border-radius: 4px;
                padding: 2px;
            }
        """)
        
        # 打印操作信息
        print(f"点击了{nav_names[index]}导航按钮")
        
        # 使用计时器在短暂延迟后恢复按钮样式
        QTimer.singleShot(200, lambda: sender.setStyleSheet(original_style))
        
        # 实际功能可以在此处添加

    def toggle_function_button(self, index):
        """切换功能按钮状态"""
        self.function_button_states[index] = not self.function_button_states[index]
        
        # 更新按钮样式
        sender = self.sender()
        
        if self.function_button_states[index]:
            # 激活状态 - 绿色
            sender.setStyleSheet("""
                QPushButton {
                    background-color: #90EE90;  /* 浅绿色 */
                    color: #006400;  /* 深绿色文字 */
                    border: 1px solid #2E8B57;  /* 海绿色边框 */
                    border-radius: 4px;
                    padding: 2px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #7CFC00;  /* 草绿色悬停 */
                    border-color: #006400;
                }
            """)
        else:
            # 未激活状态 - 灰色
            sender.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;  /* 浅灰色 */
                    color: #333333;  /* 深灰色文字 */
                    border: 1px solid #999999;  /* 灰色边框 */
                    border-radius: 4px;
                    padding: 2px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;  /* 稍深灰色悬停 */
                    border-color: #666666;
                }
            """)
        
        # 打印状态信息
        button_names = ["Reset View", "Rest Displayed"]
        status = "激活" if self.function_button_states[index] else "未激活"
        print(f"{button_names[index]} 按钮状态: {status}")

    def show_face_intersections(self, face_idx):
        """显示指定面片的所有相交面片"""
        if not hasattr(self, 'face_intersection_map') or not self.face_intersection_map:
            QMessageBox.information(self, "信息", "没有可用的面片相交关系数据，请先运行相交检测。")
            return
        
        face_idx = int(face_idx)  # 确保是整数
        if face_idx not in self.face_intersection_map:
            QMessageBox.information(self, "信息", f"面片 #{face_idx} 没有相交关系。")
            return
        
        # 获取与当前面片相交的所有面片
        intersecting_faces = self.face_intersection_map[face_idx]
        
        # 高亮显示这些面片
        self.selected_faces = [face_idx] + list(intersecting_faces)
        self.update_display()
        
        # 显示信息
        QMessageBox.information(
            self, 
            "面片相交关系", 
            f"面片 #{face_idx} 与以下 {len(intersecting_faces)} 个面片相交：\n{', '.join(map(str, sorted(intersecting_faces)))}"
        )

    def toggle_face_selection(self, face_id):
        """切换面片选择状态"""
        if face_id in self.selected_faces:
            self.selected_faces.remove(face_id)
            self.statusBar.showMessage(f'取消选择面 {face_id}')
        else:
            self.selected_faces.append(face_id)
            self.statusBar.showMessage(f'选择面 {face_id}')
        self.update_display()
    
    def delete_face(self, face_id):
        """删除指定的面片"""
        if face_id < 0 or face_id >= len(self.mesh_data['faces']):
            return
            
        # 从选择中移除
        if face_id in self.selected_faces:
            self.selected_faces.remove(face_id)
            
        # 记录要删除的面片
        face_to_delete = self.mesh_data['faces'][face_id]
        
        # 从模型中删除面片
        self.mesh_data['faces'] = np.delete(self.mesh_data['faces'], face_id, axis=0)
        
        # 更新大于被删除面片索引的已选择面片
        self.selected_faces = [f if f < face_id else f - 1 for f in self.selected_faces]
        
        # 标记模型已修改
        self.mark_model_modified()
        
        # 更新相交关系映射
        if hasattr(self, 'face_intersection_map') and self.face_intersection_map:
            # 移除被删除面的相交关系
            if face_id in self.face_intersection_map:
                del self.face_intersection_map[face_id]
                
            # 更新其他面的相交关系
            updated_map = {}
            for f, intersections in self.face_intersection_map.items():
                # 调整大于被删除面的索引
                new_f = f if f < face_id else f - 1
                
                # 从相交列表中移除被删除的面
                new_intersections = set()
                for i in intersections:
                    if i != face_id:  # 不包含被删除的面
                        new_i = i if i < face_id else i - 1
                        new_intersections.add(new_i)
                        
                updated_map[new_f] = new_intersections
                
            self.face_intersection_map = updated_map
        
        # 更新缓存，使其失效
        self.detection_cache['face_intersections'] = None
        self.detection_cache['face_intersection_map'] = None
        
        # 更新显示
        self.update_display()
        self.statusBar.showMessage(f'已删除面 {face_id}')
        
        # 更新模型分析
        self.update_model_analysis()
