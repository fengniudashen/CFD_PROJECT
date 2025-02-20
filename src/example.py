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