# CFD网格处理工具

这是一个用于处理和可视化CFD（计算流体力学）网格的Python工具包。支持STL和NAS格式的网格文件读取、处理和可视化，并提供先进的网格质量评估和修复工具。

## 版本历史

### C0.0.1 (当前开发版本)

* 添加了足球网格生成和可视化功能示例
* 优化了网格数据验证流程
* 增强了STL文件的导入/导出功能
* 改进了网格信息统计功能
* 增加了基本的3D可视化界面

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
  - `mesh_viewer_qt.py`: 3D可视化界面模块
  - `create_football_mesh.py`: 足球网格生成模块
  - `face_quality_analyzer.py`: 面质量分析模块
  - `face_proximity_analyzer.py`: 面片邻近分析模块
  - `high_performance_proximity.py`: 高性能邻近检测模块
  - `icons/`: 界面图标资源目录
- `data/`: 示例网格文件
- `tests/`: 测试文件
- `CFD/`: 虚拟环境目录（不包含在版本控制中）

## 系统要求

- Python 3.7+
- PyQt5 5.15+
- VTK 9.0+
- NumPy 1.20+
- SciPy 1.7+

## 贡献指南

欢迎提交问题和改进建议！详细贡献流程请参考[贡献指南](CONTRIBUTING.md)。

## 许可证

这个项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情
