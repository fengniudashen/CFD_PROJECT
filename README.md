# 计算流体动力学(CFD)项目

## 项目简介

这是一个计算流体动力学(CFD)项目，主要用于处理三维网格模型的自相交检测和网格质量分析。项目包含两种实现方式：Python实现和C++实现。C++实现通过Python绑定调用，以提高计算效率。

## 最新版本 (V0.1.1)

V0.1.1版本更新内容：
- **相邻面检测逻辑重构**: C++实现采用新的 Proximity 公式 `P = d / min(L_A, L_B)` 进行判断，移除了相交判断。
- **错误修复**: 修复了 `combined_intersection_algorithm.py` 中多处 `try...except` 结构、缩进和 `NoneType` 返回值错误。
- **标准化编译**: 引入 `setup.py` 文件，标准化 C++ 扩展模块的编译过程。

## 主要功能

- 三维模型自相交检测
- 相邻面检测 (基于 Proximity 公式 `P = d / min(L_A, L_B)`)
- 穿刺面检测
- 重叠点检测
- 自由边检测
- 面片质量分析
- 几何计算（点到三角形距离、点到线段距离等）
- (V0.1.0) 网格修复工具
- (V0.1.0) 大型网格并行处理

## 目录结构

```
CFD_PROJECT/
├── src/                 # 源代码
│   ├── algorithms/      # 算法实现
│   │   ├── adjacent_faces_detector.cpp     # C++ 相邻面检测实现
│   │   └── combined_intersection_algorithm.py # Python 组合算法
│   ├── utils/           # 工具类
│   ├── mesh/            # 网格处理
│   └── ...              # 其他 C++ 扩展源文件
├── models/              # 测试用的3D模型
├── docs/                # 文档
├── tests/               # 单元测试
├── benchmark/           # 性能基准测试
├── test_performance.py  # 性能测试脚本
├── setup.py             # C++ 模块编译脚本 (推荐)
└── README.md            # 本文件
```

## 安装与使用

### 基本安装

```bash
# 克隆仓库
git clone https://github.com/fengniudashen/CFD_PROJECT.git
cd CFD_PROJECT

# 安装依赖
pip install -r requirements.txt
```

### 编译C++扩展（可选但推荐）

为获得最佳性能，建议编译C++扩展模块：

```bash
# 安装编译依赖 (如果尚未安装)
pip install setuptools pybind11

# 确保已安装 C++ 编译器 (如 MSVC Build Tools)
# 执行编译
python setup.py build_ext --inplace
```
详细说明请参考 `C++加速使用说明.md`。

## 性能测试

项目提供了性能测试脚本，用于比较Python和C++实现的执行效率。

### 使用方法

```bash
python test_performance.py <model_file1> [model_file2 ...]
```

### 测试结果 (基于V0.1.0, V0.1.1 相邻面逻辑已变)

*注意: V0.1.1 修改了相邻面检测逻辑，以下加速比可能发生变化。*

| 功能     | Python实现 | C++实现 (V0.1.0) | 加速比 (V0.1.0) |
| ------ | -------- | -------------- | --------------- |
| 相邻面检测  | 120秒     | 2.5秒          | 48倍            |
| 重叠点检测  | 35秒      | 0.3秒          | 117倍           |
| 面片质量分析 | 25秒      | 0.6秒          | 42倍            |
| 穿刺面检测  | 250秒     | 0.4秒          | 625倍           |
| 网格修复   | 180秒     | 3秒            | 60倍            |

## 多线程性能 (基于V0.1.0)

V0.1.0版本引入了多线程支持，以下是多线程模式下的性能对比（8核处理器测试）：

| 线程数 | 相邻面检测 (V0.1.0) | 重叠点检测 | 面片质量分析 |
| --- | --------------- | ----- | ------ |
| 1线程 | 2.5秒           | 0.3秒  | 0.6秒   |
| 4线程 | 0.8秒           | 0.1秒  | 0.2秒   |
| 8线程 | 0.5秒           | 0.06秒 | 0.12秒  |

## 算法说明

该项目实现了高效的自相交检测算法，主要包含以下关键技术：

1.  **空间分割与优化**: 使用AABB包围盒和八叉树等技术快速排除不相关的计算。
2.  **精确几何计算**: 包括三角形相交测试（Möller-Trumbore算法）、点到三角形/线段的最小距离计算。
3.  **相邻面检测 (V0.1.1)**: 基于 Proximity 公式 `P = d / min(L_A, L_B)` 判断面片邻近性，其中 `d` 为质心距离，`L_A`, `L_B` 为各自平均边长。
4.  (来自 V0.1.0) 多线程计算框架。
5.  (来自 V0.1.0) 网格修复算法。

C++实现通过优化数据结构和算法实现，显著提高了计算效率，尤其适用于大型网格模型。

## 依赖项

- Python 3.6+
- NumPy
- PyQt5（用户界面）
- VTK（3D可视化）
- pybind11（C++绑定，编译C++扩展时需要）
- C++编译器（编译C++扩展时需要）
- setuptools (编译C++扩展时需要)
- OpenMP（可选，用于多线程支持）

## 文档

详细文档请参阅`docs/`目录。关键文档包括：

- API参考：`docs/api_reference.md`
- 安装指南：`docs/installation_guide.md`
- 算法说明：`docs/self_intersection_algorithm.md`
- 发布说明：`docs/release_notes_V0.1.1.md` (新增)
- C++加速说明: `C++加速使用说明.md`

## 许可证

本项目采用MIT许可证。
