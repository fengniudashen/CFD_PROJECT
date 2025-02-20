import pyvista as pv
import numpy as np
from typing import Dict

class MeshViewer:
    def __init__(self):
        """初始化网格查看器"""
        self.plotter = pv.Plotter()
        
    def view_stl(self, mesh_data: Dict):
        """
        显示STL网格
        Args:
            mesh_data: 包含vertices和faces的字典
        """
        # 创建PyVista网格对象
        mesh = pv.PolyData(
            mesh_data['vertices'],
            np.hstack([np.full((len(mesh_data['faces']), 1), 3),
                      mesh_data['faces']]).astype(np.int32)
        )
        
        # 添加网格到场景
        self.plotter.add_mesh(mesh,
                            show_edges=True,
                            line_width=1,
                            color='white',
                            edge_color='black')
        
        # 设置视图
        self.plotter.set_background('white')
        self.plotter.add_axes()
        self.plotter.camera_position = 'iso'
        
        # 显示网格
        self.plotter.show()
        
    def view_nas(self, mesh_data: Dict):
        """
        显示Nastran网格
        Args:
            mesh_data: 包含nodes和elements的字典
        """
        # 创建单元到顶点的连接
        cells = []
        cell_types = []
        
        for i, element in enumerate(mesh_data['elements']):
            if mesh_data['element_types'][i] == 'CHEXA':
                # 六面体单元
                cells.append(len(element))  # 节点数
                cells.extend(element)  # 节点索引
                cell_types.append(pv.CellType.HEXAHEDRON)
                
        # 创建PyVista非结构化网格
        grid = pv.UnstructuredGrid({
            'cells': cells,
            'cell_types': cell_types,
            'points': mesh_data['nodes']
        })
        
        # 添加网格到场景
        self.plotter.add_mesh(grid,
                            show_edges=True,
                            line_width=1,
                            color='white',
                            edge_color='black')
        
        # 设置视图
        self.plotter.set_background('white')
        self.plotter.add_axes()
        self.plotter.camera_position = 'iso'
        
        # 显示网格
        self.plotter.show() 