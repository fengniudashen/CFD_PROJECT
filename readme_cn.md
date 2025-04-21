# 计算流体动力学(CFD)项目

## 项目简介

这是一个计算流体动力学(CFD)项目，主要用于处理三维网格模型的自相交检测。项目包含两种实现方式：Python实现和C++实现。C++实现通过Python绑定调用，以提高计算效率。

## 主要功能

- 三维模型自相交检测
- 相邻面检测
- 几何计算（点到三角形距离、点到线段距离等）

## 目录结构

```
CFD_PROJECT/
├── src/                 # 源代码
│   ├── algorithms/      # 算法实现
│   │   └── self_intersection_algorithm.py  # Python实现
│   └── self_intersection_detector.cpp      # C++实现
├── models/              # 测试用的3D模型
├── test_performance.py  # 性能测试脚本
└── README.md            # 本文件
```

## 性能测试

项目提供了一个性能测试脚本，用于比较Python和C++实现的执行效率。

### 使用方法

```bash
python test_performance.py <model_file1> [model_file2 ...]
```

例如：

```bash
python test_performance.py models/bunny.obj models/dragon.obj
```

### 测试内容

测试脚本会：
1. 加载指定的3D模型
2. 使用不同的判断距离参数（0.01, 0.05, 0.1）测试
3. 分别运行Python实现和C++实现并计时
4. 比较两种实现的执行时间和结果一致性
5. 计算加速比
6. 可视化结果并生成图表（保存为performance_comparison.png）

### 测试结果

测试结果将以表格形式在控制台输出，并生成可视化图表。比较内容包括：
- 执行时间对比
- 加速比（Python时间/C++时间）
- 结果一致性检查

## 算法说明

该项目实现了高效的自相交检测算法，主要包含以下关键技术：

1. 空间分割和边界盒检测，用于快速排除不可能相交的三角形
2. 精确的三角形相交测试（Möller-Trumbore算法）
3. 点到三角形和点到线段的最小距离计算
4. 基于欧氏距离的相邻面判断

C++实现通过优化数据结构和算法实现，显著提高了计算效率，尤其适用于大型网格模型。

## 编译C++模块

要编译C++模块，需要运行以下命令：

```bash
python setup_self_intersection.py build_ext --inplace
```

这将在当前目录下生成`self_intersection_cpp`模块，可以直接在Python中导入使用。

## 依赖项

- NumPy
- Trimesh（用于加载和处理3D模型）
- Matplotlib（用于可视化结果）
- C++编译器（用于编译C++实现）
- pybind11（用于Python绑定） 