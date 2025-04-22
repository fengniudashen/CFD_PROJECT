# CFD_PROJECT V0.1.2 发行说明

## 主要更新内容

此版本主要聚焦于用户界面 (UI) 的改进和错误修复，提升了应用的易用性和稳定性。

### 新增功能与改进

*   **UI 功能增强**:
    *   在 "修复" 标签页添加了多个新的图标按钮，用于常见的网格编辑操作：
        *   合并选中顶点 (Collapse selected vertices): 支持合并选中的点或边的端点。
        *   分割选中边/面 (Split selected edges/faces): (功能待实现)
        *   交换选中边 (Swap selected edge): (功能待实现)
        *   交互式面片创建 (Fill polygonal patch): 启动交互式面片填充功能。
        *   AI 修复 (AI Repair): (占位符，功能待实现)
        *   删除选定面 (Delete selected faces): 添加了专门的图标按钮用于删除面。
    *   实现了层级式菜单用于 "创建点" 功能，点击主按钮后显示 "从三坐标创建点" 选项及 XYZ 输入框。
    *   为 "创建点" 的子菜单选项添加了视觉分组样式（淡蓝色背景和边框）。
*   **UI 布局与显示优化**:
    *   调整了 "修复" 标签页顶部图标按钮的大小 (调整为 45x45)，并更新了图标绘制逻辑以适应新尺寸。
    *   移除了 "修复" 标签页中与状态栏功能重复的 "清除选择" 按钮。

### 错误修复

*   修复了 `mesh_viewer_qt.py` 中因 `QPointF` 对象传递给需要 `QPoint` 的绘图函数而导致的 `AttributeError`。
*   修复了 `mesh_viewer_qt.py` 中 `QPoint` 和 `QPointF` 从错误的模块 (`QtGui` 而非 `QtCore`) 导入的问题 (`ImportError`)。
*   修复了 `combined_intersection_algorithm.py` 中 `if` 语句块后缺少正确缩进的问题 (`IndentationError`)。
*   解决了因 Python 字节码缓存 (`__pycache__`) 未及时更新导致 UI 修改（移除按钮）不生效的问题。

### 其他

*   (如果适用，可以在此添加对 C++ 模块或其他核心算法的微小调整或修复)

## 已知问题

*   部分新增的 UI 按钮（如 "分割选中边/面", "交换选中边", "AI 修复"）对应的后端功能尚未完全实现。

感谢使用 CFD_PROJECT！ 