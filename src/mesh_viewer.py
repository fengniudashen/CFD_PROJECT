import pyvista as pv
import numpy as np
from typing import Dict
import os

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
        
    def read_nas_file(self, file_path: str) -> Dict:
        """
        高效读取NAS文件
        
        Args:
            file_path: NAS文件路径
            
        Returns:
            包含nodes, elements和element_types的字典
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        nodes = {}  # 使用字典存储节点ID到坐标的映射，提高查找效率
        elements = []
        element_types = []
        
        # 使用带缓冲的读取和更高效的字符串处理
        with open(file_path, 'r') as f:
            # 一次读取大块数据，减少I/O操作
            buffer_size = 8192 * 1024  # 8MB缓冲区
            
            # 处理可能跨行的节点数据
            continued_line = None
            
            while True:
                chunk = f.read(buffer_size)
                if not chunk:
                    break
                    
                lines = chunk.splitlines()
                
                # 处理上一个chunk可能被截断的情况
                if continued_line:
                    lines[0] = continued_line + lines[0]
                    continued_line = None
                
                i = 0
                while i < len(lines):
                    line = lines[i]
                    
                    # 处理GRID节点
                    if line.startswith('GRID'):
                        # 处理标准GRID格式
                        if line.startswith('GRID '):
                            parts = line.split()
                            if len(parts) >= 6:
                                node_id = int(parts[1])
                                # 高效解析浮点数
                                try:
                                    x = float(parts[3])
                                    y = float(parts[4])
                                    z = float(parts[5])
                                    nodes[node_id] = [x, y, z]
                                except (ValueError, IndexError):
                                    pass
                        
                        # 处理GRID*格式（长格式，可能跨行）
                        elif line.startswith('GRID*'):
                            if i + 1 < len(lines):  # 确保有下一行
                                parts1 = line.split()
                                next_line = lines[i+1]
                                
                                if next_line.startswith('*'):
                                    parts2 = next_line.split()
                                    
                                    try:
                                        node_id = int(parts1[1])
                                        x = float(parts1[3])
                                        y = float(parts1[4])
                                        z = float(parts2[1])
                                        nodes[node_id] = [x, y, z]
                                    except (ValueError, IndexError):
                                        pass
                                    
                                    i += 1  # 跳过已处理的下一行
                            else:
                                # 当前行是chunk的最后一行，需要与下一个chunk的第一行合并
                                continued_line = line
                    
                    # 处理CTRIA3三角形单元
                    elif line.startswith('CTRIA3'):
                        parts = line.split()
                        if len(parts) >= 6:
                            try:
                                # 提取三个节点ID
                                n1 = int(parts[3])
                                n2 = int(parts[4])
                                n3 = int(parts[5])
                                elements.append([n1, n2, n3])
                                element_types.append('CTRIA3')
                            except (ValueError, IndexError):
                                pass
                    
                    # 处理CHEXA六面体单元（可能跨行）
                    elif line.startswith('CHEXA'):
                        parts = line.split()
                        if len(parts) >= 6:
                            hexa_nodes = []
                            
                            # 添加第一行中的节点
                            for j in range(3, min(len(parts), 9)):
                                try:
                                    hexa_nodes.append(int(parts[j]))
                                except (ValueError, IndexError):
                                    pass
                            
                            # 如果需要处理续行（以+开头）
                            if i + 1 < len(lines) and lines[i+1].startswith('+'):
                                next_line = lines[i+1]
                                next_parts = next_line.split()
                                
                                # 从第2列开始添加剩余节点
                                for j in range(1, len(next_parts)):
                                    try:
                                        hexa_nodes.append(int(next_parts[j]))
                                    except (ValueError, IndexError):
                                        pass
                                
                                i += 1  # 跳过已处理的续行
                            
                            if hexa_nodes:
                                elements.append(hexa_nodes)
                                element_types.append('CHEXA')
                    
                    i += 1
        
        # 转换为numpy数组并重新映射节点索引
        node_list = []
        node_ids = sorted(nodes.keys())
        id_map = {old_id: i for i, old_id in enumerate(node_ids)}
        
        for node_id in node_ids:
            node_list.append(nodes[node_id])
        
        # 使用向量化操作转换单元中的节点索引
        remapped_elements = []
        for element in elements:
            remapped = [id_map.get(node_id, 0) for node_id in element]
            remapped_elements.append(remapped)
        
        return {
            'nodes': np.array(node_list),
            'elements': np.array(remapped_elements),
            'element_types': element_types
        }
    
    def view_nas_from_file(self, file_path: str):
        """
        从NAS文件直接读取并显示网格
        
        Args:
            file_path: NAS文件路径
        """
        # 读取NAS文件
        mesh_data = self.read_nas_file(file_path)
        
        # 显示网格
        self.view_nas(mesh_data)
        
    def view_triangular_nas(self, mesh_data: Dict):
        """
        显示带有三角形面片的Nastran网格
        
        Args:
            mesh_data: 包含nodes, elements和element_types的字典
        """
        # 创建单元到顶点的连接
        cells = []
        cell_types = []
        
        for i, element in enumerate(mesh_data['elements']):
            element_type = mesh_data['element_types'][i] if i < len(mesh_data['element_types']) else None
            
            if element_type == 'CTRIA3':
                # 三角形单元
                if len(element) >= 3:
                    cells.append(3)  # 3个节点的三角形
                    cells.extend(element[:3])  # 添加三个节点索引
                    cell_types.append(pv.CellType.TRIANGLE)
            elif element_type == 'CHEXA':
                # 六面体单元
                if len(element) >= 8:
                    cells.append(8)  # 8个节点的六面体
                    cells.extend(element[:8])  # 添加8个节点索引
                    cell_types.append(pv.CellType.HEXAHEDRON)
        
        if cells:
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
        else:
            print("错误: 无法从网格数据中找到有效的单元")
    
    def view_triangular_nas_from_file(self, file_path: str):
        """
        从NAS文件直接读取并显示三角形网格
        
        Args:
            file_path: NAS文件路径
        """
        # 读取NAS文件
        mesh_data = self.read_nas_file(file_path)
        
        # 显示三角形网格
        self.view_triangular_nas(mesh_data) 