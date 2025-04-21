# Release Notes - V0.1.1

**发布日期:** (请在此处填写实际发布日期, e.g., 2024-07-27)

## 主要变更

本次更新主要集中在相邻面检测逻辑的重构、关键 Python 算法的错误修复以及 C++ 扩展编译流程的标准化。

### 1. 相邻面检测逻辑重构 (C++)

-   **核心变化**: `adjacent_faces_cpp` 模块的相邻判断逻辑完全重写。
-   **新 Proximity 公式**: 移除旧的基于相对质心距离和几何相交的判断方式，改为采用以下 Proximity 公式：
    ```
    P = d / min(L_A, L_B)
    ```
    其中 `d` 是两个面片质心之间的距离，`L_A` 和 `L_B` 分别是两个面片各自的平均边长。
-   **阈值意义改变**: `proximity_threshold` 参数现在直接对应 Proximity 值 `P` 的阈值。只有当 `P <= proximity_threshold` 时，两个面片才被视为相邻。
-   **移除相交判断**: 相邻性判断不再考虑两个面片是否发生几何相交。
-   **预期效果**: 新逻辑更能反映面片间基于其自身尺寸的相对接近程度，避免了旧逻辑中小阈值可能选中过多不相关面片的问题。

### 2. Python 算法错误修复 (`combined_intersection_algorithm.py`)

-   修复了 `execute` 方法中因缩进错误导致在某些情况下返回 `None` 而不是预期结果字典的问题，解决了引发 `'NoneType' object has no attribute 'get'` 错误的根源。
-   全面修复了 `detect_pierced_faces` 和 `detect_pierced_faces_python` 方法中多处 `try...except` 结构不匹配和缩进错误的问题，提高了代码的健壮性和异常处理能力。
-   修正了部分变量（如 `detection_time`, `intersecting_faces`）在特定逻辑分支下可能未定义的问题。

### 3. 标准化 C++ 扩展编译

-   引入了标准的 `setup.py` 文件，用于编译 C++ 扩展模块 (如 `adjacent_faces_cpp`)。
-   **推荐编译方式**: 使用 `python setup.py build_ext --inplace` 进行编译。
-   **目的**: 提供更通用、跨平台的编译方法，替代可能存在的旧脚本 (如 `compile_cpp_extensions.py`)。

## 其他

-   更新了相关文档 (`README.md`, `C++加速使用说明.md`, `docs/self_intersection_algorithm.md`) 以反映上述更改。

## 已知问题

-   性能测试表格中的数据基于 V0.1.0 的逻辑，相邻面检测的性能和加速比在 V0.1.1 中可能有所变化，后续版本会更新基准测试。

## 未来计划

-   对 V0.1.1 的新相邻面检测逻辑进行全面的性能基准测试。
-   根据新的算法逻辑调整默认阈值或提供更直观的阈值设置建议。 