# CFD网格处理工具文档中心

欢迎使用CFD网格处理工具文档中心。这里提供了项目的所有文档和指南，帮助您了解和使用本工具。

## 最新版本信息

- **稳定版本**：[V0.0.7](../CHANGELOG.md) - 2024-05-10发布
- **开发版本**：[C0.0.1](release_notes_C0.0.1.md) - 开发中

## C0.0.1版本文档

### 入门指南

- [项目概述](../README.md)：项目介绍和基本功能
- [开发路线图](roadmap.md)：项目规划和未来发展方向
- [发布说明](release_notes_C0.0.1.md)：C0.0.1版本新功能和更新

### 功能文档

- [足球网格生成指南](football_mesh_guide.md)：足球网格生成功能详细说明
- [API参考文档](api_reference.md)：核心函数和类的详细说明

### 开发者文档

- [贡献指南](../CONTRIBUTING.md)：如何参与项目贡献
- [许可证](../LICENSE)：项目许可证信息

## 示例

### 网格生成

```python
from src.create_football_mesh import create_football_mesh, save_to_stl

# 生成足球网格
vertices, faces, normals = create_football_mesh(radius=100.0, subdivisions=2)

# 保存为STL文件
save_to_stl('output.stl', vertices, faces, normals)
```

### 网格可视化

```python
from src.create_football_mesh import create_football_mesh
from src.mesh_viewer_qt import MeshViewerQt
from PyQt5.QtWidgets import QApplication
import sys

# 生成网格
vertices, faces, normals = create_football_mesh()

# 可视化
app = QApplication(sys.argv)
viewer = MeshViewerQt({
    'vertices': vertices,
    'faces': faces,
    'normals': normals
})
viewer.show()
sys.exit(app.exec_())
```

## 常见问题

1. **如何安装CFD网格处理工具？**
   
   请参考[README.md](../README.md)中的安装说明。

2. **支持哪些网格文件格式？**

   当前版本支持STL和NAS格式。

3. **如何报告问题或提出新功能请求？**

   请在GitHub上[创建Issue](https://github.com/fengniudashen/CFD_PROJECT/issues/new/choose)。

4. **如何参与项目开发？**

   请参考[贡献指南](../CONTRIBUTING.md)。

## 版本历史

- [C0.0.1](release_notes_C0.0.1.md)：当前开发分支版本
- [V0.0.7](../CHANGELOG.md)：当前稳定版本
- [V0.0.6](../CHANGELOG.md)：历史版本
- [更多版本](../CHANGELOG.md)：完整版本历史

## 联系方式

如有任何问题或建议，请通过GitHub Issues与我们联系。 