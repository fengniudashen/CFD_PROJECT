# API参考文档 (C0.0.1)

本文档提供了CFD网格处理工具C0.0.1版本中核心函数的详细说明和使用方法。

## 网格生成模块 (create_football_mesh.py)

### `create_icosahedron()`

创建基础二十面体网格。

**返回值**：
- `Tuple[np.ndarray, np.ndarray]`：包含顶点坐标和面片索引的元组

**示例**：
```python
vertices, faces = create_icosahedron()
```

### `subdivide_mesh(vertices, faces)`

细分网格，将每个三角形分成四个小三角形。

**参数**：
- `vertices (np.ndarray)`：顶点坐标数组
- `faces (np.ndarray)`：面片索引数组

**返回值**：
- `Tuple[np.ndarray, np.ndarray]`：包含新的顶点坐标和面片索引的元组

**示例**：
```python
new_vertices, new_faces = subdivide_mesh(vertices, faces)
```

### `create_football_mesh(radius=100.0, subdivisions=2)`

创建足球形状的三角形网格。

**参数**：
- `radius (float)`：球体半径，默认为100.0
- `subdivisions (int)`：细分次数，默认为2

**返回值**：
- `Tuple[np.ndarray, np.ndarray, np.ndarray]`：包含顶点坐标、面片索引和顶点法向量的元组

**示例**：
```python
vertices, faces, normals = create_football_mesh(radius=100.0, subdivisions=3)
```

### `save_to_stl(filename, vertices, faces, normals)`

将网格保存为二进制STL文件。

**参数**：
- `filename (str)`：输出文件名
- `vertices (np.ndarray)`：顶点坐标数组
- `faces (np.ndarray)`：面片索引数组
- `normals (np.ndarray)`：顶点法向量数组

**示例**：
```python
save_to_stl('data/football.stl', vertices, faces, normals)
```

## 网格可视化模块 (mesh_viewer_qt.py)

### `MeshViewerQt`类

基于PyQt5和VTK的3D网格可视化界面。

**构造函数**：
```python
MeshViewerQt(mesh_data, parent=None)
```

**参数**：
- `mesh_data (dict)`：包含以下键的字典：
  - `vertices (np.ndarray)`：顶点坐标数组
  - `faces (np.ndarray)`：面片索引数组
  - `normals (np.ndarray, 可选)`：顶点法向量数组
- `parent (QWidget, 可选)`：父窗口

**主要方法**：

#### `show()`

显示可视化窗口。

**示例**：
```python
viewer = MeshViewerQt(mesh_data)
viewer.show()
```

#### `load_mesh(mesh_data)`

加载新的网格数据。

**参数**：
- `mesh_data (dict)`：包含vertices、faces和可选的normals的字典

**示例**：
```python
viewer.load_mesh({
    'vertices': new_vertices,
    'faces': new_faces
})
```

## 示例模块 (example_football.py)

### 足球网格示例

展示如何创建足球网格并进行可视化。

**主要功能**：
- 生成足球网格
- 保存为STL文件
- 显示网格信息
- 验证网格数据
- 可视化网格

**示例**：
```python
from src.example_football import main
main()
```

## 工具函数

### 坐标变换

```python
# 顶点归一化（投影到球面）
normalized_vertex = vertex / np.linalg.norm(vertex)

# 缩放顶点
scaled_vertex = normalized_vertex * radius
```

### 网格统计

```python
# 获取顶点数量
vertex_count = len(vertices)

# 获取面片数量
face_count = len(faces)

# 计算顶点坐标范围
x_range = [vertices[:, 0].min(), vertices[:, 0].max()]
y_range = [vertices[:, 1].min(), vertices[:, 1].max()]
z_range = [vertices[:, 2].min(), vertices[:, 2].max()]
```

## 扩展和自定义

### 创建自定义网格生成函数

可以参考`create_football_mesh`函数的结构创建自定义的网格生成函数：

```python
def create_custom_mesh(param1, param2, ...):
    # 1. 创建基础网格
    vertices, faces = create_base_mesh()
    
    # 2. 处理网格（细分、变形等）
    vertices, faces = process_mesh(vertices, faces)
    
    # 3. 计算法向量
    normals = compute_normals(vertices, faces)
    
    return vertices, faces, normals
```

### 自定义可视化

可以扩展`MeshViewerQt`类来添加自定义功能：

```python
class CustomMeshViewer(MeshViewerQt):
    def __init__(self, mesh_data, parent=None):
        super().__init__(mesh_data, parent)
        
        # 添加自定义UI元素
        self.add_custom_ui()
    
    def add_custom_ui(self):
        # 添加自定义按钮、菜单等
        pass
        
    def custom_function(self):
        # 实现自定义功能
        pass
```

## API使用最佳实践

1. 对于大型网格，建议逐步增加细分次数以避免内存问题
2. 在使用可视化界面前，先验证网格数据的合法性
3. 使用标准参数值进行初次测试，然后根据需要调整
4. 保存中间结果以避免重复计算 