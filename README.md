# CFD网格处理工具

这是一个用于处理和可视化CFD（计算流体力学）网格的Python工具包。支持STL和NAS格式的网格文件读取、处理和可视化，并提供先进的网格质量评估和修复工具。该项目包含高性能C++库，可显著提升大型网格处理速度。

## 版本历史

### C0.0.2 (开发中)

* 添加了高性能C++实现的自由边检测库（free_edges_cpp）
* 更新了mesh_reader库的C++实现，提高大型网格文件的读取性能
* 优化了网格处理性能，支持超过100万面的大型模型
* 完善了C++库文档和构建指南
* [查看C++库文档](CPP_LIBRARIES.md)

### C0.0.1 (当前开发版本)

* 添加了足球网格生成和可视化功能示例
* 优化了网格数据验证流程
* 增强了STL文件的导入/导出功能
* 改进了网格信息统计功能
* 增加了基本的3D可视化界面

### V0.0.8 (最新稳定版本)

* 集成高性能C++穿刺面检测算法，性能提升约1000倍
* 优化了大型网格处理流程，支持高效处理百万级面片模型
* 添加了算法性能对比工具，进行Python和C++实现对比
* 增加了示例脚本，便于用户理解算法性能差异
* 修复了NAS文件生成器中的索引错误问题
* 改进了网格组件的鲁棒性和容错处理能力
* 优化了内存管理，显著降低了大型模型的内存占用

### V0.0.7 (稳定版本)

* 优化了生成大型NAS文件的功能，支持处理超过100万个节点的模型
* 修复了三角剖分阶段的索引错误问题
* 改进了多线程性能，提高大型模型处理效率
* 添加了高性能点云处理功能
* 增强了内存管理，减少大型模型处理的内存占用
* 优化了用户界面响应速度

### V0.0.6 (稳定版本)

* 添加了右侧按钮数字标签功能，显示检测到的问题数量
* 实现了数字标签根据数字位数自动调整字体大小的功能（1-7位数字）
* 实现了分析结果持久化，数字标签在模型变更前保持检测结果
* 优化了按钮布局，确保UI元素对齐统一
* 添加了数字标签的"未分析"状态指示
* 优化了性能，提高了大型网格的处理速度
* 修复了部分UI元素缩进和布局问题

### V0.0.5

* 添加了渲染窗口顶部的27个按钮，呈水平排列，靠右对齐
* 添加了渲染窗口左侧的9个垂直排列按钮
* 改进了按钮1的重置视图功能，添加了四向箭头图标
* 为按钮2添加了相机图标和下拉菜单，包含视图存储和恢复功能
* 添加了标准视图切换功能（前、后、左、右、顶、底、等轴测视图）
* 添加了投影模式切换功能（透视投影和平行投影）
* 优化了用户界面布局和交互体验

### V0.0.4

* 增加面质量分析器 (`face_quality_analyzer.py`) - 基于STAR-CCM+的质量评估算法
* 修复了`mesh_viewer_qt.py`中出现的重复if语句错误
* 优化了性能，改进了大型网格的处理速度
* 代码稳定性和用户界面改进

### V0.0.3

* 增加网格可视化界面
* 支持基本的网格编辑功能

## 功能特点

* 支持读取和保存STL、NAS格式的网格文件
* 提供网格数据的基本处理功能
* 包含3D网格可视化界面
* 支持创建标准几何体（如足球形状）的网格
* 网格质量分析，包括：  
   * 面质量评估（skewness、面积比率等）  
   * 交叉面检测（带有数量显示）  
   * 相邻面检测（带有数量显示）  
   * 重叠点和边检测（带有数量显示）  
   * 自由边检测（带有数量显示）
* 视图控制和导航功能：
   * 标准视图切换（前、后、左、右、顶、底、等轴测）
   * 投影模式切换（透视/平行）
   * 视图存储和恢复
* 高级用户界面功能：
   * 自适应数字标签显示
   * 分析结果持久化
   * 智能按钮布局和对齐

## 安装说明

1. 克隆项目到本地：
```bash
git clone https://github.com/fengniudashen/CFD_PROJECT.git
cd CFD_PROJECT
```

2. 创建并激活虚拟环境（推荐）：
```bash
python -m venv CFD
CFD\Scripts\activate  # Windows
source CFD/bin/activate  # Linux/macOS
```

3. 安装依赖包：
```bash
pip install -r requirements.txt
```

## 使用示例

### 1. 读取STL文件
```python
from src.mesh_reader import create_mesh_reader

reader = create_mesh_reader("data/test_cube.stl")
mesh_data = reader.read("data/test_cube.stl")
```

