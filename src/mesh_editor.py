import numpy as np
import pyvista as pv
from typing import Dict, List, Tuple

class MeshEditor:
    def __init__(self, mesh_data: Dict):
        """
        初始化网格编辑器
        Args:
            mesh_data: 包含网格数据的字典
        """
        self.mesh_data = mesh_data.copy()  # 创建副本以保护原始数据
        # 创建一个带有工具栏的plotter
        self.plotter = pv.Plotter(notebook=False)
        self.selected_faces = []  # 存储选中的面
        self.temp_points = []  # 临时存储用于创建新面的点
        self.mesh = None
        self.picking_mode = 'face'  # 'face' 或 'point'
        
    def run(self):
        """运行交互式编辑器"""
        # 创建初始网格
        self.mesh = pv.PolyData(
            self.mesh_data['vertices'],
            np.hstack([np.full((len(self.mesh_data['faces']), 1), 3),
                      self.mesh_data['faces']]).astype(np.int32)
        )
        
        # 添加键盘事件
        self.plotter.add_key_event('m', self._toggle_mode)  # 切换模式
        self.plotter.add_key_event('d', self._delete_selected_faces)  # 删除面
        self.plotter.add_key_event('f', self._create_face)  # 创建面
        self.plotter.add_key_event('c', self._clear_selection)  # 清除选择
        
        # 启用单元选择
        self.plotter.enable_cell_picking(
            callback=self._cell_picked,
            through=False,
            show=True,
            show_message=True,
            style='wireframe',
            color='red'
        )
        
        # 添加操作说明文本
        self._add_instruction_text()
        
        # 初始显示
        self._update_display()
        
        # 启动交互
        self.plotter.show()
    
    def _add_instruction_text(self):
        """添加操作说明文本"""
        instructions = [
            "操作说明:",
            "m: 切换模式 (当前: 面选择)",
            "d: 删除选中的面",
            "f: 创建新面",
            "c: 清除选择",
            "左键: 选择面/点",
            "右键: 旋转视图",
            "中键: 平移视图",
            "滚轮: 缩放视图"
        ]
        
        y_position = 0.95
        for instruction in instructions:
            self.plotter.add_text(
                instruction,
                position=(0.02, y_position),
                font_size=12,
                color='black',
                shadow=True
            )
            y_position -= 0.05
    
    def _toggle_mode(self):
        """切换选择模式"""
        self.picking_mode = 'point' if self.picking_mode == 'face' else 'face'
        self._clear_selection()
        print(f"切换到{self.picking_mode}选择模式")
        self._update_display()
    
    def _cell_picked(self, cell_id):
        """处理单元选择事件"""
        if self.picking_mode == 'face':
            if cell_id not in self.selected_faces:
                self.selected_faces.append(cell_id)
                print(f"选中面 {cell_id}")
        else:  # point mode
            if len(self.temp_points) < 3:
                face = self.mesh_data['faces'][cell_id]
                center = np.mean(self.mesh_data['vertices'][face], axis=0)
                self.temp_points.append(center)
                print(f"选中点 {len(self.temp_points)}/3")
        
        self._update_display()
    
    def _update_display(self):
        """更新显示"""
        # 清除现有网格
        self.plotter.clear_actors()
        
        # 显示基础网格
        self.plotter.add_mesh(
            self.mesh,
            show_edges=True,
            line_width=1,
            color='lightgray',
            edge_color='black'
        )
        
        # 显示选中的面
        if self.selected_faces:
            selected_mesh = self.mesh.extract_cells(self.selected_faces)
            self.plotter.add_mesh(
                selected_mesh,
                color='red',
                opacity=0.7,
                show_edges=True
            )
        
        # 显示选中的点
        if self.temp_points:
            points = pv.PolyData(np.array(self.temp_points))
            self.plotter.add_mesh(
                points,
                color='blue',
                point_size=20,
                render_points_as_spheres=True
            )
        
        # 添加模式显示
        self.plotter.add_text(
            f"当前模式: {'点' if self.picking_mode == 'point' else '面'}选择",
            position=(0.02, 0.02),
            font_size=14,
            color='black',
            shadow=True
        )
        
        # 重新添加说明文本
        self._add_instruction_text()
        
        # 更新显示
        self.plotter.render()
    
    def _delete_selected_faces(self):
        """删除选中的面"""
        if not self.selected_faces:
            print("没有选中的面可删除")
            return
            
        mask = np.ones(len(self.mesh_data['faces']), dtype=bool)
        mask[self.selected_faces] = False
        
        self.mesh_data['faces'] = self.mesh_data['faces'][mask]
        if 'normals' in self.mesh_data:
            self.mesh_data['normals'] = self.mesh_data['normals'][mask]
        
        self.mesh = pv.PolyData(
            self.mesh_data['vertices'],
            np.hstack([np.full((len(self.mesh_data['faces']), 1), 3),
                      self.mesh_data['faces']]).astype(np.int32)
        )
        
        self.selected_faces = []
        print("已删除选中的面")
        self._update_display()
    
    def _create_face(self):
        """从三个点创建新面"""
        if len(self.temp_points) != 3:
            print("需要选择3个点才能创建面")
            return
        
        new_face = []
        for point in self.temp_points:
            distances = np.linalg.norm(self.mesh_data['vertices'] - point, axis=1)
            nearest_idx = np.argmin(distances)
            new_face.append(nearest_idx)
        
        self.mesh_data['faces'] = np.vstack([self.mesh_data['faces'], new_face])
        
        if 'normals' in self.mesh_data:
            v1 = self.mesh_data['vertices'][new_face[1]] - self.mesh_data['vertices'][new_face[0]]
            v2 = self.mesh_data['vertices'][new_face[2]] - self.mesh_data['vertices'][new_face[0]]
            normal = np.cross(v1, v2)
            normal = normal / np.linalg.norm(normal)
            self.mesh_data['normals'] = np.vstack([self.mesh_data['normals'], normal])
        
        self.mesh = pv.PolyData(
            self.mesh_data['vertices'],
            np.hstack([np.full((len(self.mesh_data['faces']), 1), 3),
                      self.mesh_data['faces']]).astype(np.int32)
        )
        
        self.temp_points = []
        print("已创建新面")
        self._update_display()
    
    def _clear_selection(self):
        """清除所有选择"""
        self.selected_faces = []
        self.temp_points = []
        print("已清除选择")
        self._update_display() 