# CFD项目C++库构建指南

本指南提供详细步骤，介绍如何编译和使用CFD项目中的C++库。

## 系统要求

- **操作系统**：
  - Windows 10/11
  - Linux (Ubuntu 18.04+, CentOS 7+)
  - macOS 10.14+

- **编译器**：
  - Windows: Visual Studio 2017+或MinGW-w64 8.0+
  - Linux: GCC 7.0+
  - macOS: Clang 6.0+或GCC 7.0+

- **构建工具**：
  - CMake 3.10+
  - Python 3.7+
  - pip (Python包管理器)

- **依赖项**：
  - Eigen 3.3+ (矩阵计算库)
  - pybind11 2.6+ (Python绑定库)

## 安装依赖项

### Windows

1. 安装Visual Studio (包含C++编译器)

2. 安装Python和依赖库：
   ```cmd
   :: 安装Python依赖
   pip install pybind11 numpy setuptools wheel
   
   :: 安装Eigen (使用vcpkg)
   git clone https://github.com/Microsoft/vcpkg.git
   cd vcpkg
   .\bootstrap-vcpkg.bat
   .\vcpkg install eigen3
   ```

### Linux

```bash
# 安装编译器和构建工具
sudo apt-get update
sudo apt-get install -y build-essential cmake python3-dev python3-pip

# 安装Python依赖
pip3 install pybind11 numpy setuptools wheel

# 安装Eigen
sudo apt-get install -y libeigen3-dev
```

### macOS

```bash
# 使用Homebrew安装依赖
brew install cmake eigen python

# 安装Python依赖
pip3 install pybind11 numpy setuptools wheel
```

## 获取源代码

```bash
# 克隆仓库
git clone https://github.com/your-username/cfd-project.git
cd cfd-project
```

## 构建free_edges_cpp库

### 使用setuptools构建（推荐）

```bash
# 进入src目录
cd src

# 构建库
python setup.py build_ext --inplace

# 运行测试
python compare_free_edges.py
```

### 使用CMake构建（可选）

```bash
mkdir build-free-edges && cd build-free-edges
cmake ../src/free_edges_cpp
make
```

## 构建mesh_reader库

```bash
# 创建构建目录
mkdir build-mesh-reader && cd build-mesh-reader

# 配置和构建
cmake ../src/mesh_reader
make

# 安装库（可选）
sudo make install
```

## 验证安装

### 测试free_edges_cpp

```python
# 创建测试文件test_free_edges.py
import numpy as np
import free_edges_cpp

# 创建一个简单的立方体
faces = [
    [0, 1, 2], [0, 2, 3],  # 前面
    [4, 6, 5], [4, 7, 6],  # 后面
    [0, 3, 7], [0, 7, 4],  # 左面
    [1, 5, 6], [1, 6, 2],  # 右面
    [0, 4, 5], [0, 5, 1],  # 下面
    [2, 6, 7], [2, 7, 3],  # 上面
]

# 删除一个面，创建自由边
faces.pop()

# 检测自由边
free_edges, time = free_edges_cpp.detect_free_edges_with_timing(faces)
print(f"检测到{len(free_edges)}条自由边，耗时{time:.6f}秒")
print(f"自由边: {free_edges}")
```

### 测试mesh_reader

```python
# 创建测试文件test_mesh_reader.py
from mesh_reader import read_nas_file

# 读取网格文件（替换为您的文件路径）
mesh = read_nas_file("path/to/your/model.nas")

# 打印网格信息
print(f"顶点数量: {len(mesh['vertices'])}")
print(f"面片数量: {len(mesh['faces'])}")
```

## 常见问题解决

### ImportError: No module named 'free_edges_cpp'

确保您在正确的目录中构建了库，并且构建成功。您可以运行以下命令检查是否生成了pyd文件：

```bash
# Windows
dir src\*.pyd

# Linux/macOS
ls -la src/*.so
```

### 编译错误："pybind11/pybind11.h: No such file or directory"

确保正确安装了pybind11并且可以被编译器找到：

```bash
# 检查pybind11安装位置
python -c "import pybind11; print(pybind11.get_include())"

# 确保包含该目录
export CPLUS_INCLUDE_PATH=$(python -c "import pybind11; print(pybind11.get_include())")
```

### Eigen相关错误

确保Eigen库正确安装且路径正确：

```bash
# 设置Eigen包含路径（Linux示例）
export CPLUS_INCLUDE_PATH=/usr/include/eigen3:$CPLUS_INCLUDE_PATH
```

## 更多资源

- [pybind11文档](https://pybind11.readthedocs.io/)
- [Eigen文档](https://eigen.tuxfamily.org/dox/)
- [CMake文档](https://cmake.org/documentation/)

## 联系和支持

如有问题，请通过项目Issues页面联系我们：
[https://github.com/your-username/cfd-project/issues](https://github.com/your-username/cfd-project/issues) 