### 2. 创建足球网格并可视化
```python
from src.create_football_mesh import create_football_mesh, save_to_stl
from src.mesh_viewer_qt import MeshViewerQt
from PyQt5.QtWidgets import QApplication
import sys

# 生成足球网格
vertices, faces, normals = create_football_mesh(radius=100.0, subdivisions=3)

# 显示网格
app = QApplication(sys.argv)
viewer = MeshViewerQt({
    'vertices': vertices,
    'faces': faces,
    'normals': normals
})
viewer.show()
sys.exit(app.exec_())
```

### 3. 面质量分析
```python
from src.face_quality_analyzer import analyze_face_quality, generate_quality_report
import numpy as np

# 准备顶点和面数据
vertices = np.array([...])  # 顶点坐标
faces = np.array([...])     # 面索引

# 分析面质量
results = analyze_face_quality(vertices, faces, threshold=0.5)

# 获取质量报告
report = generate_quality_report(results['stats'])
print(report)
```

### 4. 使用网格分析工具
```python
# 启动主界面
from src.example_football import main
main()

# 在界面中，点击右侧按钮可执行不同的分析：
# - 交叉面按钮：检测并显示模型中的交叉面数量
# - 面质量按钮：分析面质量问题并显示结果
# - 自由边按钮：检测自由边并显示数量
# 数字标签会显示检测到的问题数量
```

## 目录结构

- `src/`: 源代码目录
  - `mesh_reader.py`: 网格文件读取模块
  - `mesh_reader.cpp/hpp`: C++实现的高性能网格读取库
  - `mesh_viewer_qt.py`: 3D可视化界面模块
  - `mesh_viewer_qt_cpp.py`: 集成C++库的高性能可视化界面
  - `create_football_mesh.py`: 足球网格生成模块
  - `face_quality_analyzer.py`: 面质量分析模块
  - `face_proximity_analyzer.py`: 面片邻近分析模块
  - `high_performance_proximity.py`: 高性能邻近检测模块
  - `free_edges_detector.cpp`: C++实现的自由边检测库
  - `setup.py`: C++库构建脚本
  - `compare_free_edges.py`: C++与Python性能对比工具
  - `icons/`: 界面图标资源目录
- `docs/`: 文档目录
  - `free_edges_cpp.md`: 自由边检测库文档
  - `mesh_reader.md`: 网格读取库文档
  - `build_guide.md`: C++库构建指南
- `data/`: 示例网格文件
- `tests/`: 测试文件
- `CPP_LIBRARIES.md`: C++库总览文档
- `CFD/`: 虚拟环境目录（不包含在版本控制中）

## 系统要求

- Python 3.7+
- PyQt5 5.15+
- VTK 9.0+
- NumPy 1.20+
- SciPy 1.7+
- threadpoolctl 3.1+ (用于多线程控制)
- psutil 5.9+ (用于内存管理)

### C++库额外要求

- C++14兼容的编译器
- CMake 3.10+ (可选，用于高级构建)
- pybind11 (Python绑定)
- Eigen 3.3+ (矩阵运算)

## 高性能C++库

本项目包含多个高性能C++库，专为处理大型网格模型而设计：

### pierced_faces_cpp 穿刺面检测库

- 高效检测网格中的相互穿刺（相交）面片
- 比Python实现快约3倍
- 使用分离轴定理(SAT)和八叉树空间分区技术
- [查看详细文档](docs/pierced_faces_cpp.md)

```python
# 使用示例
import pierced_faces_cpp
pierced_faces, time = pierced_faces_cpp.detect_pierced_faces_with_timing(faces, vertices)
print(f"检测到{len(pierced_faces)}个穿刺面，用时{time:.4f}秒")
```

### free_edges_cpp 自由边检测库

- 高效检测网格中的自由边（仅与一个面相连的边）
- 比Python实现快约1.4倍
- 完全集成到网格查看器中
- [查看详细文档](docs/free_edges_cpp.md)

```python
# 使用示例
import free_edges_cpp
free_edges, time = free_edges_cpp.detect_free_edges_with_timing(faces)
print(f"检测到{len(free_edges)}条自由边，用时{time:.4f}秒")
```

### mesh_reader 网格读取库

- 支持NAS/Nastran和STL格式
- 高效内存管理，针对大型模型优化
- 两遍读取策略，预分配内存提高性能
- [查看详细文档](docs/mesh_reader.md)

## 构建C++库

请参阅[构建指南](docs/build_guide.md)获取详细的构建步骤。

## 贡献指南

欢迎提交问题和改进建议！详细贡献流程请参考[贡献指南](CONTRIBUTING.md)。

## 许可证

这个项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情
