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
            line = lines[i].strip().lower()
            
            if line.startswith('facet normal'):
                # 读取法向量
                try:
                    normal = np.array([float(x) for x in line.split()[2:5]])
                    normals.append(normal)
                    
                    # 跳过 outer loop 行
                    i += 2
                    
                    # 读取三个顶点
                    vertex_indices = []
                    for _ in range(3):
                        vertex_line = lines[i].strip().split()
                        if vertex_line[0].lower() == 'vertex':
                            vertex = np.array([float(x) for x in vertex_line[1:4]])
                            vertices.append(vertex)
                            vertex_indices.append(len(vertices) - 1)
                        i += 1
                    
                    faces.append(vertex_indices)
                    
                    # 跳过 endloop 和 endfacet
                    i += 2
                except (ValueError, IndexError) as e:
                    print(f"Warning: 跳过无效的面: {line}")
                    i += 1
            else:
                i += 1
            
        return {
            'vertices': np.array(vertices),
            'faces': np.array(faces),
            'normals': np.array(normals)
        }

class NASReader(MeshReader):
    """NAS文件读取器"""
    def read(self, file_path: str) -> Dict:
        vertices = []
        faces = []
        temp_vertices = {}  # 用于存储临时顶点数据
        
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # 处理GRID点
                if line.startswith('GRID*'):
                    # GRID* 格式的第一行
                    parts = line.split()
                    node_id = int(parts[1])
                    x = float(parts[3])
                    y = float(parts[4])
                    
                    # 读取下一行获取z坐标
                    i += 1
                    next_line = lines[i].strip()
                    z = float(next_line.split()[1])
                    
                    # 存储顶点
                    temp_vertices[node_id] = len(vertices)  # 记录节点ID到索引的映射
                    vertices.append([x, y, z])
                
                # 处理三角形面
                elif line.startswith('CTRIA3'):
                    parts = line.split()
                    # 获取三个顶点的节点ID并转换为索引
                    v1 = temp_vertices[int(parts[3])]
                    v2 = temp_vertices[int(parts[4])]
                    v3 = temp_vertices[int(parts[5])]
                    faces.append([v1, v2, v3])
                
                i += 1
        
        # 转换为numpy数组
        return {
            'vertices': np.array(vertices, dtype=np.float32),
            'faces': np.array(faces, dtype=np.int32)
        }

def create_mesh_reader(file_path: str) -> MeshReader:
    """创建适当的网格读取器"""
    if file_path.lower().endswith('.nas'):
        return NASReader()
    elif file_path.lower().endswith('.stl'):
        return STLReader()
    else:
        raise ValueError(f"不支持的文件格式: {file_path}")

def read_nas_file(file_path: str) -> Dict:
    """便捷函数用于读取NAS文件"""
    reader = NASReader()
    return reader.read(file_path) 