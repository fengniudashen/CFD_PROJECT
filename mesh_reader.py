import numpy as np
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import struct

class MeshReader(ABC):
    """抽象基类，定义网格读取器的接口"""
    
    @abstractmethod
    def read(self, file_path: str) -> Dict:
        """读取网格文件的抽象方法"""
        pass

class STLReader(MeshReader):
    """STL文件读取器"""
    
    def read(self, file_path: str) -> Dict:
        """
        读取STL文件
        Args:
            file_path: STL文件路径
        Returns:
            包含顶点和面的字典
            {
                'vertices': np.ndarray,  # 形状为(n, 3)的顶点数组
                'faces': np.ndarray,     # 形状为(m, 3)的面索引数组
                'normals': np.ndarray    # 形状为(m, 3)的法向量数组
            }
        """
        with open(file_path, 'rb') as f:
            header = f.read(80)
            if self._is_binary(header):
                return self._read_binary(file_path)
            else:
                return self._read_ascii(file_path)
    
    def _is_binary(self, header: bytes) -> bool:
        """判断是否为二进制STL文件"""
        try:
            header.decode('ascii')
            return False
        except UnicodeDecodeError:
            return True
    
    def _read_binary(self, file_path: str) -> Dict:
        vertices = []
        normals = []
        faces = []
        
        with open(file_path, 'rb') as f:
            f.seek(80)  # 跳过头部
            face_count = struct.unpack('I', f.read(4))[0]
            
            for _ in range(face_count):
                data = struct.unpack('f' * 12 + 'H', f.read(50))
                normal = data[0:3]
                v1 = data[3:6]
                v2 = data[6:9]
                v3 = data[9:12]
                
                normals.append(normal)
                vertices.extend([v1, v2, v3])
                faces.append([len(vertices)-3, len(vertices)-2, len(vertices)-1])
        
        return {
            'vertices': np.array(vertices),
            'faces': np.array(faces),
            'normals': np.array(normals)
        }
    
    def _read_ascii(self, file_path: str) -> Dict:
        vertices = []
        normals = []
        faces = []
        
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('facet normal'):
                normal = np.array([float(x) for x in line.split()[2:]])
                normals.append(normal)
                
                # 读取三个顶点
                for _ in range(3):
                    i += 1
                    vertex = np.array([float(x) for x in lines[i].strip().split()[1:]])
                    vertices.append(vertex)
                
                faces.append([len(vertices)-3, len(vertices)-2, len(vertices)-1])
                i += 3  # 跳过 endfacet
            i += 1
            
        return {
            'vertices': np.array(vertices),
            'faces': np.array(faces),
            'normals': np.array(normals)
        }

class NastranReader(MeshReader):
    """Nastran文件读取器"""
    
    def read(self, file_path: str) -> Dict:
        """
        读取Nastran文件
        Args:
            file_path: Nastran文件路径
        Returns:
            包含节点和单元的字典
            {
                'nodes': np.ndarray,     # 形状为(n, 3)的节点坐标数组
                'elements': np.ndarray,   # 形状为(m, k)的单元连接数组
                'element_types': List     # 单元类型列表
            }
        """
        nodes = {}
        elements = []
        element_types = []
        
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        for line in lines:
            if line.startswith('GRID'):
                # GRID格式: GRID    ID     CP      X       Y       Z
                parts = line[:-1].split()
                node_id = int(parts[1])
                x = float(parts[3])
                y = float(parts[4])
                z = float(parts[5])
                nodes[node_id] = [x, y, z]
                
            elif line.startswith('CTETRA') or line.startswith('CHEXA'):
                # 读取四面体或六面体单元
                parts = line[:-1].split()
                element_type = parts[0]
                element_nodes = [int(x) for x in parts[3:]]
                elements.append(element_nodes)
                element_types.append(element_type)
        
        # 转换为numpy数组并确保节点ID连续
        node_ids = sorted(nodes.keys())
        id_map = {old_id: new_id for new_id, old_id in enumerate(node_ids)}
        nodes_array = np.array([nodes[nid] for nid in node_ids])
        
        # 重新映射单元中的节点ID
        elements_array = [[id_map[nid] for nid in element] for element in elements]
        
        return {
            'nodes': nodes_array,
            'elements': np.array(elements_array),
            'element_types': element_types
        }

def create_mesh_reader(file_path: str) -> MeshReader:
    """
    工厂方法，根据文件扩展名创建相应的读取器
    """
    ext = Path(file_path).suffix.lower()
    if ext == '.stl':
        return STLReader()
    elif ext == '.nas':
        return NastranReader()
    else:
        raise ValueError(f"Unsupported file format: {ext}") 