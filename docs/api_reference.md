# API参考文档 (V0.1.2)

*更新日期: 2024-07-27*

本文档提供了CFD网格处理工具V0.1.2版本中核心类和函数的说明和使用方法。

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

## 算法模块 (src/algorithms/)

### `CombinedIntersectionAlgorithm` 类 (combined_intersection_algorithm.py)

组合的网格相交检测算法类，目前专注于穿刺面检测。

**构造函数**：
```python
CombinedIntersectionAlgorithm(mesh_data=None, detection_mode="pierced")
```

**主要方法**：

#### `execute(parent=None, threshold=None)`
执行网格相交检测，根据 `detection_mode` 调用相应方法。

#### `detect_pierced_faces(parent=None)`
检测穿刺面，会尝试使用 C++ 加速（如果可用），否则回退到 Python 实现。支持通过 `parent` 参数显示进度对话框。

### `AdjacentFacesAlgorithm` 类 (adjacent_faces_detector.py / adjacent_faces_detector.cpp)

检测相邻面片的算法。

**构造函数**：
```python
AdjacentFacesAlgorithm(mesh_data=None, threshold=0.1)
```

**主要方法**：

#### `execute(parent=None, threshold=None)`
执行相邻面检测。C++ 版本使用 Proximity 公式。

*(其他算法类如 FreeEdgesAlgorithm, OverlappingEdgesAlgorithm, FaceQualityAlgorithm, MergedVertexDetectionAlgorithm 可类似添加)*

## 网格可视化模块 (mesh_viewer_qt.py)

### `MeshViewerQt`类

基于PyQt5和VTK的3D网格可视化界面。

**构造函数**：
```python
MeshViewerQt(mesh_data: Dict)
```

**参数**：
- `mesh_data (dict)`：包含以下键的字典：
  - `vertices (np.ndarray)`：顶点坐标数组
  - `faces (np.ndarray)`：面片索引数组
  - `normals (np.ndarray, 可选)`：顶点法向量数组

**主要方法 (部分)**：

#### `show()`
显示可视化窗口。

#### `load_mesh(mesh_data)`
加载新的网格数据。

#### `update_display()`
根据当前的网格数据和选择状态更新 VTK 显示。

#### `clear_all_selections()`
清除所有当前的选择（点、边、面）。

#### **选择操作 (通过 UI 按钮触发)**:
*   `on_pick(obj, event)`: 处理鼠标点击拾取事件，根据当前激活的选择模式（点/边/面）更新选择集。
*   `select_free_edges()`: 检测并高亮显示自由边。
*   `select_overlapping_edges()`: 检测并高亮显示重叠边。
*   `select_overlapping_points()`: 检测并高亮显示重叠点。
*   `detect_face_intersections()`: 检测并高亮显示相交面（穿刺面）。
*   `analyze_face_quality()`: 分析并根据阈值高亮显示低质量面。
*   `select_adjacent_faces()`: 分析并根据阈值高亮显示相邻过近的面。

#### **编辑操作 (通过 UI 按钮触发)**:
*   `create_point()`: 通过输入的 X, Y, Z 坐标创建新顶点。
*   `create_face()`: 从当前选中的3个顶点创建新面片。
*   `delete_selected_faces()`: 删除当前选中的面片。
*   `collapse_selected_vertices()`: 将选中的顶点（或选中边的端点）合并到它们的质心。
*   `start_interactive_face_creation(checked)`: 启动或停止交互式面片创建模式。
*   `finalize_interactive_face_creation()`: 完成交互式面片创建。
*   `split_selected_elements()`: (占位符) 分割选中的边或面。
*   `swap_selected_edge()`: (占位符) 交换选中的边。

#### **内部 UI 控制方法**:
*   `_toggle_create_point_options()`: 切换"创建点"的二级选项（"从三坐标创建点"按钮和输入框容器）的可见性。
*   `_toggle_xyz_input_ui()`: 切换 XYZ 坐标输入框和"创建"按钮的可见性。

#### **其他常用方法**:
*   `reset_camera()`: 重置相机视图。
*   `set_standard_view(view_type)`: 设置标准视图 (front, back, top, bottom, left, right, isometric)。

### `check_triangle_intersection(tri1_verts, tri2_verts)` 
*(该方法似乎已移至 AlgorithmUtils 或不再直接暴露在 MeshViewerQt 中，建议确认)*

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