# 足球网格生成功能指南

## 概述

足球网格生成功能是CFD网格处理工具中的一个重要组件，它能够生成具有足球特征的球形网格。这种网格基于二十面体，通过细分算法生成，最终形成类似足球图案的球形网格结构。

## 技术原理

足球网格的生成原理如下：

1. **创建基础二十面体**：使用12个顶点和20个三角形面构建基础网格
2. **网格细分**：将每个三角形面分成四个小三角形
3. **顶点归一化**：将所有顶点投影到球面上
4. **缩放到指定半径**：按照用户指定的半径缩放网格

## 功能特点

- 支持参数化定制，可指定球体半径和细分层级
- 生成均匀分布的三角形网格
- 自动计算顶点法向量
- 支持导出为STL格式文件

## 使用方法

### 基本用法

```python
from src.create_football_mesh import create_football_mesh, save_to_stl

# 生成足球网格
vertices, faces, normals = create_football_mesh(radius=100.0, subdivisions=3)

# 保存为STL文件
output_file = 'data/football.stl'
save_to_stl(output_file, vertices, faces, normals)
```

### 参数说明

- **radius**：球体半径，默认为100.0
- **subdivisions**：细分次数，默认为2
  - 细分次数为1时：顶点数=42，面片数=80
  - 细分次数为2时：顶点数=162，面片数=320
  - 细分次数为3时：顶点数=642，面片数=1280
  - 细分次数为4时：顶点数=2562，面片数=5120

### 性能考量

随着细分次数的增加，顶点和面的数量会以四倍的速度增长。推荐的细分次数范围是2-4，这能够在网格精度和计算效率之间取得良好的平衡。

对于大型网格（细分次数≥5），需要注意内存使用量和处理时间可能会显著增加。

## 可视化示例

足球网格生成后可以使用`MeshViewerQt`进行可视化：

```python
from src.create_football_mesh import create_football_mesh
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

## 应用场景

- 标准测试案例的网格生成
- CFD算法验证
- 网格处理算法的基准测试
- 教学和演示用途

## 未来改进计划

- 添加更多几何参数控制（如六边形和五边形的大小比例）
- 支持纹理坐标生成
- 提高大型网格的生成效率
- 添加更多标准几何体的生成支持 