# 面相交检测算法及C++扩展模块总结

## 面相交检测功能概述

该系统中的面相交检测功能是CFD网格处理的关键组成部分，用于识别网格中相互穿刺(相交)的三角形面片。这些穿刺面会导致CFD仿真出现问题，因此需要及时发现并修复。

## 实现方式

系统提供了两种实现方式：
1. **Python实现**：基于分离轴定理(SAT)的纯Python实现
2. **C++高性能实现**：通过pybind11绑定到Python的C++实现

## C++扩展模块的重要性

在`mesh_viewer_qt.py`中的`check_cpp_extensions`方法通过尝试导入各种C++扩展模块来检测它们是否可用，包括：

- `self_intersection_cpp`：用于自相交检测
- `pierced_faces_cpp`：用于穿刺面检测
- `non_manifold_vertices_cpp`：用于非流形顶点检测
- `overlapping_points_cpp`：用于重叠点检测
- `face_quality_cpp`：用于面质量检测

其中`pierced_faces_cpp`模块特别重要，它还会检查是否为增强版模块(支持相交映射)。

### 性能优势

根据文档，C++实现相比Python版本有显著的性能提升：
- 在大型网格处理中，性能提升高达1000倍
- 大大缩短了检测时间，从几小时缩减到几秒钟

### 增强版C++模块

系统会检测`pierced_faces_cpp`模块是否为增强版：
```python
try:
    # 使用极小的测试网格测试新功能
    test_verts = np.array([[0,0,0],[1,0,0],[0,1,0]], dtype=np.float64)
    test_faces = np.array([[0,1,2]], dtype=np.int32)
    _, test_map, _ = pierced_faces_cpp.detect_pierced_faces_with_timing(test_faces, test_verts)
    print("已加载增强版 pierced_faces_cpp 模块 (支持相交映射)")
    self.has_enhanced_pierced_faces = True
except ValueError:
    print("已加载基础版 pierced_faces_cpp 模块 (不支持相交映射)")
    self.has_enhanced_pierced_faces = False
```

增强版C++模块的特点：
- 支持完整的相交关系映射（能返回每个面与哪些面相交）
- 无需后处理即可获得相交关系

### 技术实现细节

C++模块`pierced_faces_detector.cpp`实现了高效的穿刺面检测算法，主要特点包括：

1. 使用向量计算优化的分离轴定理(SAT)实现
2. 八叉树空间分区技术加速检测过程
3. AABB包围盒快速预过滤
4. 高效的点、边和面的相交测试
5. 优化的内存管理策略

## 在系统中的集成

在`mesh_viewer_qt.py`的`detect_face_intersections`方法中：

```python
# 检查是否有缓存结果且模型未修改
if not self.model_modified and self.detection_cache['face_intersections'] is not None:
    # 直接使用缓存结果
    self.selected_faces = self.detection_cache['face_intersections']
    # 如果缓存中有相交映射关系，也一并恢复
    if 'face_intersection_map' in self.detection_cache:
        self.face_intersection_map = self.detection_cache['face_intersection_map']
    self.update_display()
    print("使用缓存：交叉面检测 (已选择 " + str(len(self.selected_faces)) + " 个面)")
    return

# 设置增强CPP优先的配置
cpp_preference = {
    "use_cpp": True,
    "force_enhanced": hasattr(self, 'has_enhanced_pierced_faces') and self.has_enhanced_pierced_faces
}

# 创建并执行穿刺面检测算法 - 使用新的合并算法，设置detection_mode="pierced"
from algorithms.combined_intersection_algorithm import CombinedIntersectionAlgorithm
algorithm = CombinedIntersectionAlgorithm(self.mesh_data, detection_mode="pierced")

# 如果存在增强模块，设置增强标志
if hasattr(self, 'has_enhanced_pierced_faces'):
    algorithm.enhanced_cpp_available = self.has_enhanced_pierced_faces
```

系统会：
1. 先检查缓存结果是否有效
2. 优先使用C++算法，特别是增强版C++模块
3. 如果C++模块不可用，则回退到Python实现

## 相交映射关系的重要性

相交映射关系（由增强版C++模块提供）使系统能够：
1. 快速定位相交面并显示它们的关系
2. 实现更高效的网格修复功能
3. 支持点击某个面片时显示与之相交的所有面片：

```python
def show_face_intersections(self, face_idx):
    """显示指定面片的所有相交面片"""
    if not hasattr(self, 'face_intersection_map') or not self.face_intersection_map:
        QMessageBox.information(self, "信息", "没有可用的面片相交关系数据，请先运行相交检测。")
        return
    
    face_idx = int(face_idx)  # 确保是整数
    if face_idx not in self.face_intersection_map:
        QMessageBox.information(self, "信息", f"面片 #{face_idx} 没有相交关系。")
        return
    
    # 获取与当前面片相交的所有面片
    intersecting_faces = self.face_intersection_map[face_idx]
    
    # 高亮显示这些面片
    self.selected_faces = [face_idx] + list(intersecting_faces)
    self.update_display()
```

## 通知用户C++扩展状态

系统会在界面中通知用户C++扩展的状态：

```python
# 检查C++扩展模块是否可用
self.has_cpp_extensions = self.check_cpp_extensions()

# 显示状态栏信息
if not self.has_cpp_extensions:
    self.statusBar.showMessage("提示: 安装C++模块可显著提高性能")
```

## 总结

C++扩展模块，尤其是`pierced_faces_cpp`，对于系统的面相交检测功能至关重要：

1. 显著提高处理大型网格的性能
2. 提供完整的相交关系映射
3. 支持更高级的交互功能
4. 无需手动重建相交关系

如果没有C++扩展模块，系统将回退到Python实现，但会导致性能显著下降，尤其是在处理大型网格时。增强版C++模块的可用性直接影响系统的功能完整性和性能。 