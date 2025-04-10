<<<<<<< HEAD
from src.mesh_reader import read_nas_file
import numpy as np

# 读取足球体网格文件
file_path = 'tests/football_mesh.nas'
mesh_data = read_nas_file(file_path)

# 获取网格数据
vertices = mesh_data['vertices']
faces = mesh_data['faces']

# 打印网格信息
print(f"加载网格文件: {file_path}")
print(f"顶点数量: {len(vertices)}")
print(f"面片数量: {len(faces)}")

# 验证网格数据
print("\n网格数据验证:")
print(f"顶点坐标范围:")
print(f"X: [{vertices[:, 0].min():.2f}, {vertices[:, 0].max():.2f}]")
print(f"Y: [{vertices[:, 1].min():.2f}, {vertices[:, 1].max():.2f}]")
print(f"Z: [{vertices[:, 2].min():.2f}, {vertices[:, 2].max():.2f}]")
=======
# 创建读取器并读取文件
reader = create_mesh_reader("example.stl")
mesh_data = reader.read("example.stl")

# 访问网格数据
vertices = mesh_data['vertices']
faces = mesh_data['faces']
normals = mesh_data['normals']

# 读取Nastran文件
nas_reader = create_mesh_reader("example.nas")
nas_data = nas_reader.read("example.nas")

# 访问Nastran数据
nodes = nas_data['nodes']
elements = nas_data['elements']
element_types = nas_data['element_types'] 
>>>>>>> 61808a0fd45044b397c6488dce73d9e755b79762
