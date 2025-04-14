import numpy as np
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import struct
import time
import os

# Assuming the compiled module is in the CFD directory
try:
    from CFD import mesh_reader_cpp
except ImportError:
    print("Error: Could not import the compiled mesh_reader_cpp module.")
    print("Ensure 'mesh_reader_cpp.cp310-win_amd64.pyd' is inside the 'CFD' directory.")
    exit(1)

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
            
        i = 0
        while i < len(lines):
            line_content = lines[i].strip()
            
            # 标准 GRID 格式
            if line_content.startswith('GRID') and not line_content.startswith('GRID*'):
                try:
                    parts = line_content.split()
                    if len(parts) < 6:
                        i += 1
                        continue
                    node_id = int(parts[1])
                    x_idx, y_idx, z_idx = 3, 4, 5 
                    x = float(parts[x_idx]) 
                    y = float(parts[y_idx])
                    z = float(parts[z_idx])
                    nodes[node_id] = [x, y, z]
                except (IndexError, ValueError) as e:
                    i += 1
                    continue # Skip problematic line
            
            # GRID* 格式 (两行表示一个节点)
            elif line_content.startswith('GRID*'):
                try:
                    if i + 1 < len(lines):  # 确保有下一行
                        parts1 = line_content.split()
                        next_line = lines[i+1].strip()
                        
                        if next_line.startswith('*'):  # 确认第二行以 * 开头
                            parts2 = next_line.split()
                            
                            if len(parts1) < 5 or len(parts2) < 2:
                                i += 2  # 跳过这两行
                                continue
                                
                            node_id = int(parts1[1])
                            x = float(parts1[3])
                            y = float(parts1[4])
                            z = float(parts2[1])
                            
                            nodes[node_id] = [x, y, z]
                            i += 2  # 处理完这两行后，增加两次索引
                            continue
                except (IndexError, ValueError) as e:
                    i += 2  # 处理出错，跳过这两行
                    continue
                
            elif line_content.startswith('CTETRA') or line_content.startswith('CHEXA'):
                try:
                    parts = line_content.split()
                    if len(parts) < 4:
                         i += 1
                         continue
                    element_type = parts[0]
                    element_nodes = [int(x) for x in parts[3:]]
                    if not element_nodes:
                        i += 1
                        continue
                    elements.append(element_nodes)
                    element_types.append(element_type)
                except (IndexError, ValueError) as e:
                     i += 1
                     continue # Skip problematic line
            
            # 如果没有任何条件匹配，增加索引继续处理下一行
            i += 1
        
        # 转换为numpy数组并确保节点ID连续
        if not nodes:
            return {'nodes': np.array([]), 'elements': np.array([]), 'element_types': []}
            
        node_ids = sorted(nodes.keys())
        id_map = {old_id: new_id for new_id, old_id in enumerate(node_ids)}
        nodes_array = np.array([nodes[nid] for nid in node_ids])
        
        # 重新映射单元中的节点ID
        elements_array = []
        valid_element_types = [] # Keep track of types for valid elements
        for i, element in enumerate(elements):
            try:
                mapped_element = [id_map[nid] for nid in element]
                elements_array.append(mapped_element)
                valid_element_types.append(element_types[i]) # Add type if element is valid
            except KeyError as e:
                pass # Skip element

        # Convert potentially jagged list to object array if elements have different node counts
        try:
            final_elements_array = np.array(elements_array)
        except ValueError:
            final_elements_array = np.array(elements_array, dtype=object)

        return {
            'nodes': nodes_array,
            'elements': final_elements_array,
            'element_types': valid_element_types # Return types corresponding to valid elements
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

def load_and_time_mesh(filepath):
    """
    Loads the mesh file using the C++ module and measures the time taken.

    Args:
        filepath (str): The path to the .nas file.

    Returns:
        The result from the load_mesh function (if any), or None if loading fails.
    """
    if not os.path.exists(filepath):
        print(f"Error: Mesh file not found at '{filepath}'")
        return None

    print(f"Attempting to load mesh file: {filepath}")
    start_time = time.perf_counter()

    try:
        # Call the correct function exposed by the C++ module
        mesh_data = mesh_reader_cpp.read_nas_file(filepath)
        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"Successfully loaded mesh in {duration:.4f} seconds.")
        # Depending on what load_mesh returns, you might want to use mesh_data
        # print(f"Loaded mesh data: {mesh_data}") # Example
        return mesh_data
    except AttributeError:
        # Update the error message to reflect the function we tried
        print("Error: The 'mesh_reader_cpp' module does not have a 'read_nas_file' function.")
        print("Please check the available functions in the C++ module (src/mesh_reader_py.cpp).")
        return None
    except Exception as e:
        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"Error loading mesh after {duration:.4f} seconds: {e}")
        return None

if __name__ == "__main__":
    # Define the path to the LARGE mesh file
    mesh_file_path = os.path.join("src", "data", "large_star.nas")

    print(f"--- Loading LARGE file: {mesh_file_path} ---")
    print("\n--- Loading with C++ Module ---")
    load_and_time_mesh(mesh_file_path)

    print("\n--- Loading with Python Module ---")
    if not os.path.exists(mesh_file_path):
        print(f"Error: Mesh file not found at '{mesh_file_path}'")
    else:
        print(f"Attempting to load mesh file: {mesh_file_path}")
        start_time_py = time.perf_counter()
        try:
            # Use the pure Python reader
            py_reader = create_mesh_reader(mesh_file_path)
            mesh_data_py = py_reader.read(mesh_file_path)
            end_time_py = time.perf_counter()
            duration_py = end_time_py - start_time_py
            print(f"Successfully loaded mesh in {duration_py:.4f} seconds.")
            # You could optionally compare mesh_data_py with the C++ result
            # if mesh_data is not None:
            #     # Add comparison logic here if needed
            #     pass
        except Exception as e:
            end_time_py = time.perf_counter()
            duration_py = end_time_py - start_time_py
            print(f"Error loading mesh with Python module after {duration_py:.4f} seconds: {e}") 