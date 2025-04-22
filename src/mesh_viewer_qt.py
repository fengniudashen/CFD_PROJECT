import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QFrame, QLabel, QLineEdit,
                           QGridLayout, QMessageBox, QStatusBar, QProgressDialog, QInputDialog,
                           QTabWidget, QShortcut, QMenu, QAction, QRadioButton, QCheckBox, QStyle,
                           QSplitter)
from PyQt5.QtGui import QFont, QIcon, QPainter, QPen, QColor, QPixmap, QImage, qRgb, QCursor
from PyQt5.QtCore import Qt, QSize, QTimer, QPoint, QPointF
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

# 导入 defaultdict
from collections import defaultdict

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
        # self.selection_mode = 'smart' # <-- 移除旧的选择模式

        # 新的激活选择状态标志
        self.select_points_active = False
        self.select_edges_active = False
        self.select_faces_active = False
        
        # 面相交关系映射 - 储存每个面与哪些面相交
        self.face_intersection_map = {}
        
        # --- 新增：交互式面片创建状态 --- 
        self.is_creating_face = False
        self.new_face_points = [] # 存储用户点击的3D坐标点
        self.preview_actor = None # 用于显示临时预览线 (将在Overlay渲染)
        self.fixed_edges_actor = None # 用于显示已固定的边 (将在Overlay渲染)
        # --- 状态变量添加结束 ---
        
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
        
        # 添加相邻面检测阈值
        self.adjacent_faces_threshold = None
        
        # 添加面质量和相邻面功能初始化标记，只有用户手动点击并输入阈值后才会设为True
        self.face_quality_initialized = False
        self.adjacent_faces_initialized = False
        
        # 创建 VTK 小部件
        self.vtk_widget = QVTKRenderWindowInteractor()
        render_window = self.vtk_widget.GetRenderWindow()
        
        # --- 创建主渲染器 --- 
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetLayer(0) # 主渲染器在底层
        self.renderer.SetBackground(1.0, 1.0, 1.0)
        render_window.AddRenderer(self.renderer)
        
        # --- 新增：创建 Overlay 渲染器 --- 
        self.overlay_renderer = vtk.vtkRenderer()
        self.overlay_renderer.SetLayer(1) # Overlay 在顶层
        self.overlay_renderer.SetActiveCamera(self.renderer.GetActiveCamera()) # 与主渲染器共享相机
        self.overlay_renderer.InteractiveOff() # 禁用交互，只用于显示
        render_window.SetNumberOfLayers(2) # 声明有两个渲染层
        render_window.AddRenderer(self.overlay_renderer)
        # --- Overlay 渲染器创建结束 ---
        
        # 设置交互器 (使用主渲染器)
        self.iren = render_window.GetInteractor()
        self.cell_picker = vtk.vtkCellPicker()
        self.cell_picker.SetTolerance(0.001)
        self.iren.SetPicker(self.cell_picker)
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(style)
        
        # 创建网格 (添加到主渲染器)
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
        # content_layout = QHBoxLayout() # <-- 不再需要这个 QHBoxLayout
        
        # 创建左侧控制面板（使用标签页）
        control_panel = QFrame()
        control_panel.setFrameStyle(QFrame.Panel | QFrame.Raised)
        control_panel.setMaximumWidth(400) # 可以适当增加最大宽度
        control_panel.setMinimumWidth(200) # 设置一个最小宽度
        control_layout = QVBoxLayout(control_panel)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        control_layout.addWidget(self.tab_widget)
        
        # 创建"修复"标签页
        fix_tab = QWidget()
        fix_layout = QVBoxLayout(fix_tab)
        
        # --- 创建顶部图标按钮行 ---
        top_icon_layout = QHBoxLayout() 
        top_icon_layout.setContentsMargins(0, 0, 0, 0) 
        top_icon_layout.setSpacing(2) 

        # 新按钮尺寸
        icon_button_size = 45
        icon_pixmap_size = icon_button_size - 10 # 给图标留点边距，设为 35x35
        pixmap = QPixmap(icon_pixmap_size, icon_pixmap_size) # 创建统一尺寸的画布
        center_x, center_y = icon_pixmap_size // 2, icon_pixmap_size // 2

        # --- 1. 创建点主图标按钮 (十字准星) ---
        self.show_create_point_btn = QPushButton()
        create_pt_icon = QIcon()
        pixmap.fill(Qt.transparent)
        create_pt_painter = QPainter(pixmap)
        create_pt_painter.setRenderHint(QPainter.Antialiasing)
        create_pt_pen = QPen(QColor(0, 0, 0), 2) 
        create_pt_painter.setPen(create_pt_pen)
        line_len = icon_pixmap_size // 3
        create_pt_painter.drawLine(center_x - line_len, center_y, center_x + line_len, center_y)
        create_pt_painter.drawLine(center_x, center_y - line_len, center_x, center_y + line_len)
        create_pt_painter.setBrush(QColor(0, 0, 0))
        dot_radius = 3
        create_pt_painter.drawEllipse(center_x - dot_radius, center_y - dot_radius, dot_radius * 2, dot_radius * 2)
        create_pt_painter.end()
        create_pt_icon.addPixmap(pixmap)
        self.show_create_point_btn.setIcon(create_pt_icon)
        self.show_create_point_btn.setIconSize(QSize(icon_pixmap_size, icon_pixmap_size))
        self.show_create_point_btn.setToolTip("创建点选项") 
        self.show_create_point_btn.setFixedSize(icon_button_size, icon_button_size) 
        self.show_create_point_btn.clicked.connect(self._toggle_create_point_options) 
        top_icon_layout.addWidget(self.show_create_point_btn) 

        # --- 2. 创建"从选中点创建面"图标按钮 --- 
        self.create_face_icon_btn = QPushButton()
        create_face_icon = QIcon()
        pixmap.fill(Qt.transparent)
        create_face_painter = QPainter(pixmap)
        create_face_painter.setRenderHint(QPainter.Antialiasing)
        dot_r = 3
        p1 = QPoint(center_x, 5)
        p2 = QPoint(7, icon_pixmap_size - 7)
        p3 = QPoint(icon_pixmap_size - 7, icon_pixmap_size - 7)
        create_face_painter.setBrush(QColor(0, 0, 0))
        create_face_painter.setPen(Qt.NoPen)
        create_face_painter.drawEllipse(p1, dot_r, dot_r)
        create_face_painter.drawEllipse(p2, dot_r, dot_r)
        create_face_painter.drawEllipse(p3, dot_r, dot_r)
        create_face_pen = QPen(QColor(100, 100, 100), 1, Qt.DotLine) 
        create_face_painter.setPen(create_face_pen)
        create_face_painter.drawLine(p1, p2)
        create_face_painter.drawLine(p2, p3)
        create_face_painter.drawLine(p3, p1)
        create_face_painter.end()
        create_face_icon.addPixmap(pixmap)
        self.create_face_icon_btn.setIcon(create_face_icon)
        self.create_face_icon_btn.setIconSize(QSize(icon_pixmap_size, icon_pixmap_size))
        self.create_face_icon_btn.setToolTip("从选中的3个点创建面")
        self.create_face_icon_btn.setFixedSize(icon_button_size, icon_button_size) 
        self.create_face_icon_btn.clicked.connect(self.create_face) 
        top_icon_layout.addWidget(self.create_face_icon_btn) 

        # --- 3. 新增："合并选中顶点"图标按钮 --- 
        self.collapse_vertices_btn = QPushButton()
        collapse_icon = QIcon()
        pixmap.fill(Qt.transparent)
        collapse_painter = QPainter(pixmap)
        collapse_painter.setRenderHint(QPainter.Antialiasing)
        points_to_draw = [QPoint(8, 8), QPoint(icon_pixmap_size-8, 8), 
                          QPoint(8, icon_pixmap_size-8), QPoint(icon_pixmap_size-8, icon_pixmap_size-8)]
        center_p = QPoint(center_x, center_y)
        collapse_painter.setBrush(QColor(0, 0, 0))
        collapse_painter.setPen(Qt.NoPen)
        for p in points_to_draw:
             collapse_painter.drawEllipse(p, 2, 2)
        collapse_pen = QPen(QColor(100, 100, 100), 1)
        collapse_painter.setPen(collapse_pen)
        for p in points_to_draw:
            vec = center_p - p
            # 使用 QPointF 进行向量计算以保持精度
            vec_f = QPointF(vec.x(), vec.y()) 
            center_p_f = QPointF(center_p.x(), center_p.y())
            p_f = QPointF(p.x(), p.y())
            length = np.sqrt(vec_f.x()**2 + vec_f.y()**2)
            if length < 1e-6: continue
            norm_vec_f = vec_f / length
            # 计算浮点坐标
            start_p_f = p_f + norm_vec_f * 4 
            end_p_f = center_p_f - norm_vec_f * 4 
            # 绘制时转换为 QPoint
            collapse_painter.drawLine(QPoint(int(start_p_f.x()), int(start_p_f.y())), 
                                      QPoint(int(end_p_f.x()), int(end_p_f.y())))
        collapse_painter.setBrush(QColor(255, 0, 0)) 
        collapse_painter.setPen(Qt.NoPen)
        collapse_painter.drawEllipse(center_p, 3, 3)
        collapse_painter.end()
        collapse_icon.addPixmap(pixmap)
        self.collapse_vertices_btn.setIcon(collapse_icon)
        self.collapse_vertices_btn.setIconSize(QSize(icon_pixmap_size, icon_pixmap_size))
        self.collapse_vertices_btn.setToolTip("合并选中的顶点")
        self.collapse_vertices_btn.setFixedSize(icon_button_size, icon_button_size) 
        self.collapse_vertices_btn.clicked.connect(self.collapse_selected_vertices) 
        top_icon_layout.addWidget(self.collapse_vertices_btn) 

        # --- 4. 新增："分割选中边/面"图标按钮 --- 
        self.split_elements_btn = QPushButton()
        split_icon = QIcon()
        pixmap.fill(Qt.transparent)
        split_painter = QPainter(pixmap)
        split_painter.setRenderHint(QPainter.Antialiasing)
        t_margin = 6
        top_p = QPoint(center_x, t_margin)
        bl_p = QPoint(t_margin, icon_pixmap_size - t_margin)
        br_p = QPoint(icon_pixmap_size - t_margin, icon_pixmap_size - t_margin)
        base_mid_p = QPoint(center_x, icon_pixmap_size - t_margin)
        split_pen = QPen(QColor(0, 0, 0), 1)
        split_painter.setPen(split_pen)
        split_painter.drawLine(bl_p, br_p)
        split_painter.drawLine(bl_p, top_p)
        split_painter.drawLine(br_p, top_p)
        split_pen.setStyle(Qt.DashLine)
        split_pen.setColor(QColor(255, 0, 0)) 
        split_painter.setPen(split_pen)
        split_painter.drawLine(top_p, base_mid_p)
        split_painter.end()
        split_icon.addPixmap(pixmap)
        self.split_elements_btn.setIcon(split_icon)
        self.split_elements_btn.setIconSize(QSize(icon_pixmap_size, icon_pixmap_size))
        self.split_elements_btn.setToolTip("分割选中的边/面 (Split selected edges/faces)")
        self.split_elements_btn.setFixedSize(icon_button_size, icon_button_size) 
        self.split_elements_btn.clicked.connect(self.split_selected_elements) 
        top_icon_layout.addWidget(self.split_elements_btn) 

        # --- 5. 新增："交换选中边"图标按钮 --- 
        self.swap_edge_btn = QPushButton()
        swap_icon = QIcon()
        pixmap.fill(Qt.transparent)
        swap_painter = QPainter(pixmap)
        swap_painter.setRenderHint(QPainter.Antialiasing)
        s_margin_h = 8
        s_margin_v = 6
        A = QPoint(s_margin_h, center_y)
        B = QPoint(icon_pixmap_size - s_margin_h, center_y)
        C = QPoint(center_x, s_margin_v)
        D = QPoint(center_x, icon_pixmap_size - s_margin_v)
        swap_pen = QPen(QColor(0, 0, 0), 1)
        swap_painter.setPen(swap_pen)
        swap_painter.drawLine(A, B)
        swap_painter.drawLine(B, C)
        swap_painter.drawLine(C, A)
        swap_painter.drawLine(A, D)
        swap_painter.drawLine(D, B)
        swap_pen.setStyle(Qt.DashLine)
        swap_pen.setColor(QColor(255, 0, 0)) 
        swap_painter.setPen(swap_pen)
        swap_painter.drawLine(C, D)
        swap_painter.end()
        swap_icon.addPixmap(pixmap)
        self.swap_edge_btn.setIcon(swap_icon)
        self.swap_edge_btn.setIconSize(QSize(icon_pixmap_size, icon_pixmap_size))
        self.swap_edge_btn.setToolTip("交换选中的边 (Swap selected edge)")
        self.swap_edge_btn.setFixedSize(icon_button_size, icon_button_size) 
        self.swap_edge_btn.clicked.connect(self.swap_selected_edge) 
        top_icon_layout.addWidget(self.swap_edge_btn) 

        # --- 6. 保留："交互式面片创建"图标按钮 --- 
        self.fill_patch_btn = QPushButton() 
        fill_icon = QIcon()
        pixmap.fill(Qt.transparent)
        fill_painter = QPainter(pixmap)
        fill_painter.setRenderHint(QPainter.Antialiasing)
        h_margin = 6
        hw = center_x
        hh = center_y
        hr = min(hw, hh) - h_margin
        poly_points = [
             QPoint(hw + int(hr * np.cos(np.pi * i / 3)), hh + int(hr * np.sin(np.pi * i / 3))) for i in range(6)
        ]
        fill_pen = QPen(QColor(0, 0, 0), 1)
        fill_painter.setPen(fill_pen)
        fill_painter.drawPolygon(*poly_points)
        fill_painter.setBrush(QColor(173, 216, 230, 180)) 
        fill_painter.setPen(Qt.NoPen) 
        fill_painter.drawPolygon(*poly_points)
        fill_painter.end()
        fill_icon.addPixmap(pixmap)
        self.fill_patch_btn.setIcon(fill_icon)
        self.fill_patch_btn.setIconSize(QSize(icon_pixmap_size, icon_pixmap_size))
        self.fill_patch_btn.setToolTip("交互式创建面片 (Interactive face creation)") 
        self.fill_patch_btn.setFixedSize(icon_button_size, icon_button_size) 
        self.fill_patch_btn.setCheckable(True) 
        self.fill_patch_btn.clicked.connect(self.start_interactive_face_creation) 
        top_icon_layout.addWidget(self.fill_patch_btn) 
        
        # --- 7. 新增："AI修复"图标按钮 --- 
        self.ai_repair_btn = QPushButton()
        ai_icon = QIcon()
        pixmap.fill(Qt.transparent)
        ai_painter = QPainter(pixmap)
        ai_painter.setRenderHint(QPainter.Antialiasing)
        ai_t_margin = 8
        ai_top_p = QPoint(center_x - 3, ai_t_margin)
        ai_bl_p = QPoint(ai_t_margin, icon_pixmap_size - ai_t_margin)
        ai_br_p = QPoint(icon_pixmap_size - ai_t_margin, icon_pixmap_size - ai_t_margin - 2)
        ai_pen = QPen(QColor(150, 150, 150), 1) 
        ai_painter.setPen(ai_pen)
        ai_painter.drawLine(ai_bl_p, ai_br_p)
        ai_painter.drawLine(ai_bl_p, ai_top_p)
        ai_painter.drawLine(ai_br_p, ai_top_p)
        wand_pen = QPen(QColor(139, 69, 19), 2)
        wand_start = QPoint(icon_pixmap_size - 10, 8)
        wand_end = QPoint(icon_pixmap_size - 5, 13)
        ai_painter.setPen(wand_pen)
        ai_painter.drawLine(wand_start, wand_end)
        star_pen = QPen(QColor(255, 215, 0), 1)
        ai_painter.setPen(star_pen)
        star_center = wand_start + QPoint(-1, -1)
        ai_painter.drawLine(star_center + QPoint(0, -3), star_center + QPoint(0, 3))
        ai_painter.drawLine(star_center + QPoint(-3, 0), star_center + QPoint(3, 0))
        ai_painter.drawLine(star_center + QPoint(-2, -2), star_center + QPoint(2, 2))
        ai_painter.drawLine(star_center + QPoint(-2, 2), star_center + QPoint(2, -2))
        ai_painter.end()
        ai_icon.addPixmap(pixmap)
        self.ai_repair_btn.setIcon(ai_icon)
        self.ai_repair_btn.setIconSize(QSize(icon_pixmap_size, icon_pixmap_size))
        self.ai_repair_btn.setToolTip("AI修复")
        self.ai_repair_btn.setFixedSize(icon_button_size, icon_button_size) 
        top_icon_layout.addWidget(self.ai_repair_btn) 

        # --- 8. 新增："删除选定面"图标按钮 --- 
        self.delete_face_icon_btn = QPushButton()
        delete_icon = QIcon()
        pixmap.fill(Qt.transparent)
        delete_painter = QPainter(pixmap)
        delete_painter.setRenderHint(QPainter.Antialiasing)
        face_pen = QPen(QColor(150, 150, 150), 1)
        delete_painter.setPen(face_pen)
        d_margin = 8
        p1 = QPoint(center_x, d_margin)
        p2 = QPoint(d_margin, icon_pixmap_size - d_margin)
        p3 = QPoint(icon_pixmap_size - d_margin, icon_pixmap_size - d_margin)
        delete_painter.drawLine(p1, p2)
        delete_painter.drawLine(p2, p3)
        delete_painter.drawLine(p3, p1)
        cross_pen = QPen(QColor(255, 0, 0), 3) 
        delete_painter.setPen(cross_pen)
        cross_margin = d_margin + 4
        delete_painter.drawLine(cross_margin, cross_margin, 
                                icon_pixmap_size - cross_margin, icon_pixmap_size - cross_margin)
        delete_painter.drawLine(cross_margin, icon_pixmap_size - cross_margin, 
                                icon_pixmap_size - cross_margin, cross_margin)
        delete_painter.end()
        delete_icon.addPixmap(pixmap)
        self.delete_face_icon_btn.setIcon(delete_icon)
        self.delete_face_icon_btn.setIconSize(QSize(icon_pixmap_size, icon_pixmap_size))
        self.delete_face_icon_btn.setToolTip("删除选定面 (D)") 
        self.delete_face_icon_btn.setFixedSize(icon_button_size, icon_button_size) 
        self.delete_face_icon_btn.clicked.connect(self.delete_selected_faces) 
        top_icon_layout.addWidget(self.delete_face_icon_btn) 

        top_icon_layout.addStretch(1) 
        fix_layout.addLayout(top_icon_layout) 

        # --- 创建包含二级和三级菜单的容器 ---
        self.create_point_options_container = QWidget()
        options_container_layout = QVBoxLayout(self.create_point_options_container)
        options_container_layout.setContentsMargins(5, 5, 5, 5) # 内边距
        options_container_layout.setSpacing(5) # 内部控件间距

        # 设置容器样式 (使用更明显的颜色)
        self.create_point_options_container.setStyleSheet("""
            QWidget#createPointOptionsContainer { /* 使用对象名称确保特异性 */
                background-color: #eaf2f8; /* 淡蓝色背景 */
                border: 1px solid #c5d9e8; /* 稍深的蓝色边框 */
                border-radius: 4px; /* 轻微增加圆角 */
            }
        """)
        # 为了让样式表通过对象名称生效，需要设置对象名称
        self.create_point_options_container.setObjectName("createPointOptionsContainer")

        # 3. 创建"从三坐标创建点"按钮 (放入容器)
        self.show_xyz_input_btn = QPushButton("从三坐标创建点")
        # self.show_xyz_input_btn.setVisible(False) # 不再需要在这里隐藏，由容器控制
        self.show_xyz_input_btn.clicked.connect(self._toggle_xyz_input_ui) # 连接到切换三级菜单的方法
        options_container_layout.addWidget(self.show_xyz_input_btn) # 添加到容器布局

        # 4. 创建 X, Y, Z 输入区域 (放入容器)
        self.xyz_input_group = QFrame() # 重命名 self.coord_group
        coord_layout = QGridLayout(self.xyz_input_group)
        coord_layout.addWidget(QLabel('X:'), 0, 0)
        self.x_input = QLineEdit()
        coord_layout.addWidget(self.x_input, 0, 1)
        coord_layout.addWidget(QLabel('Y:'), 1, 0)
        self.y_input = QLineEdit()
        coord_layout.addWidget(self.y_input, 1, 1)
        coord_layout.addWidget(QLabel('Z:'), 2, 0)
        self.z_input = QLineEdit()
        coord_layout.addWidget(self.z_input, 2, 1)
        create_point_confirm_btn = QPushButton('创建点') 
        create_point_confirm_btn.clicked.connect(self.create_point)
        coord_layout.addWidget(create_point_confirm_btn, 3, 0, 1, 2)

        self.xyz_input_group.setVisible(False) # 输入框默认隐藏
        options_container_layout.addWidget(self.xyz_input_group) # 添加到容器布局

        self.create_point_options_container.setVisible(False) # 容器默认隐藏
        fix_layout.addWidget(self.create_point_options_container) # 将容器添加到主布局

        # --- 面操作区域 ---
        face_group = QFrame()
        face_layout = QVBoxLayout(face_group)
        


        # 添加伸缩器
        fix_layout.addStretch()

        # 连接模式切换信号 (移除)
        # self.point_mode_btn.clicked.connect(lambda: self.set_selection_mode('point'))
        # ... (移除所有旧模式信号连接)
        
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
        
        # 添加伸缩器，将下面的按钮推到底部
        control_layout.addStretch(1)

        # 在标签页下方添加五个居中的按钮 (现在会在最底部)
        bottom_button_container = QWidget() # 使用QWidget作为容器
        bottom_button_layout = QHBoxLayout(bottom_button_container)
        bottom_button_layout.setContentsMargins(0, 5, 0, 5) # 添加上下边距
        bottom_button_layout.setSpacing(0) # <--- 设置按钮间距为 0
        bottom_button_layout.addStretch(1) # 左侧伸缩

        # 定义按钮文本和图标
        button_configs = [
            {"text": "Reset Regions..."},
            {"text": "Close"},
            {"text": "Help"},
            {"icon": QStyle.SP_ArrowBack}, # 使用标准 后退/撤销 图标
            {"icon": QStyle.SP_ArrowForward}  # 使用标准 前进/重做 图标
        ]

        for i, config in enumerate(button_configs): # <--- 添加 enumerate 获取索引
            bottom_btn = QPushButton()
            # 保持最小宽度，但允许按钮根据内容调整，特别是图标按钮
            # bottom_btn.setMinimumWidth(50)

            if "text" in config:
                bottom_btn.setText(config["text"])
                # 如果是第一个按钮，缩小字体
                if i == 0: # <--- 检查是否是第一个按钮
                    font = bottom_btn.font()
                    font.setPointSize(8) # <--- 设置稍小的字体大小 (例如 8pt)
                    bottom_btn.setFont(font)
                # 为文本按钮设置一个合适的最小宽度，确保文字显示
                bottom_btn.setMinimumWidth(70)
            elif "icon" in config:
                # 获取标准图标
                style = QApplication.style() # 获取当前应用程序的样式
                # 使用正确的枚举值获取图标
                icon = style.standardIcon(config["icon"])
                bottom_btn.setIcon(icon)
                # 让图标按钮更紧凑
                bottom_btn.setFixedSize(30, 30) # 可以设置固定大小或调整

            # 可以添加样式或连接信号
            # bottom_btn.setStyleSheet("...")
            # bottom_btn.clicked.connect(...) # 示例：连接到 handle_bottom_button
            bottom_button_layout.addWidget(bottom_btn)


        bottom_button_layout.addStretch(1) # 右侧伸缩
        control_layout.addWidget(bottom_button_container) # 将按钮容器添加到主垂直布局

        # 设置控制面板布局 (不需要重复设置)
        # control_panel.setLayout(control_layout)
        
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
        
        # --- 修改状态指示器 --- 
        # 定义选中和未选中时的样式
        toggle_style_sheet = """
            QPushButton {{ 
                background-color: #f0f0f0; 
                border: 1px solid #ababab; 
                padding: 2px 5px; 
                border-radius: 3px; 
                min-width: 25px; 
            }}
            QPushButton:checked {{ 
                background-color: #cceeff; 
                border: 1px solid #99dfff; 
            }}
            QPushButton:hover {{ 
                background-color: #e0e0e0; 
            }}
        """

        # --- 点状态 (标签改为按钮，添加图标) ---
        point_status_widget = QWidget()
        point_status_layout = QHBoxLayout(point_status_widget)
        point_status_layout.setContentsMargins(0, 0, 0, 0)
        point_status_layout.setSpacing(2)

        # 创建点图标
        point_icon = QIcon()
        point_pixmap = QPixmap(16, 16) # 小图标尺寸
        point_pixmap.fill(Qt.transparent)
        point_painter = QPainter(point_pixmap)
        point_painter.setRenderHint(QPainter.Antialiasing)
        point_painter.setBrush(QColor(0, 0, 0)) # 黑色填充
        point_painter.drawEllipse(4, 4, 8, 8) # 绘制一个居中的小圆点
        point_painter.end()
        point_icon.addPixmap(point_pixmap)

        self.point_toggle_btn = QPushButton("点")
        self.point_toggle_btn.setIcon(point_icon) # 设置图标
        self.point_toggle_btn.setCheckable(True)
        self.point_toggle_btn.setStyleSheet(toggle_style_sheet)
        self.point_toggle_btn.toggled.connect(self._update_selection_active_state)
        self.point_count = QLabel(": 0")
        point_clear = QPushButton("×")
        point_clear.setMaximumWidth(20)
        point_clear.clicked.connect(self.clear_points)
        point_status_layout.addWidget(self.point_toggle_btn)
        point_status_layout.addWidget(self.point_count)
        point_status_layout.addWidget(point_clear)

        # --- 线状态 (标签改为按钮，添加图标) ---
        edge_status_widget = QWidget()
        edge_status_layout = QHBoxLayout(edge_status_widget)
        edge_status_layout.setContentsMargins(0, 0, 0, 0)
        edge_status_layout.setSpacing(2)

        # 创建线图标
        edge_icon = QIcon()
        edge_pixmap = QPixmap(16, 16)
        edge_pixmap.fill(Qt.transparent)
        edge_painter = QPainter(edge_pixmap)
        edge_painter.setRenderHint(QPainter.Antialiasing)
        edge_pen = QPen(QColor(0, 0, 0))
        edge_pen.setWidth(2)
        edge_painter.setPen(edge_pen)
        edge_painter.drawLine(3, 8, 13, 8) # 绘制一条居中的水平线
        edge_painter.end()
        edge_icon.addPixmap(edge_pixmap)

        self.edge_toggle_btn = QPushButton("线")
        self.edge_toggle_btn.setIcon(edge_icon) # 设置图标
        self.edge_toggle_btn.setCheckable(True)
        self.edge_toggle_btn.setStyleSheet(toggle_style_sheet)
        self.edge_toggle_btn.toggled.connect(self._update_selection_active_state)
        self.edge_count = QLabel(": 0")
        edge_clear = QPushButton("×")
        edge_clear.setMaximumWidth(20)
        edge_clear.clicked.connect(self.clear_edges)
        edge_status_layout.addWidget(self.edge_toggle_btn)
        edge_status_layout.addWidget(self.edge_count)
        edge_status_layout.addWidget(edge_clear)

        # --- 面状态 (标签改为按钮，添加图标) ---
        face_status_widget = QWidget()
        face_status_layout = QHBoxLayout(face_status_widget)
        face_status_layout.setContentsMargins(0, 0, 0, 0)
        face_status_layout.setSpacing(2)

        # 创建面图标 (三角形)
        face_icon = QIcon()
        face_pixmap = QPixmap(16, 16)
        face_pixmap.fill(Qt.transparent)
        face_painter = QPainter(face_pixmap)
        face_painter.setRenderHint(QPainter.Antialiasing)
        face_pen = QPen(QColor(0, 0, 0))
        face_pen.setWidth(1)
        face_painter.setPen(face_pen)
        # face_painter.setBrush(QColor(200, 200, 200)) # 可选：灰色填充
        # 定义三角形顶点
        triangle_points = [
            QPoint(8, 3),  # 顶点
            QPoint(3, 13), # 左下角
            QPoint(13, 13) # 右下角
        ]
        face_painter.drawPolygon(*triangle_points) # 绘制三角形轮廓
        face_painter.end()
        face_icon.addPixmap(face_pixmap)

        self.face_toggle_btn = QPushButton("面")
        self.face_toggle_btn.setIcon(face_icon) # 设置图标
        self.face_toggle_btn.setCheckable(True)
        self.face_toggle_btn.setStyleSheet(toggle_style_sheet)
        self.face_toggle_btn.toggled.connect(self._update_selection_active_state)
        self.face_count = QLabel(": 0")
        face_clear = QPushButton("×")
        face_clear.setMaximumWidth(20)
        face_clear.clicked.connect(self.clear_faces)
        face_status_layout.addWidget(self.face_toggle_btn)
        face_status_layout.addWidget(self.face_count)
        face_status_layout.addWidget(face_clear)
        # --- 修改结束 --- 
        
        # 添加状态指示器到状态面板
        status_layout.addStretch(1)
        status_layout.addWidget(point_status_widget) # 添加修改后的 widget
        status_layout.addWidget(edge_status_widget)
        status_layout.addWidget(face_status_widget)
        status_layout.addStretch(1)
        
        # 添加状态面板到右侧布局
        right_layout.addWidget(status_panel)
        
        # 添加一些底部空间 (右侧不再需要额外spacer)
        # spacer = QWidget()
        # spacer.setMinimumHeight(20)
        # right_layout.addWidget(spacer)

        # 创建水平分割器来替代 content_layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(control_panel)   # 添加左侧面板
        splitter.addWidget(right_container) # 添加右侧容器

        # 设置初始大小比例 (例如，左侧 250px，右侧占据剩余空间)
        initial_width = self.geometry().width() # 获取窗口初始宽度
        left_width = 250
        right_width = max(200, initial_width - left_width - 20) # 估算右侧宽度，确保大于最小宽度
        splitter.setSizes([left_width, right_width])

        # 可选：设置某个面板不能完全折叠
        # splitter.setCollapsible(0, False)
        # splitter.setCollapsible(1, False)

        # 可选：设置分割条的宽度
        # splitter.setHandleWidth(5)

        # 将分割器添加到主布局中，替换原来的 content_layout
        main_layout.addWidget(splitter, 1) # 第二个参数 1 表示拉伸因子，让 splitter 占据主要空间
        
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
        self.iren.RemoveObservers("RightButtonPressEvent") # <--- 移除可能存在的旧右键观察器
        self.iren.RemoveObservers("KeyPressEvent") # <--- 移除可能存在的旧键盘观察器
        
        # 添加新的观察器
        self.iren.AddObserver("LeftButtonPressEvent", self.on_left_button_press)
        self.iren.AddObserver("MouseMoveEvent", self.on_mouse_move)
        self.iren.AddObserver("LeftButtonReleaseEvent", self.on_left_button_release)
        self.iren.AddObserver("RightButtonPressEvent", self.on_right_button_press) # <--- 添加右键观察器
        self.iren.AddObserver("KeyPressEvent", self.keyPressEvent) # <--- 重新添加键盘观察器
        
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
    
    def _update_selection_active_state(self):
        """根据底部切换按钮更新活动的选择类型"""
        self.select_points_active = self.point_toggle_btn.isChecked()
        self.select_edges_active = self.edge_toggle_btn.isChecked()
        self.select_faces_active = self.face_toggle_btn.isChecked()
        # 可以选择在这里打印状态或更新状态栏
        # print(f"Selection Active: P={self.select_points_active}, E={self.select_edges_active}, F={self.select_faces_active}")
    
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
        if self.is_creating_face:
            x, y = self.iren.GetEventPosition()
            # 使用 CellPicker 获取精确的模型表面交点
            picker = vtk.vtkCellPicker()
            picker.SetTolerance(0.001)
            picker.Pick(x, y, 0, self.renderer)
            
            if picker.GetCellId() != -1: # 确保点击在模型上
                picked_position = np.array(picker.GetPickPosition())
                self.new_face_points.append(picked_position)
                print(f"Added point {len(self.new_face_points)}: {picked_position}")
                self._update_fixed_edges_display() # 更新固定边显示
                self.vtk_widget.GetRenderWindow().Render() # 更新视图
                # 阻止默认的相机交互
                self.iren.GetInteractorStyle().OnLeftButtonDown() # 调用基类方法可能仍会触发相机移动，需要更强的阻止
                # 尝试直接终止事件处理 (如果VTK版本支持) - 通常不推荐
                # self.iren.TerminateApp() # 这是一个猜测，可能不正确或有副作用
                return # 直接返回，不让基类处理相机事件
            else:
                print("Click did not hit the mesh.")
                # 点击到空白处，可以考虑取消操作
                # self.cancel_interactive_face_creation()
                # return
                
        # 如果不在创建模式，执行原来的逻辑
        self.left_button_down = True
        self.moved_since_press = False
        self.press_pos = self.iren.GetEventPosition()
        self.iren.GetInteractorStyle().OnLeftButtonDown()
    
    def on_mouse_move(self, obj, event):
        """处理鼠标移动事件"""
        if self.is_creating_face and len(self.new_face_points) > 0:
            x, y = self.iren.GetEventPosition()
            # 持续拾取以获取鼠标下的模型表面点
            picker = vtk.vtkCellPicker()
            picker.SetTolerance(0.001)
            picker.Pick(x, y, 0, self.renderer)
            
            if picker.GetCellId() != -1:
                current_mesh_pos = np.array(picker.GetPickPosition())
                self._update_preview_lines(current_mesh_pos)
                # 仅渲染预览层或整个窗口
                self.vtk_widget.GetRenderWindow().Render() # 简单起见，渲染整个窗口
            
            # 阻止默认的相机交互
            self.iren.GetInteractorStyle().OnMouseMove() # 调用基类可能仍会触发相机，需要阻止
            return # 直接返回

        # 如果不在创建模式，执行原来的逻辑
        if self.left_button_down:
            current_pos = self.iren.GetEventPosition()
            if self.press_pos:
                dx = abs(current_pos[0] - self.press_pos[0])
                dy = abs(current_pos[1] - self.press_pos[1])
                if dx > 3 or dy > 3:
                    self.moved_since_press = True
        
        if self.left_button_down:
            self.is_interacting = True
            self.vtk_widget.GetRenderWindow().SetDesiredUpdateRate(30.0)
        
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
        
        # --- 右键菜单逻辑 (保持不变) ---
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
        
        # --- 修改后的选择逻辑 --- 
        point_picked = False
        edge_picked = False
        face_picked = False

        # 1. 尝试选择点 (如果激活)
        if self.select_points_active:
            min_dist = float('inf')
            closest_point_id = -1
            for i, vertex in enumerate(self.mesh_data['vertices']):
                dist = np.linalg.norm(vertex - picked_position)
                if dist < min_dist:
                    min_dist = dist
                    closest_point_id = i
            
            # 如果足够接近某个点
            if min_dist < 2.0: # 使用合适的容差值
                hit_anything = True
                point_picked = True
                if closest_point_id in self.selected_points:
                    self.selected_points.remove(closest_point_id)
                else:
                    self.selected_points.append(closest_point_id)
            
                vertex = self.mesh_data['vertices'][closest_point_id]
                self.statusBar.showMessage(
                    f'选中/取消点 {closest_point_id}: X={vertex[0]:.3f}, Y={vertex[1]:.3f}, Z={vertex[2]:.3f}'
                )
                # 如果只激活了点选择，或者点优先策略下，选中点后直接更新返回
                if not self.select_edges_active and not self.select_faces_active:
                    self.update_display()
                    return
        
        # 2. 尝试选择边 (如果激活且未选中更高优先级的点)
        if self.select_edges_active and not point_picked and cell_id != -1:
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
                    edge_picked = True
                    if closest_edge in self.selected_edges:
                        self.selected_edges.remove(closest_edge)
                    else:
                        self.selected_edges.append(closest_edge)
                    self.edge_selection_source = 'manual'  # 设置为手动选择
                    self.statusBar.showMessage(f'选中/取消边: {closest_edge[0]}-{closest_edge[1]}')
                    # 如果只激活了边选择，或者边优先策略下，选中边后直接更新返回
                    if not self.select_faces_active:
                        self.update_display()
                        return

        # 3. 尝试选择面 (如果激活且未选中更高优先级的点或边)
        if self.select_faces_active and not point_picked and not edge_picked and cell_id != -1:
            cell = self.mesh.GetCell(cell_id)
            if cell and cell.GetNumberOfPoints() == 3: # 确保是三角形面片
                hit_anything = True
                face_picked = True
                if cell_id in self.selected_faces:
                    self.selected_faces.remove(cell_id)
                    self.statusBar.showMessage(f'取消选择面 {cell_id}')
                else: # Correctly indented else block
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
        """清除所有当前选择（点、线、面）"""
        self.selected_points = []
        self.selected_edges = []
        self.selected_faces = []
        self.edge_selection_source = 'manual' # 重置边选择来源
        self.update_display()
        # 更新状态栏计数
        self.update_status_counts()
        self.statusBar.showMessage('已清除选择') # 更新状态栏消息
    
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
            # 先判断是否需要强制重新输入阈值
            force_prompt = False
            
            # 如果未初始化或模型已修改，需要输入阈值
            if not self.face_quality_initialized or self.model_modified:
                force_prompt = True
                
            # 如果不需要强制输入阈值，检查缓存
            if not force_prompt and self.detection_cache['face_quality'] is not None:
                # 直接使用缓存结果
                self.selected_faces = self.detection_cache['face_quality'].copy()
                self.adjust_font_size(self.quality_count, str(len(self.selected_faces)))
                self.update_display()
                print("使用缓存：面片质量分析 (已选择 " + str(len(self.selected_faces)) + " 个面)")
                return
                
            # 需要输入阈值
            threshold, ok = QInputDialog.getDouble(
                self, "设置面片质量阈值", 
                "请输入质量阈值 (0.1-0.5)，较小的值检测更严格:", 
                0.30, 0.1, 0.5, 2)
            
            if not ok:
                return
                
            # 设置初始化标记 - 表示用户已经手动设置了阈值
            self.face_quality_initialized = True
            self.model_modified = False # 重置修改标记
            
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
        """分析面片邻近性，现在通过ModelChangeTracker管理"""
        try:
            # 检查是否有缓存结果且模型未修改
            cached_results = None
            # 先判断是否需要强制重新输入阈值
            threshold = self.adjacent_faces_threshold
            force_prompt = False
            if threshold is None or self.model_modified:
                force_prompt = True
            
            # 如果需要强制输入阈值
            if force_prompt:
                threshold_input, ok = QInputDialog.getDouble(
                    self, "设置面片邻近性阈值", 
                    "请输入邻近性阈值 (0-1)，较小的值检测更严格:", 
                    0.1, 0.0, 1.0, 2)
                
                if not ok:
                    return  # 用户取消输入
                
                threshold = threshold_input
                self.adjacent_faces_threshold = threshold  # 存储新阈值
                self.model_modified = False  # 重置修改标记
                
                # 设置初始化标记 - 表示用户已经手动设置了阈值
                self.adjacent_faces_initialized = True
            else:
                # 如果不需要强制输入，再检查缓存
                if hasattr(self, 'model_tracker'):
                    cached_results = self.model_tracker.get_cached_results('Adjacent Faces')
                
                # 如果追踪器有缓存结果，并且我们不需要强制输入，则使用缓存
                if cached_results is not None:
                    self.selected_faces = cached_results.copy()
                    self.adjust_font_size(self.proximity_count, str(len(self.selected_faces)))
                    self.update_display()
                    print("使用缓存：相邻面分析 (来自 ModelChangeTracker)")
                    return
            
            # --- 执行分析 --- 
            # 确保阈值有效
            if self.adjacent_faces_threshold is None:
                QMessageBox.warning(self, "错误", "无法获取有效的邻近性阈值。")
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
            
            # --- 分析逻辑移交给 ModelChangeTracker --- 
            if hasattr(self, 'model_tracker'):
                # 触发模型追踪器运行分析
                print(f"触发相邻面分析，阈值: {self.adjacent_faces_threshold}")
                self.model_tracker.run_analysis_for_button('Adjacent Faces', threshold=self.adjacent_faces_threshold)
                
                # 从追踪器获取结果
                final_results = self.model_tracker.get_cached_results('Adjacent Faces')
                execution_time = self.model_tracker.get_last_analysis_time('Adjacent Faces')
                
                if final_results is not None:
                    self.selected_faces = final_results.copy()
                    self.adjust_font_size(self.proximity_count, str(len(self.selected_faces)))
                    self.update_display()
                    
                    # 显示结果
                    total_faces = len(self.mesh_data['faces'])
                    percentage = len(self.selected_faces) / total_faces * 100 if total_faces > 0 else 0
                    QMessageBox.information(
                        self, "邻近性分析完成", 
                        f"检测到 {len(self.selected_faces)} 个邻近面片 (阈值 <= {self.adjacent_faces_threshold:.2f})，占总面片数的 {percentage:.2f}%。\n"
                        f"(分析由 ModelChangeTracker 管理)"
                    )
                    self.statusBar.showMessage(f"检测到 {len(self.selected_faces)} 个邻近面片 (阈值={self.adjacent_faces_threshold:.2f}, C++实现)")
                else:
                    # 如果追踪器没有返回结果
                    self.clear_faces()
                    self.adjust_font_size(self.proximity_count, "0")
                    QMessageBox.information(
                        self, "邻近性分析完成", 
                        f"未检测到邻近面片 (阈值={self.adjacent_faces_threshold:.2f})。\n(分析由 ModelChangeTracker 管理)"
                    )
                    self.statusBar.showMessage(f"未检测到邻近面片 (阈值={self.adjacent_faces_threshold:.2f}, C++实现)")
            else:
                # 如果没有 ModelChangeTracker
                QMessageBox.warning(self, "警告", "ModelChangeTracker 不可用，执行独立分析。")
                self.statusBar.showMessage("邻近性分析失败：ModelChangeTracker 不可用")
                
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
        # --- 添加 Esc 取消创建 --- 
        if self.is_creating_face and event.key() == Qt.Key_Escape:
            print("Escape pressed, cancelling face creation.")
            self.cancel_interactive_face_creation()
            return # 消耗事件
            
        # --- 保留其他键盘事件处理 --- 
        if event.key() == Qt.Key_V:
            # self.set_selection_mode('point') # 假设旧模式已移除
            pass 
        elif event.key() == Qt.Key_E:
            pass # 旧的选择模式暂时忽略或移除
        # ... (其他快捷键，如删除、性能切换等，如果需要保留，应放在这里)
        elif event.key() == Qt.Key_D: # 保留删除快捷键示例
            self.delete_selected_faces()
        elif event.key() == Qt.Key_P: # 保留性能切换快捷键示例
            self.toggle_performance_mode()
        elif event.key() == Qt.Key_A: # 保留坐标轴切换快捷键示例
            self.toggle_axes_visibility()
        else: # Fix: Correctly indented pass for unhandled keys
            pass
            # 确保其他快捷键或默认处理能继续
            # 如果基类 keyPressEvent 有用，调用它
            # super().keyPressEvent(event) 
            # 或者直接让 VTK 处理？但这里是 Qt 的事件
            # 让 VTK 处理键盘事件通常在 VTK 窗口获得焦点时
            # 如果没有其他需要 Qt 处理的快捷键，可以注释掉 super() 调用

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
            
            # --- 更新界面显示 --- 
            # 获取最新的完整计数
            latest_counts = self.model_tracker.get_button_counts()

            # 更新交叉面按钮标签
            if hasattr(self, 'intersection_count'):
                self.adjust_font_size(self.intersection_count, str(latest_counts.get('交叉面', 0)))
            
            # 更新面质量按钮标签 - 未初始化时显示"未分析"
            if hasattr(self, 'quality_count'):
                if hasattr(self, 'face_quality_initialized') and not self.face_quality_initialized:
                    self.adjust_font_size(self.quality_count, "未分析")
                else:
                    self.adjust_font_size(self.quality_count, str(latest_counts.get('面质量', 0)))
            
            # 更新相邻面按钮标签 - 未初始化时显示"未分析"
            if hasattr(self, 'proximity_count'):
                if hasattr(self, 'adjacent_faces_initialized') and not self.adjacent_faces_initialized:
                    self.adjust_font_size(self.proximity_count, "未分析")
                else:
                    self.adjust_font_size(self.proximity_count, str(latest_counts.get('相邻面', 0)))
            
            # 更新自由边按钮标签
            if hasattr(self, 'free_edge_count'):
                self.adjust_font_size(self.free_edge_count, str(latest_counts.get('自由边', 0)))
            
            # 更新重叠边按钮标签
            if hasattr(self, 'overlap_edge_count'):
                self.adjust_font_size(self.overlap_edge_count, str(latest_counts.get('重叠边', 0)))
            
            # 更新重叠点按钮标签
            if hasattr(self, 'overlap_point_count'):
                self.adjust_font_size(self.overlap_point_count, str(latest_counts.get('重叠点', 0)))
                
            # 更新VTK显示 (如果需要)
            if updates: # 如果 updates 非空 (表示 tracker 认为有变化)
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
        """静默运行检测函数（不显示进度条和消息，仅更新状态栏和按钮计数）"""
        try:
            # 备份当前选择状态，以防静默检测意外修改
            temp_faces = self.selected_faces.copy() if self.selected_faces else []
            temp_edges = self.selected_edges.copy() if self.selected_edges else []
            temp_points = self.selected_points.copy() if self.selected_points else []

            # 更新状态栏，提示正在进行的检测
            self.statusBar.showMessage(f"后台更新: 正在检测 {detection_type}...")
            QApplication.processEvents() # 强制处理事件，让状态栏更新显示出来

            selection = None # 用于存储检测结果
            has_cpp = False # 用于记录是否使用了C++实现
            
            # 根据检测类型创建并执行相应的算法
            if detection_type == "自由边":
                algorithm = FreeEdgesAlgorithm(self.mesh_data)
                result = algorithm.execute(parent=None) # parent=None 应该抑制算法内部的消息框
                if 'selected_edges' in result:
                    selection = result['selected_edges']
                    self.adjust_font_size(self.free_edge_count, str(len(selection)))
                    # 更新缓存
                    self.detection_cache['free_edges'] = selection.copy()
                else:
                    self.adjust_font_size(self.free_edge_count, "0")
                    self.detection_cache['free_edges'] = []

            
            elif detection_type == "重叠边":
                algorithm = OverlappingEdgesAlgorithm(self.mesh_data)
                result = algorithm.execute(parent=None)
                if 'selected_edges' in result:
                    selection = result['selected_edges']
                    self.adjust_font_size(self.overlap_edge_count, str(len(selection)))
                    # 更新缓存
                    self.detection_cache['overlapping_edges'] = selection.copy()
                else:
                    self.adjust_font_size(self.overlap_edge_count, "0")
                    self.detection_cache['overlapping_edges'] = []

            
            elif detection_type == "交叉面":
                # 检查增强模块是否可用，以决定使用哪个算法或配置
                enhanced_cpp = hasattr(self, 'has_enhanced_pierced_faces') and self.has_enhanced_pierced_faces

                # 使用合并的交叉/穿刺检测算法
                from algorithms.combined_intersection_algorithm import CombinedIntersectionAlgorithm
                algorithm = CombinedIntersectionAlgorithm(self.mesh_data, detection_mode="pierced")

                # 设置增强标志
                if hasattr(self, 'has_enhanced_pierced_faces'):
                    algorithm.enhanced_cpp_available = self.has_enhanced_pierced_faces

                result = algorithm.execute(parent=None)
                if 'selected_faces' in result:
                    selection = result['selected_faces']
                    self.adjust_font_size(self.intersection_count, str(len(selection)))
                    # 静默更新也需要更新缓存
                    if 'intersection_map' in result:
                       self.detection_cache['face_intersection_map'] = {int(k): v for k, v in result['intersection_map'].items()}
                    self.detection_cache['face_intersections'] = selection.copy()
                else:
                    self.adjust_font_size(self.intersection_count, "0")
                    self.detection_cache['face_intersections'] = []
                    self.detection_cache['face_intersection_map'] = {}

            
            elif detection_type == "面质量":
                # 检查C++实现
                try:
                    import face_quality_cpp
                    has_cpp = True
                except ImportError:
                    has_cpp = False
                
                # 如果未初始化，则跳过自动检测，防止弹出阈值输入框
                # 同时检查阈值是否存在
                # (Fix: use self.face_quality_threshold, not face_quality_threshold)
                if not self.face_quality_initialized or not hasattr(self, 'face_quality_threshold') or self.face_quality_threshold is None:
                    self.statusBar.showMessage(f"后台更新: 面质量未初始化或无阈值，跳过检测")
                    # 还原选择状态后返回
                    self.selected_faces = temp_faces
                    self.selected_edges = temp_edges
                    self.selected_points = temp_points
                    return # 直接返回，不执行此项检测

                algorithm = FaceQualityAlgorithm(self.mesh_data, threshold=self.face_quality_threshold) # 使用已保存的阈值
                algorithm.use_cpp = has_cpp
                result = algorithm.execute(parent=None)
                
                if 'selected_faces' in result and result['selected_faces']:
                    selection = result['selected_faces']
                    self.adjust_font_size(self.quality_count, str(len(selection)))
                    # 更新缓存
                    self.detection_cache['face_quality'] = selection.copy()
                else:
                    self.adjust_font_size(self.quality_count, "0")
                    self.detection_cache['face_quality'] = []

            
            elif detection_type == "相邻面":
                 # 如果未初始化，则跳过自动检测，防止弹出阈值输入框
                 # 同时检查阈值是否存在
                 # (Fix: use self.adjacent_faces_threshold, not adjacent_faces_threshold)
                if not self.adjacent_faces_initialized or not hasattr(self, 'adjacent_faces_threshold') or self.adjacent_faces_threshold is None:
                    self.statusBar.showMessage(f"后台更新: 相邻面未初始化或无阈值，跳过检测")
                    # 还原选择状态后返回
                    self.selected_faces = temp_faces
                    self.selected_edges = temp_edges
                    self.selected_points = temp_points
                    return # 直接返回，不执行此项检测

                # 检查可用的C++模块
                try:
                    import self_intersection_cpp # 假设相邻面检测也使用这个模块
                    has_cpp = True
                except ImportError:
                    has_cpp = False

                algorithm = CombinedIntersectionAlgorithm(self.mesh_data, detection_mode="adjacent", threshold=self.adjacent_faces_threshold) # 使用已保存的阈值
                algorithm.use_cpp = has_cpp
                result = algorithm.execute(parent=None)

                if 'selected_faces' in result and result['selected_faces']:
                    selection = result['selected_faces']
                    self.adjust_font_size(self.proximity_count, str(len(selection)))
                     # 更新缓存
                    self.detection_cache['adjacent_faces'] = selection.copy()
                else:
                    self.adjust_font_size(self.proximity_count, "0")
                    self.detection_cache['adjacent_faces'] = []

            
            elif detection_type == "重叠点":
                # 检查C++实现
                try:
                    import non_manifold_vertices_cpp
                    has_cpp = True
                except ImportError:
                    try:
                        import overlapping_points_cpp
                        has_cpp = True
                    except ImportError:
                        has_cpp = False
                
                # 使用合并后的顶点检测算法
                from algorithms.merged_vertex_detection_algorithm import MergedVertexDetectionAlgorithm
                algorithm = MergedVertexDetectionAlgorithm(self.mesh_data, detection_mode="overlapping")
                algorithm.use_cpp = has_cpp
                result = algorithm.execute(parent=None)
                
                if 'selected_points' in result and result['selected_points']:
                    selection = result['selected_points']
                    self.adjust_font_size(self.overlap_point_count, str(len(selection)))
                    # 更新缓存
                    self.detection_cache['overlapping_points'] = selection.copy()
                else:
                    self.adjust_font_size(self.overlap_point_count, "0")
                    self.detection_cache['overlapping_points'] = []


            # 更新状态栏显示检测完成
            count = len(selection) if selection is not None else 0
            cpp_suffix = " (C++)" if has_cpp else " (Py)"
            self.statusBar.showMessage(f"后台更新: {detection_type} 检测完成，发现 {count} 个问题{cpp_suffix}", 5000) # 显示5秒
            
            # 还原之前的选择状态
            self.selected_faces = temp_faces
            self.selected_edges = temp_edges
            self.selected_points = temp_points
            # 静默更新后不需要强制刷新显示，除非选择状态确实需要被更新（但这里还原了）
            # self.update_display()
                
        except Exception as e:
            # 静默捕获异常，在状态栏显示错误信息
            print(f"静默检测时发生错误: {detection_type} - {str(e)}")
            self.statusBar.showMessage(f"后台更新: {detection_type} 检测失败", 5000) # 显示5秒
            # 同样还原选择
            self.selected_faces = temp_faces
            self.selected_edges = temp_edges
            self.selected_points = temp_points

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
        # 同样使相邻面缓存失效
        self.detection_cache['adjacent_faces'] = None
        
        # 更新显示
        self.update_display()
        self.statusBar.showMessage(f'已删除面 {face_id}')
        
        # 更新模型分析
        self.update_model_analysis()

    # --- 添加新方法 --- (确保只添加一次)
    # (检查是否已存在 _toggle_create_point_ui)
    def _toggle_create_point_options(self):
        """切换"从三坐标创建点"按钮的可见性"""
        if hasattr(self, 'create_point_options_container'):
            is_visible = self.create_point_options_container.isVisible()
            self.create_point_options_container.setVisible(not is_visible)
            # 如果隐藏容器，确保XYZ输入组也隐藏
            if is_visible and hasattr(self, 'xyz_input_group'):
                self.xyz_input_group.setVisible(False)

    def _toggle_xyz_input_ui(self):
        """切换 X, Y, Z 输入区域的可见性"""
        if hasattr(self, 'xyz_input_group'): 
            is_visible = self.xyz_input_group.isVisible()
            self.xyz_input_group.setVisible(not is_visible)

        # --- 确保粘贴的位置正确，例如在其他方法定义之间 ---

    def collapse_selected_vertices(self):
        """
        合并选中的顶点（包括选中边的端点）：
        1. 收集所有要合并的顶点索引（来自 selected_points 和 selected_edges）。
        2. 计算选中顶点的质心。
        3. 创建一个新的顶点列表，包含未选中的顶点和质心。
        4. 创建旧索引到新索引的映射。
        5. 遍历所有面片，更新顶点索引为新索引。
        6. 移除退化的面片（少于3个唯一顶点）。
        7. 更新 mesh_data。
        """
        # 1. 收集所有要合并的顶点索引
        vertices_to_collapse = set(self.selected_points)
        num_from_points = len(vertices_to_collapse)

        for v1_idx, v2_idx in self.selected_edges:
            vertices_to_collapse.add(v1_idx)
            vertices_to_collapse.add(v2_idx)

        num_from_edges = len(vertices_to_collapse) - num_from_points
        total_vertices_to_collapse = len(vertices_to_collapse)

        if total_vertices_to_collapse < 2:
            QMessageBox.warning(self, "合并顶点", "请至少选择两个顶点或一条边进行合并。")
            return

        print(f"开始合并 {total_vertices_to_collapse} 个顶点 ({num_from_points} 个直接选中, {num_from_edges} 个来自选中边): {vertices_to_collapse}")

        # 使用这个合并后的集合进行后续操作
        selected_indices = vertices_to_collapse
        # 需要将 set 转换为 list 或 tuple 来索引 numpy 数组
        selected_indices_list = list(selected_indices)
        if not selected_indices_list: # 再次检查以防万一
             print("错误：无法获取有效的顶点索引列表进行合并。")
             return
        try:
            # 确保索引在范围内
            max_old_idx = len(self.mesh_data['vertices']) - 1
            valid_indices = [idx for idx in selected_indices_list if 0 <= idx <= max_old_idx]
            if len(valid_indices) != len(selected_indices_list):
                print(f"警告：移除了无效的顶点索引。原始: {selected_indices_list}, 有效: {valid_indices}")
                if not valid_indices:
                    print("错误：没有有效的顶点索引可供合并。")
                    return
                selected_indices_list = valid_indices # 使用有效的索引
                selected_indices = set(valid_indices) # 更新集合以保持一致

            selected_vertices = self.mesh_data['vertices'][selected_indices_list]
        except IndexError as e:
            print(f"错误：索引顶点时出错 - {e}。选定索引: {selected_indices_list}, 网格顶点数: {len(self.mesh_data['vertices'])}")
            QMessageBox.critical(self, "错误", f"合并顶点时索引错误: {e}")
            return
        except Exception as e: # 捕获其他可能的错误
            print(f"错误：获取选中顶点时发生未知错误 - {e}")
            QMessageBox.critical(self, "错误", f"合并顶点时发生未知错误: {e}")
            return


        # 2. 计算质心
        if selected_vertices.size == 0:
             print("错误：无法计算质心，没有有效的选中顶点。")
             return
        centroid = np.mean(selected_vertices, axis=0)
        print(f"质心计算完成: {centroid}")

        # --- 后续步骤使用 selected_indices (集合) 进行判断 ---

        # 3. 创建新顶点列表和映射
        new_vertices = []
        old_to_new_vertex_map = {}
        current_new_idx = 0
        kept_vertex_indices = []

        for old_idx, vertex in enumerate(self.mesh_data['vertices']):
            if old_idx not in selected_indices: # 使用集合判断更快
                new_vertices.append(vertex)
                old_to_new_vertex_map[old_idx] = current_new_idx
                kept_vertex_indices.append(old_idx)
                current_new_idx += 1

        # 4. 添加质心到新列表，并更新映射
        centroid_new_idx = current_new_idx
        new_vertices.append(centroid)
        for old_idx in selected_indices: # 遍历集合
            old_to_new_vertex_map[old_idx] = centroid_new_idx

        print(f"新顶点列表创建完成，共 {len(new_vertices)} 个顶点 (质心索引: {centroid_new_idx})")

        # 5. 创建新面片列表
        new_faces = []
        original_faces = self.mesh_data['faces']
        num_original_faces = len(original_faces)
        num_degenerate = 0

        print(f"开始处理 {num_original_faces} 个原始面片...")

        for face_idx, old_face in enumerate(original_faces):
            updated_face_indices = []
            valid_face = True
            for old_v_idx in old_face:
                # 检查旧索引是否存在于映射中
                if old_v_idx in old_to_new_vertex_map:
                    updated_face_indices.append(old_to_new_vertex_map[old_v_idx])
                else:
                    # 如果顶点既不是被合并的，也不是保留的，说明数据有问题
                    # （注意：这里之前的判断 `old_idx` 变量名用错了，应该是 `old_v_idx`）
                    if old_v_idx not in selected_indices and old_v_idx >= len(self.mesh_data['vertices']):
                         print(f"警告: 面 {face_idx} 包含无效的旧顶点索引 {old_v_idx} (越界)，跳过此面。")
                    else:
                         # 理论上不应发生，但作为保险
                         print(f"警告: 面 {face_idx} 中的顶点 {old_v_idx} 意外地未在映射中找到，跳过此面。")
                    valid_face = False
                    break

            if not valid_face:
                continue

            # 6. 检查并移除退化面片 (至少3个 *唯一* 的顶点)
            unique_indices = set(updated_face_indices)
            if len(unique_indices) < 3:
                num_degenerate += 1
                # print(f"面 {face_idx} 退化: {old_face} -> {updated_face_indices}")
                continue

            # 确保新面索引不超出新顶点列表范围 (理论上不应发生)
            max_new_idx = len(new_vertices) - 1
            if any(idx > max_new_idx for idx in updated_face_indices):
                 print(f"警告: 面 {face_idx} 映射到了无效的新顶点索引 {updated_face_indices} (最大允许 {max_new_idx})，跳过此面。")
                 continue

            new_faces.append(updated_face_indices)

        print(f"面片处理完成，保留 {len(new_faces)} 个面片，移除了 {num_degenerate} 个退化面片。")

        # 7. 更新 mesh_data
        self.mesh_data['vertices'] = np.array(new_vertices, dtype=np.float64)
        # 确保面片列表不为空再转换为 NumPy 数组
        if not new_faces:
             print("警告：合并后没有剩余有效面片。")
             # 保留空的面片数组，或根据需要处理
             self.mesh_data['faces'] = np.array([], dtype=np.int32)
        else:
             self.mesh_data['faces'] = np.array(new_faces, dtype=np.int32)


        # 清除选择
        self.selected_points = []
        self.selected_edges = []
        self.selected_faces = []
        self.cached_mesh = None # 清除 VTK 网格缓存

        print("mesh_data 更新完成，选择已清除。")

        # 标记模型修改并更新分析和显示
        self.mark_model_modified()
        self.update_model_analysis() # 更新旁边按钮的计数
        self.update_display()
        self.statusBar.showMessage(f"已合并 {total_vertices_to_collapse} 个顶点。")
        print("合并操作完成。")

    # --- 确保粘贴在此方法定义之后 ---
        """
        合并选中的顶点：
        1. 计算选中顶点的质心。
        2. 创建一个新的顶点列表，包含未选中的顶点和质心。
        3. 创建旧索引到新索引的映射。
        4. 遍历所有面片，更新顶点索引为新索引。
        5. 移除退化的面片（少于3个唯一顶点）。
        6. 更新 mesh_data。
        """
        if len(self.selected_points) < 2:
            QMessageBox.warning(self, "合并顶点", "请至少选择两个顶点进行合并。")
            return

        print(f"开始合并 {len(self.selected_points)} 个顶点: {self.selected_points}")

        selected_indices = set(self.selected_points)
        selected_vertices = self.mesh_data['vertices'][self.selected_points]

        # 1. 计算质心
        centroid = np.mean(selected_vertices, axis=0)
        print(f"质心计算完成: {centroid}")

        # 2. 创建新顶点列表和映射
        new_vertices = []
        old_to_new_vertex_map = {}
        current_new_idx = 0
        kept_vertex_indices = [] # 记录保留的旧顶点索引

        for old_idx, vertex in enumerate(self.mesh_data['vertices']):
            if old_idx not in selected_indices:
                new_vertices.append(vertex)
                old_to_new_vertex_map[old_idx] = current_new_idx
                kept_vertex_indices.append(old_idx) 
                current_new_idx += 1

        # 3. 添加质心到新列表，并更新映射
        centroid_new_idx = current_new_idx
        new_vertices.append(centroid)
        for old_idx in selected_indices:
            old_to_new_vertex_map[old_idx] = centroid_new_idx

        print(f"新顶点列表创建完成，共 {len(new_vertices)} 个顶点 (质心索引: {centroid_new_idx})")

        # 4. 创建新面片列表
        new_faces = []
        original_faces = self.mesh_data['faces']
        num_original_faces = len(original_faces)
        num_degenerate = 0

        print(f"开始处理 {num_original_faces} 个原始面片...")

        for face_idx, old_face in enumerate(original_faces):
            updated_face_indices = []
            valid_face = True
            for old_v_idx in old_face:
                if old_v_idx in old_to_new_vertex_map:
                    updated_face_indices.append(old_to_new_vertex_map[old_v_idx])
                else:
                    print(f"警告: 面 {face_idx} 中的顶点 {old_v_idx} 在映射中未找到，跳过此面。")
                    valid_face = False
                    break 

            if not valid_face:
                continue

            # 5. 检查并移除退化面片
            if len(set(updated_face_indices)) < 3:
                num_degenerate += 1
                continue 

            new_faces.append(updated_face_indices)

        print(f"面片处理完成，保留 {len(new_faces)} 个面片，移除了 {num_degenerate} 个退化面片。")

        # 6. 更新 mesh_data
        self.mesh_data['vertices'] = np.array(new_vertices, dtype=np.float64)
        self.mesh_data['faces'] = np.array(new_faces, dtype=np.int32)

        # 清除选择
        self.selected_points = []
        self.selected_edges = []
        self.selected_faces = []
        self.cached_mesh = None # 清除 VTK 网格缓存

        print("mesh_data 更新完成，选择已清除。")

        # 标记模型修改并更新分析和显示
        self.mark_model_modified()
        self.update_model_analysis() # 更新旁边按钮的计数
        self.update_display()
        self.statusBar.showMessage(f"已合并 {len(selected_indices)} 个顶点。")
        print("合并操作完成。")

    def split_selected_elements(self):
        """
        分割选中的边或面中的边：
        1. 收集所有需要分割的唯一边（来自选中的边和选中的面的边）。
        2. 计算每条要分割边的中点，并添加为新顶点。
        3. 创建旧边到新中点索引的映射。
        4. 重建面列表：
           - 遍历旧面片。
           - 检查其边是否被分割。
           - 根据被分割边的数量（1, 2, 或 3），创建新的面片。
        5. 更新 mesh_data。
        """
        if not self.selected_edges and not self.selected_faces:
            QMessageBox.warning(self, "分割", "请先选择要分割的边或面。")
            return

        print("开始分割操作...")
        start_time = time.time()

        # 1. 收集唯一需要分割的边
        edges_to_split = set()
        # 添加直接选中的边
        for edge in self.selected_edges:
            edges_to_split.add(tuple(sorted(edge)))
        # 添加选中面的边
        for face_idx in self.selected_faces:
            if 0 <= face_idx < len(self.mesh_data['faces']):
                face = self.mesh_data['faces'][face_idx]
                edges_to_split.add(tuple(sorted((face[0], face[1]))))
                edges_to_split.add(tuple(sorted((face[1], face[2]))))
                edges_to_split.add(tuple(sorted((face[2], face[0]))))

        if not edges_to_split:
            print("没有有效的边可供分割。")
            return

        print(f"共找到 {len(edges_to_split)} 条唯一边需要分割。")

        # 2. & 3. 计算中点并创建映射
        old_vertices = self.mesh_data['vertices']
        new_vertices = list(old_vertices) # 复制旧顶点
        edge_to_midpoint_map = {}
        vertex_offset = len(old_vertices) # 新顶点的起始索引

        for i, edge in enumerate(edges_to_split):
            v1_idx, v2_idx = edge
            if 0 <= v1_idx < len(old_vertices) and 0 <= v2_idx < len(old_vertices):
                midpoint = (old_vertices[v1_idx] + old_vertices[v2_idx]) / 2.0
                new_vertices.append(midpoint)
                edge_to_midpoint_map[edge] = vertex_offset + i
            else:
                print(f"警告: 边 {edge} 包含无效顶点索引，跳过。")

        print(f"创建了 {len(edge_to_midpoint_map)} 个新中点顶点。")

        # 4. 重建面列表
        new_faces = []
        original_faces = self.mesh_data['faces']
        num_split_faces = 0

        for face_idx, face in enumerate(original_faces):
            v1, v2, v3 = face
            edge1 = tuple(sorted((v1, v2)))
            edge2 = tuple(sorted((v2, v3)))
            edge3 = tuple(sorted((v3, v1)))

            m1 = edge_to_midpoint_map.get(edge1)
            m2 = edge_to_midpoint_map.get(edge2)
            m3 = edge_to_midpoint_map.get(edge3)

            split_count = sum(1 for m in [m1, m2, m3] if m is not None)

            if split_count == 0:
                new_faces.append(face)
            elif split_count == 1:
                num_split_faces += 1
                if m1 is not None:
                    new_faces.append([v1, m1, v3])
                    new_faces.append([m1, v2, v3])
                elif m2 is not None:
                    new_faces.append([v2, m2, v1])
                    new_faces.append([m2, v3, v1])
                elif m3 is not None:
                    new_faces.append([v3, m3, v2])
                    new_faces.append([m3, v1, v2])
            elif split_count == 2:
                num_split_faces += 1
                if m1 is None: 
                    new_faces.append([v1, v2, m3])
                    new_faces.append([v2, m2, m3])
                    new_faces.append([m2, v3, m3])
                elif m2 is None: 
                    new_faces.append([v2, v3, m1])
                    new_faces.append([v3, m3, m1])
                    new_faces.append([m3, v1, m1])
                elif m3 is None: 
                    new_faces.append([v3, v1, m2])
                    new_faces.append([v1, m1, m2])
                    new_faces.append([m1, v2, m2])
            elif split_count == 3:
                num_split_faces += 1
                new_faces.append([v1, m1, m3])
                new_faces.append([v2, m2, m1])
                new_faces.append([v3, m3, m2])
                new_faces.append([m1, m2, m3])

        print(f"面片重建完成，生成 {len(new_faces)} 个新面片，分割了 {num_split_faces} 个原面片。")

        # 5. 更新 mesh_data
        self.mesh_data['vertices'] = np.array(new_vertices, dtype=np.float64)
        self.mesh_data['faces'] = np.array(new_faces, dtype=np.int32)

        # 清除选择
        self.selected_points = []
        self.selected_edges = []
        self.selected_faces = []
        self.cached_mesh = None

        end_time = time.time()
        print(f"mesh_data 更新完成，选择已清除。分割操作耗时: {end_time - start_time:.4f} 秒")

        # 标记模型修改并更新分析和显示
        self.mark_model_modified()
        self.update_model_analysis()
        self.update_display()
        self.statusBar.showMessage(f"已分割 {len(edges_to_split)} 条边。")

    def swap_selected_edge(self):
        """
        交换选中的边：
        1. 检查是否只选中了一条边。
        2. 查找共享该边的两个面片。
        3. 识别两个面片中的第三个顶点。
        4. （可选）执行有效性检查。
        5. 删除旧面片，创建由新边连接的新面片。
        6. 更新 mesh_data。
        """
        if len(self.selected_edges) != 1:
            QMessageBox.warning(self, "交换边", "请只选择一条内部边进行交换。")
            return

        edge_to_swap_tuple = tuple(sorted(self.selected_edges[0]))
        v1, v2 = edge_to_swap_tuple
        print(f"开始交换边: {edge_to_swap_tuple}")

        # 2. 查找共享该边的两个面片
        shared_face_indices = []
        original_faces = self.mesh_data['faces']
        for idx, face in enumerate(original_faces):
            face_set = set(face)
            if v1 in face_set and v2 in face_set:
                shared_face_indices.append(idx)

        if len(shared_face_indices) != 2:
            QMessageBox.warning(self, "交换边", f"选中的边 ({v1}-{v2}) 不是内部边（被 {len(shared_face_indices)} 个面共享）。无法交换。")
            print(f"错误: 边 {edge_to_swap_tuple} 共享了 {len(shared_face_indices)} 个面: {shared_face_indices}")
            return

        face1_idx, face2_idx = shared_face_indices
        face1 = original_faces[face1_idx]
        face2 = original_faces[face2_idx]
        print(f"找到共享面: 索引 {face1_idx} -> {face1}, 索引 {face2_idx} -> {face2}")

        # 3. 识别第三个顶点
        try:
            v3 = [v for v in face1 if v != v1 and v != v2][0]
            v4 = [v for v in face2 if v != v1 and v != v2][0]
        except IndexError:
             print(f"错误: 无法从面 {face1} 或 {face2} 中找到第三个顶点。")
             QMessageBox.critical(self, "错误", "查找共享面顶点时出错。")
             return

        if v3 == v4:
             print(f"错误: 两个共享面具有相同的第三个顶点 {v3}。无法交换。")
             QMessageBox.warning(self, "交换边", "无法交换此边（可能导致退化）。")
             return

        print(f"找到对角顶点: v3={v3}, v4={v4}")

        # 5. 创建新面片
        new_face1 = [v1, v3, v4]
        new_face2 = [v2, v4, v3]
        print(f"创建新面片: {new_face1} 和 {new_face2}")

        # 6. 更新 mesh_data
        new_faces_list = []
        deleted_count = 0
        indices_to_delete = {face1_idx, face2_idx}
        for idx, face in enumerate(original_faces):
            if idx not in indices_to_delete:
                new_faces_list.append(face)
            else:
                deleted_count += 1
        
        # 添加新创建的面
        new_faces_list.append(new_face1)
        new_faces_list.append(new_face2)

        if deleted_count != 2:
             print(f"警告：尝试删除共享面时出现问题 (删除了 {deleted_count} 个)。")
             # 可能需要回退或发出错误

        self.mesh_data['faces'] = np.array(new_faces_list, dtype=np.int32)
        print(f"面列表已更新，包含 {len(new_faces_list)} 个面。")

        # 清除选择
        self.selected_points = []
        self.selected_edges = []
        self.selected_faces = []
        self.cached_mesh = None
        print("选择已清除。")

        # 标记模型修改并更新分析和显示
        self.mark_model_modified()
        self.update_model_analysis()
        self.update_display()
        self.statusBar.showMessage(f"已交换边 ({v1}-{v2}) <-> ({v3}-{v4})。")
        print("交换边操作完成。")

    def fill_polygonal_patch(self):
        """
        填充由选中边构成的多边形孔洞：
        1. 验证选中的边是否构成单个闭合环路。
        2. 计算环路顶点的质心。
        3. 添加质心作为新顶点。
        4. 通过连接质心和环路边来创建新的三角面片。
        5. 更新 mesh_data。
        """
        if len(self.selected_edges) < 3:
            QMessageBox.warning(self, "填充孔洞", "请至少选择构成闭合环路的3条边。")
            return

        print(f"开始填充孔洞，选择了 {len(self.selected_edges)} 条边。")
        selected_edges_set = set(tuple(sorted(edge)) for edge in self.selected_edges)

        # 1. 构建邻接表并检查顶点度数
        adj = defaultdict(list)
        vertices_in_selection = set()
        for u, v in selected_edges_set:
            adj[u].append(v)
            adj[v].append(u)
            vertices_in_selection.add(u)
            vertices_in_selection.add(v)

        # 检查所有相关顶点的度数是否为2
        degrees = {v: len(adj[v]) for v in vertices_in_selection}
        if any(d != 2 for d in degrees.values()):
            invalid_vertices = [v for v, d in degrees.items() if d != 2]
            QMessageBox.warning(self, "填充孔洞", f"选中的边未形成简单闭合环路。顶点 {invalid_vertices} 的度数不为2。")
            print(f"错误：环路检测失败，顶点度数不为2。度数: {degrees}")
            return

        # 2. 提取有序环路顶点
        ordered_loop = []
        if not vertices_in_selection: # 如果没有顶点直接返回
            QMessageBox.warning(self, "填充孔洞", "选择的边没有关联顶点。")
            return
            
        start_node = next(iter(vertices_in_selection)) # 从任意顶点开始
        current_node = start_node
        visited_nodes = set()

        try:
            for _ in range(len(vertices_in_selection)):
                 ordered_loop.append(current_node)
                 visited_nodes.add(current_node)
                 found_next = False
                 for neighbor in adj[current_node]:
                     if neighbor not in visited_nodes:
                         current_node = neighbor
                         found_next = True
                         break
                 # 如果没找到未访问的邻居，检查是否能回到起点
                 if not found_next:
                     if start_node in adj[current_node] and len(ordered_loop) == len(vertices_in_selection):
                         # 已经访问完所有点，可以闭合了
                         break # 正常结束循环
                     else:
                         # 无法继续遍历，可能不是单环或有中断
                         raise ValueError("无法找到下一个顶点，环路可能中断或不完整。")
            
            # 验证是否形成完整环路
            if len(ordered_loop) != len(vertices_in_selection):
                 raise ValueError(f"提取的顶点数 ({len(ordered_loop)}) 与选择中的唯一顶点数 ({len(vertices_in_selection)}) 不匹配。")
            if start_node not in adj[ordered_loop[-1]]: # 检查首尾是否相连
                 raise ValueError("提取的环路未正确闭合。")

        except ValueError as e:
            QMessageBox.warning(self, "填充孔洞", f"无法提取有效的单闭合环路: {e}")
            print(f"错误：提取有序环路失败: {e}")
            return
        except Exception as e: # 捕捉其他可能的错误
             QMessageBox.critical(self, "错误", f"提取环路时发生意外错误: {e}")
             print(f"意外错误: {e}")
             return


        print(f"提取的有序环路顶点 ({len(ordered_loop)}个): {ordered_loop}")

        # 3. 计算质心并添加为新顶点
        loop_vertices_coords = self.mesh_data['vertices'][ordered_loop]
        centroid = np.mean(loop_vertices_coords, axis=0)
        centroid_idx = len(self.mesh_data['vertices'])
        self.mesh_data['vertices'] = np.vstack([self.mesh_data['vertices'], centroid])
        print(f"质心计算完成: {centroid}，新顶点索引: {centroid_idx}")

        # 4. 创建新的三角面片
        new_faces_to_add = []
        num_loop_vertices = len(ordered_loop)
        for i in range(num_loop_vertices):
            v_i = ordered_loop[i]
            v_next = ordered_loop[(i + 1) % num_loop_vertices] # 处理环路末尾连接回开头
            # 创建面片 (质心, 当前点, 下一个点)
            # 注意：顶点顺序可能影响法线方向，这里假设逆时针为外法线
            new_faces_to_add.append([centroid_idx, v_i, v_next])

        print(f"创建了 {len(new_faces_to_add)} 个新三角面片。")

        # 5. 更新 mesh_data
        if new_faces_to_add:
            # 检查原始面片数组是否为空
            if self.mesh_data['faces'].size == 0:
                self.mesh_data['faces'] = np.array(new_faces_to_add, dtype=np.int32)
            else:
                self.mesh_data['faces'] = np.vstack([self.mesh_data['faces'], np.array(new_faces_to_add, dtype=np.int32)])

        # 清除选择
        self.selected_points = []
        self.selected_edges = []
        self.selected_faces = []
        self.cached_mesh = None # 清除 VTK 网格缓存

        print("mesh_data 更新完成，选择已清除。")

        # 标记模型修改并更新分析和显示
        self.mark_model_modified()
        self.update_model_analysis()
        self.update_display()
        self.statusBar.showMessage(f"已使用 {len(new_faces_to_add)} 个面片填充孔洞。")
        print("填充孔洞操作完成。")

    # --- 重命名旧方法 --- 
    def _fill_polygonal_patch_by_edges(self):
        """ (旧功能) 填充由选中边构成的多边形孔洞 """
        # ... (旧的 fill_polygonal_patch 代码保持不变，只是方法名改了) ...
        if len(self.selected_edges) < 3:
            QMessageBox.warning(self, "填充孔洞", "请至少选择构成闭合环路的3条边。")
            return

        print(f"开始填充孔洞，选择了 {len(self.selected_edges)} 条边。")
        selected_edges_set = set(tuple(sorted(edge)) for edge in self.selected_edges)

        # 1. 构建邻接表并检查顶点度数
        adj = defaultdict(list)
        vertices_in_selection = set()
        for u, v in selected_edges_set:
            adj[u].append(v)
            adj[v].append(u)
            vertices_in_selection.add(u)
            vertices_in_selection.add(v)

        # 检查所有相关顶点的度数是否为2
        degrees = {v: len(adj[v]) for v in vertices_in_selection}
        if any(d != 2 for d in degrees.values()):
            invalid_vertices = [v for v, d in degrees.items() if d != 2]
            QMessageBox.warning(self, "填充孔洞", f"选中的边未形成简单闭合环路。顶点 {invalid_vertices} 的度数不为2。")
            print(f"错误：环路检测失败，顶点度数不为2。度数: {degrees}")
            return

        # 2. 提取有序环路顶点
        ordered_loop = []
        if not vertices_in_selection: # 如果没有顶点直接返回
            QMessageBox.warning(self, "填充孔洞", "选择的边没有关联顶点。")
            return
            
        start_node = next(iter(vertices_in_selection)) # 从任意顶点开始
        current_node = start_node
        visited_nodes = set()

        try:
            for _ in range(len(vertices_in_selection)):
                 ordered_loop.append(current_node)
                 visited_nodes.add(current_node)
                 found_next = False
                 for neighbor in adj[current_node]:
                     if neighbor not in visited_nodes:
                         current_node = neighbor
                         found_next = True
                         break
                 # 如果没找到未访问的邻居，检查是否能回到起点
                 if not found_next:
                     if start_node in adj[current_node] and len(ordered_loop) == len(vertices_in_selection):
                         # 已经访问完所有点，可以闭合了
                         break # 正常结束循环
                     else:
                         # 无法继续遍历，可能不是单环或有中断
                         raise ValueError("无法找到下一个顶点，环路可能中断或不完整。")
            
            # 验证是否形成完整环路
            if len(ordered_loop) != len(vertices_in_selection):
                 raise ValueError(f"提取的顶点数 ({len(ordered_loop)}) 与选择中的唯一顶点数 ({len(vertices_in_selection)}) 不匹配。")
            if start_node not in adj[ordered_loop[-1]]: # 检查首尾是否相连
                 raise ValueError("提取的环路未正确闭合。")

        except ValueError as e:
            QMessageBox.warning(self, "填充孔洞", f"无法提取有效的单闭合环路: {e}")
            print(f"错误：提取有序环路失败: {e}")
            return
        except Exception as e: # 捕捉其他可能的错误
             QMessageBox.critical(self, "错误", f"提取环路时发生意外错误: {e}")
             print(f"意外错误: {e}")
             return


        print(f"提取的有序环路顶点 ({len(ordered_loop)}个): {ordered_loop}")

        # 3. 计算质心并添加为新顶点
        loop_vertices_coords = self.mesh_data['vertices'][ordered_loop]
        centroid = np.mean(loop_vertices_coords, axis=0)
        centroid_idx = len(self.mesh_data['vertices'])
        self.mesh_data['vertices'] = np.vstack([self.mesh_data['vertices'], centroid])
        print(f"质心计算完成: {centroid}，新顶点索引: {centroid_idx}")

        # 4. 创建新的三角面片
        new_faces_to_add = []
        num_loop_vertices = len(ordered_loop)
        for i in range(num_loop_vertices):
            v_i = ordered_loop[i]
            v_next = ordered_loop[(i + 1) % num_loop_vertices] # 处理环路末尾连接回开头
            # 创建面片 (质心, 当前点, 下一个点)
            # 注意：顶点顺序可能影响法线方向，这里假设逆时针为外法线
            new_faces_to_add.append([centroid_idx, v_i, v_next])

        print(f"创建了 {len(new_faces_to_add)} 个新三角面片。")

        # 5. 更新 mesh_data
        if new_faces_to_add:
            # 检查原始面片数组是否为空
            if self.mesh_data['faces'].size == 0:
                self.mesh_data['faces'] = np.array(new_faces_to_add, dtype=np.int32)
            else:
                self.mesh_data['faces'] = np.vstack([self.mesh_data['faces'], np.array(new_faces_to_add, dtype=np.int32)])

        # 清除选择
        self.selected_points = []
        self.selected_edges = []
        self.selected_faces = []
        self.cached_mesh = None # 清除 VTK 网格缓存

        print("mesh_data 更新完成，选择已清除。")

        # 标记模型修改并更新分析和显示
        self.mark_model_modified()
        self.update_model_analysis()
        self.update_display()
        self.statusBar.showMessage(f"已使用 {len(new_faces_to_add)} 个面片填充孔洞。")
        print("填充孔洞操作完成。")

    # --- 交互式面片创建相关方法 --- 

    def start_interactive_face_creation(self, checked):
        """启动或停止交互式面片创建模式"""
        if checked: # 用户点击按钮，进入创建模式
            if self.is_creating_face: # 如果已经在创建中（异常情况），先取消
                self.cancel_interactive_face_creation()
                
            self.is_creating_face = True
            self.new_face_points = []
            QApplication.setOverrideCursor(Qt.CrossCursor) # 设置鼠标样式
            self.statusBar.showMessage("交互式面片创建模式：请在模型上点击选择顶点 (右键完成)")
            
            # 清除之前的选择，避免干扰
            self.clear_all_selections()
            
            # 初始化预览 Actors (如果尚未创建)
            if self.preview_actor is None:
                self.preview_actor = self._create_preview_actor(dashed=True)
                self.renderer.AddActor(self.preview_actor)
            if self.fixed_edges_actor is None:
                self.fixed_edges_actor = self._create_preview_actor(dashed=False)
                self.renderer.AddActor(self.fixed_edges_actor)
                
            # 强制渲染以显示初始状态和鼠标
            self.vtk_widget.GetRenderWindow().Render()
                
        else: # 用户再次点击按钮，或程序调用取消
            self.cancel_interactive_face_creation()

    def cancel_interactive_face_creation(self):
        """取消交互式面片创建模式"""
        if not self.is_creating_face:
            return # 本身就不在创建模式中，无需操作
            
        self.is_creating_face = False
        self.new_face_points = []
        QApplication.restoreOverrideCursor() # 恢复默认鼠标样式
        
        # 移除预览 Actors
        if self.preview_actor:
            self.renderer.RemoveActor(self.preview_actor)
            self.preview_actor = None # 重置 actor 变量
        if self.fixed_edges_actor:
            self.renderer.RemoveActor(self.fixed_edges_actor)
            self.fixed_edges_actor = None
            
        # 确保按钮状态反映模式已取消
        if self.fill_patch_btn.isChecked():
            self.fill_patch_btn.setChecked(False)
            
        self.statusBar.showMessage("已退出交互式面片创建模式")
        self.vtk_widget.GetRenderWindow().Render() # 刷新视图以移除预览线
        
    def _create_preview_actor(self, dashed=False):
        """辅助方法：创建用于预览线或固定边的 Actor"""
        poly_data = vtk.vtkPolyData()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(poly_data)
        # ResolveCoincidentTopology might help prevent z-fighting if lines are exactly on surface
        mapper.SetResolveCoincidentTopologyToPolygonOffset() 
        mapper.SetResolveCoincidentTopologyPolygonOffsetParameters(-1.0, -1.0)
        
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetLineWidth(2) # 线宽
        if dashed:
            prop.SetLineStipplePattern(0xF0F0) # 虚线样式
            prop.SetLineStippleRepeatFactor(2)
            prop.SetColor(0.2, 0.5, 1.0) # 预览线用蓝色
        else:
            prop.SetColor(1.0, 0.2, 0.2) # 固定边用红色
        # 禁用光照，使其颜色恒定
        prop.LightingOff()
        # --- 移除 SetDepthTest --- 
        # prop.SetDepthTest(False) # Removed due to AttributeError
        actor.SetPickable(False) # 预览线不可选中
        return actor
        
    # --- 其他方法 ---

    def on_right_button_press(self, obj, event):
        """处理鼠标右键按下事件，用于完成面片创建"""
        if self.is_creating_face:
            if len(self.new_face_points) >= 3:
                print("Right-click detected, finalizing face creation...")
                self.finalize_interactive_face_creation()
            else:
                QMessageBox.warning(self, "创建面片", "至少需要选择3个点才能创建面片。")
                # 可以选择取消模式，或者让用户继续添加点
                # self.cancel_interactive_face_creation()
            
            # 阻止默认的右键菜单或其他交互
            # self.iren.GetInteractorStyle().OnRightButtonDown() # 可能不需要调用基类
            return # 消耗掉右键事件
            
        # 如果不在创建模式，允许默认的右键交互（例如上下文菜单）
        # 注意：之前的 on_pick 方法中有右键菜单逻辑，现在需要调整
        # 或者，让基类处理
        self.iren.GetInteractorStyle().OnRightButtonDown()

    # --- 添加预览更新方法 --- 
    def _update_preview_lines(self, current_mouse_pos):
        """更新预览线的 Actor"""
        if not self.preview_actor or not self.new_face_points:
            return
            
        points = vtk.vtkPoints()
        lines = vtk.vtkCellArray()
        
        # 添加所有已固定的点 + 当前鼠标位置
        all_preview_points = self.new_face_points + [current_mouse_pos]
        for pt in all_preview_points:
            points.InsertNextPoint(pt)
            
        num_pts = len(all_preview_points)
        if num_pts >= 2:
            # 添加连接最后一个固定点到鼠标的线
            line1 = vtk.vtkLine()
            line1.GetPointIds().SetId(0, num_pts - 2) # last fixed point index
            line1.GetPointIds().SetId(1, num_pts - 1) # current mouse pos index
            lines.InsertNextCell(line1)
            
            # 如果点数大于2，添加连接鼠标到第一个点的线
            if num_pts > 2:
                line2 = vtk.vtkLine()
                line2.GetPointIds().SetId(0, num_pts - 1) # current mouse pos index
                line2.GetPointIds().SetId(1, 0)         # first fixed point index
                lines.InsertNextCell(line2)
                
        poly_data = self.preview_actor.GetMapper().GetInput()
        poly_data.SetPoints(points)
        poly_data.SetLines(lines)
        poly_data.Modified() # 通知 VTK 数据已改变
        self.preview_actor.GetMapper().Update()

    def _update_fixed_edges_display(self):
        """更新固定边的 Actor"""
        if not self.fixed_edges_actor or len(self.new_face_points) < 2:
             # 如果少于2个点，清空固定边显示
            if self.fixed_edges_actor:
                 poly_data = self.fixed_edges_actor.GetMapper().GetInput()
                 poly_data.Initialize()
                 poly_data.Modified()
                 self.fixed_edges_actor.GetMapper().Update()
            return
            
        points = vtk.vtkPoints()
        lines = vtk.vtkCellArray()
        
        for i, pt in enumerate(self.new_face_points):
            points.InsertNextPoint(pt)
            if i > 0:
                line = vtk.vtkLine()
                line.GetPointIds().SetId(0, i - 1)
                line.GetPointIds().SetId(1, i)
                lines.InsertNextCell(line)
                
        poly_data = self.fixed_edges_actor.GetMapper().GetInput()
        poly_data.SetPoints(points)
        poly_data.SetLines(lines)
        poly_data.Modified()
        self.fixed_edges_actor.GetMapper().Update()
        
    # --- 添加最终创建方法 (目前为空) --- 
    def finalize_interactive_face_creation(self):
        """最终创建面片"""
        print("Finalizing face creation...")
        # 1. 获取点
        points_to_add = self.new_face_points
        if len(points_to_add) < 3:
            print("Error: Not enough points to create face.")
            self.cancel_interactive_face_creation()
            return
            
        # 2. 添加新顶点到 mesh_data
        start_new_vertex_index = len(self.mesh_data['vertices'])
        self.mesh_data['vertices'] = np.vstack([self.mesh_data['vertices'], np.array(points_to_add)])
        new_vertex_indices = list(range(start_new_vertex_index, start_new_vertex_index + len(points_to_add)))
        print(f"Added {len(points_to_add)} new vertices. Indices: {new_vertex_indices}")
        
        # 3. 三角化 (扇形三角化)
        new_faces_to_add = []
        if len(new_vertex_indices) >= 3:
            v0_idx = new_vertex_indices[0]
            for i in range(1, len(new_vertex_indices) - 1):
                v1_idx = new_vertex_indices[i]
                v2_idx = new_vertex_indices[i+1]
                new_faces_to_add.append([v0_idx, v1_idx, v2_idx])
        print(f"Created {len(new_faces_to_add)} new triangle faces.")
        
        # 4. 添加新面片到 mesh_data
        if new_faces_to_add:
            if self.mesh_data['faces'].size == 0:
                self.mesh_data['faces'] = np.array(new_faces_to_add, dtype=np.int32)
            else:
                self.mesh_data['faces'] = np.vstack([self.mesh_data['faces'], np.array(new_faces_to_add, dtype=np.int32)])
        
        # 5. 清理
        self.cancel_interactive_face_creation()
        
        # 6. 更新
        self.cached_mesh = None # 使缓存失效
        self.mark_model_modified()
        self.update_model_analysis()
        self.update_display()
        self.statusBar.showMessage(f"成功创建了 {len(new_faces_to_add)} 个新面片")
