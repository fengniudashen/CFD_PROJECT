# mesh_reader：高性能网格文件读取库

`mesh_reader`是一个C++实现的高性能网格文件读取库，支持多种格式的网格文件读取，特别针对CFD分析中的大型网格模型进行了优化。

## 功能概述

- 支持多种网格格式读取：
  - NAS/Nastran格式(.nas)
  - STL格式(.stl)，包括ASCII和二进制
- 为每种格式提供专门优化的高效读取器
- 提供C++原生API和Python绑定
- 高效内存管理，适合大型模型
- 面向对象设计，易于扩展支持更多格式

## API参考

### C++ API

库的核心是抽象的`MeshReader`接口和对应的实现类：

```cpp
// 核心数据结构
struct MeshData {
    Eigen::MatrixXf vertices;  // Nx3矩阵，存储顶点坐标
    Eigen::MatrixXi faces;     // Mx3矩阵，存储面片索引
    Eigen::MatrixXf normals;   // Mx3矩阵，存储面法向量
};

// 抽象读取器接口
class MeshReader {
public:
    virtual ~MeshReader() = default;
    virtual MeshData read(const std::string& file_path) = 0;
};

// STL文件读取器
class STLReader : public MeshReader {
public:
    MeshData read(const std::string& file_path) override;

private:
    bool is_binary(const std::vector<char>& header);
    MeshData read_binary(const std::string& file_path);
    MeshData read_ascii(const std::string& file_path);
};

// NAS/Nastran文件读取器
class NASReader : public MeshReader {
public:
    MeshData read(const std::string& file_path) override;
};

// 工厂函数 - 根据文件扩展名自动创建合适的读取器
std::unique_ptr<MeshReader> create_mesh_reader(const std::string& file_path);

// 便捷函数 - 直接读取NAS文件
MeshData read_nas_file(const std::string& file_path);
```

### Python API

通过Python绑定，可以在Python中直接使用这些功能：

```python
from mesh_reader import create_mesh_reader, read_nas_file

# 使用工厂函数
reader = create_mesh_reader("model.nas")
mesh_data = reader.read("model.nas")

# 或直接使用便捷函数
mesh_data = read_nas_file("model.nas")

# 访问网格数据
vertices = mesh_data['vertices']
faces = mesh_data['faces']
normals = mesh_data['normals']
```

## 技术实现

### NASReader

NAS文件读取器实现了针对Nastran格式的高效解析：

```cpp
MeshData NASReader::read(const std::string& file_path) {
    // 第一遍：计数以预分配内存
    size_t vertex_count = 0;
    size_t face_count = 0;
    {
        std::ifstream counter_file(file_path);
        std::string line;
        while (std::getline(counter_file, line)) {
            if (line.rfind("GRID*", 0) == 0) {
                vertex_count++;
                std::getline(counter_file, line); // 跳过GRID*的第二行
            } else if (line.rfind("CTRIA3", 0) == 0) {
                face_count++;
            }
        }
    }
    
    // 预分配Eigen矩阵
    Eigen::MatrixXf vertices(vertex_count, 3);
    Eigen::MatrixXi faces(face_count, 3);
    std::unordered_map<int, int> node_map;
    
    // 第二遍：读取数据
    // 此处省略具体实现...
    
    return MeshData{vertices, faces, normals};
}
```

### STLReader

STL读取器支持ASCII和二进制格式，并自动检测：

```cpp
MeshData STLReader::read(const std::string& file_path) {
    std::ifstream file(file_path, std::ios::binary);
    std::vector<char> header(80);
    file.read(header.data(), 80);
    file.close();
    
    if (is_binary(header)) {
        return read_binary(file_path);
    } else {
        return read_ascii(file_path);
    }
}
```

## 性能优化

库使用了多种性能优化技术：

1. **两遍读取策略**：
   - 第一遍计数，确定精确的内存需求
   - 第二遍读取数据，避免频繁的内存重分配

2. **内存预分配**：
   - 使用Eigen矩阵预分配，减少内存碎片
   - 对大型哈希表使用reserve，避免重哈希

3. **高效字符串处理**：
   - 使用rfind和前缀比较代替字符串比较
   - 减少不必要的字符串分配

4. **自定义哈希表**：
   - 用于节点ID到索引的快速查找
   - 优化插入和查找性能

## 构建指南

### 依赖项

- C++14兼容的编译器
- Eigen 3.3+
- Python 3.7+ (用于Python绑定)
- pybind11 (用于Python绑定)

### 构建步骤

1. 安装依赖项
   ```bash
   pip install pybind11 eigen
   ```

2. 编译库
   ```bash
   # 设置Eigen路径
   export EIGEN_INCLUDE_DIR=/path/to/eigen
   
   # 编译
   mkdir build && cd build
   cmake ..
   make
   ```

3. 安装
   ```bash
   make install
   ```

## 使用示例

### 读取Nastran文件示例

```cpp
#include "mesh_reader.hpp"
#include <iostream>

int main() {
    try {
        // 读取NAS文件
        cfd::MeshData mesh = cfd::read_nas_file("model.nas");
        
        // 输出网格信息
        std::cout << "顶点数量: " << mesh.vertices.rows() << std::endl;
        std::cout << "面片数量: " << mesh.faces.rows() << std::endl;
        
        // 处理网格数据...
        
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "错误: " << e.what() << std::endl;
        return 1;
    }
}
```

### Python中使用示例

```python
import numpy as np
from mesh_reader import read_nas_file

# 读取网格文件
mesh = read_nas_file("complex_model.nas")

# 访问网格数据
vertices = mesh['vertices']
faces = mesh['faces']

# 计算统计信息
print(f"模型包含 {len(vertices)} 个顶点和 {len(faces)} 个面片")
print(f"顶点坐标范围: X [{vertices[:, 0].min():.2f}, {vertices[:, 0].max():.2f}]")
print(f"顶点坐标范围: Y [{vertices[:, 1].min():.2f}, {vertices[:, 1].max():.2f}]")
print(f"顶点坐标范围: Z [{vertices[:, 2].min():.2f}, {vertices[:, 2].max():.2f}]")
```

## 已知限制

- Nastran格式支持有限，主要支持`GRID*`和`CTRIA3`
- 仅支持三角形面片，不支持四边形和多边形
- 不支持无序网格格式(如OBJ、PLY等)
- 不支持并行读取，这可能在极大型文件上导致性能瓶颈

## 未来改进

- 添加并行读取支持(使用OpenMP)
- 扩展对更多Nastran元素类型的支持
- 添加对OBJ、PLY等格式的支持
- 添加压缩文件(zip、gz等)读取支持
- 提供写入功能，实现格式转换 