import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QFrame, QLabel, QLineEdit,
                           QGridLayout, QMessageBox, QStatusBar)
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
        
        # 添加VTK窗口
        right_layout.addWidget(self.vtk_widget, stretch=1)
        
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
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.iren = self.vtk_widget.GetRenderWindow().GetInteractor()
        
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
        
        mask = np.ones(len(self.mesh_data['faces']), dtype=bool)
        mask[self.selected_faces] = False
        
        self.mesh_data['faces'] = self.mesh_data['faces'][mask]
        if 'normals' in self.mesh_data:
            self.mesh_data['normals'] = self.mesh_data['normals'][mask]
        
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
        print("已清除所有选择") 