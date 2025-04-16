# CFD项目安装指南 (V0.0.9)

*更新日期: 2024-06-16*

本文档提供了CFD项目V0.0.9版本的详细安装说明，包括基本环境配置和C++扩展模块的编译方法。

## 系统要求

- **操作系统**：Windows 7/10/11、Linux、macOS
- **Python版本**：3.6或更高版本
- **C++编译器**（用于编译C++扩展，可选但推荐）：
  - Windows: Visual Studio 2017或更高版本
  - Linux: GCC 7或更高版本
  - macOS: Clang 8或更高版本
- **磁盘空间**：至少200MB
- **内存**：至少4GB（处理大型模型时建议8GB或更多）

## 基本安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/fengniudashen/CFD_PROJECT.git
cd CFD_PROJECT
```

### 2. 创建虚拟环境（推荐）

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python -m venv venv
source venv/bin/activate
```

### 3. 安装依赖包

```bash
pip install -r requirements.txt
```

## 编译C++扩展模块

为获得最佳性能，强烈建议编译C++扩展模块。V0.0.9版本提供了简化的编译脚本，能自动处理依赖安装和编译过程。

### 使用自动编译脚本

```bash
python compile_cpp_extensions.py
```

成功编译后，您会看到类似以下输出：

```
================================================================================
所有C++扩展模块编译成功!
================================================================================

================================================================================
检查编译后的模块...
================================================================================
✓ self_intersection_cpp (相邻面检测) 已成功加载!
✓ non_manifold_vertices_cpp (重叠点检测) 已成功加载!
✓ face_quality_cpp (面片质量检测) 已成功加载!

================================================================================
编译过程完成
================================================================================
提示: 如果编译成功，您现在可以启动程序并享受C++加速的性能提升！
```

### 手动编译各个模块（如有需要）

如果自动脚本运行失败，您可以尝试手动编译各个模块：

```bash
# 编译相邻面检测模块
python setup_self_intersection.py build_ext --inplace

# 编译重叠点检测模块
python src/setup_non_manifold_vertices.py build_ext --inplace

# 编译面片质量分析模块
python src/setup_face_quality.py build_ext --inplace
```

## 验证安装

编译完成后，可以通过运行示例程序验证安装：

```bash
# 运行足球网格示例
python src/example_football.py
```

如果看到创建的3D足球模型并且没有错误信息，说明安装成功。

## 常见问题解决

### 1. 缺少pybind11

**症状**：编译时报错 "未找到pybind11"
**解决方案**：手动安装pybind11

```bash
pip install pybind11
```

### 2. 编译器错误

**症状**：找不到合适的编译器
**解决方案**：确保已安装正确的C++编译器并设置环境变量

- Windows: 安装Visual Studio Build Tools
- Linux: `sudo apt-get install build-essential`
- macOS: `xcode-select --install`

### 3. 导入错误

**症状**：`ImportError: No module named 'self_intersection_cpp'`
**解决方案**：确保C++模块编译成功并位于正确路径

- 检查当前目录下是否存在 `self_intersection_cpp.*.pyd` (Windows) 或 `.so` (Linux/macOS) 文件
- 将编译好的模块复制到Python路径中：`cp *.pyd src/`

## 升级说明

如果您是从较早版本升级到V0.0.9，请按照以下步骤操作：

1. 更新代码库：
   ```bash
   git pull origin main
   ```

2. 安装或更新依赖：
   ```bash
   pip install -r requirements.txt --upgrade
   ```

3. 重新编译C++扩展：
   ```bash
   python compile_cpp_extensions.py
   ```

## 下一步

安装完成后，请参考以下文档：

- [用户指南](user_guide.md) - 了解软件基本使用方法
- [API参考](api_reference.md) - 查看详细功能说明
- [开发指南](developer_guide.md) - 如果您希望贡献代码 