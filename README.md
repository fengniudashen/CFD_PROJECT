# CFD网格处理工具

这是一个用于处理和可视化CFD（计算流体力学）网格的Python工具包。支持STL和NAS格式的网格文件读取、处理和可视化，并提供先进的网格质量评估和修复工具。

## 版本历史

### V0.0.4 (当前版本)
- 增加面质量分析器 (`face_quality_analyzer.py`) - 基于STAR-CCM+的质量评估算法
- 修复了`mesh_viewer_qt.py`中出现的重复if语句错误
- 优化了性能，改进了大型网格的处理速度
- 代码稳定性和用户界面改进

### V0.0.3
- 增加网格可视化界面
- 支持基本的网格编辑功能

## 功能特点

- 支持读取和保存STL、NAS格式的网格文件
- 提供网格数据的基本处理功能
- 包含3D网格可视化界面
- 支持创建标准几何体（如足球形状）的网格
- 网格质量分析，包括：
  - 面质量评估（skewness、面积比率等）
  - 交叉面检测
  - 相邻面检测
  - 重叠点和边检测
  - 自由边检测

## 安装说明

1. 克隆项目到本地：
```bash
git clone [你的仓库URL]
cd CFD_PROJECT
```

2. 创建并激活虚拟环境（推荐）：
```bash
python -m venv CFD
CFD\Scripts\activate  # Windows
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

## 目录结构

- `src/`: 源代码目录
  - `mesh_reader.py`: 网格文件读取模块
  - `mesh_viewer_qt.py`: 3D可视化界面模块
  - `create_football_mesh.py`: 足球网格生成模块
  - `face_quality_analyzer.py`: 面质量分析模块
- `data/`: 示例网格文件
- `tests/`: 测试文件

## 系统要求

- Python 3.7+
- PyQt5
- VTK 9.0+
- NumPy

## 贡献指南

欢迎提交问题和改进建议！如果你想贡献代码，请：

1. Fork 这个仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 许可证

这个项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情
