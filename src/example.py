<<<<<<< HEAD
from mesh_reader import create_mesh_reader

# 创建读取器并读取文件
reader = create_mesh_reader("data/test_cube.stl")
mesh_data = reader.read("data/test_cube.stl")
=======
# 创建读取器并读取文件
reader = create_mesh_reader("example.stl")
mesh_data = reader.read("example.stl")
>>>>>>> 61808a0fd45044b397c6488dce73d9e755b79762

# 访问网格数据
vertices = mesh_data['vertices']
faces = mesh_data['faces']
normals = mesh_data['normals']

<<<<<<< HEAD
# 打印网格信息
print(f"加载STL文件: data/test_cube.stl")
print(f"顶点数量: {len(vertices)}")
print(f"面片数量: {len(faces)}")

# 验证网格数据
print("\n网格数据验证:")
print(f"顶点坐标范围:")
print(f"X: [{vertices[:, 0].min():.2f}, {vertices[:, 0].max():.2f}]")
print(f"Y: [{vertices[:, 1].min():.2f}, {vertices[:, 1].max():.2f}]")
print(f"Z: [{vertices[:, 2].min():.2f}, {vertices[:, 2].max():.2f}]")
=======
# 读取Nastran文件
nas_reader = create_mesh_reader("example.nas")
nas_data = nas_reader.read("example.nas")

# 访问Nastran数据
nodes = nas_data['nodes']
elements = nas_data['elements']
element_types = nas_data['element_types'] 
>>>>>>> 61808a0fd45044b397c6488dce73d9e755b79762
