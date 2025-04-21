#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <vector>
#include <unordered_map>
#include <tuple>
#include <cmath>
#include <chrono>

namespace py = pybind11;

// 用于存储边的几何哈希键
struct EdgeKey {
    double x1, y1, z1;
    double x2, y2, z2;
    
    EdgeKey(double x1_, double y1_, double z1_, double x2_, double y2_, double z2_)
        : x1(std::min(x1_, x2_)), y1(std::min(y1_, y2_)), z1(std::min(z1_, z2_)),
          x2(std::max(x1_, x2_)), y2(std::max(y1_, y2_)), z2(std::max(z1_, z2_)) {}
    
    bool operator==(const EdgeKey& other) const {
        return std::abs(x1 - other.x1) < 1e-5 &&
               std::abs(y1 - other.y1) < 1e-5 &&
               std::abs(z1 - other.z1) < 1e-5 &&
               std::abs(x2 - other.x2) < 1e-5 &&
               std::abs(y2 - other.y2) < 1e-5 &&
               std::abs(z2 - other.z2) < 1e-5;
    }
};

// 自定义哈希函数
namespace std {
    template<>
    struct hash<EdgeKey> {
        std::size_t operator()(const EdgeKey& k) const {
            // 四舍五入到指定精度
            int precision = 5;
            double scale = std::pow(10, precision);
            
            long long ix1 = std::llround(k.x1 * scale);
            long long iy1 = std::llround(k.y1 * scale);
            long long iz1 = std::llround(k.z1 * scale);
            long long ix2 = std::llround(k.x2 * scale);
            long long iy2 = std::llround(k.y2 * scale);
            long long iz2 = std::llround(k.z2 * scale);
            
            // 组合哈希
            std::size_t h1 = std::hash<long long>()(ix1);
            std::size_t h2 = std::hash<long long>()(iy1);
            std::size_t h3 = std::hash<long long>()(iz1);
            std::size_t h4 = std::hash<long long>()(ix2);
            std::size_t h5 = std::hash<long long>()(iy2);
            std::size_t h6 = std::hash<long long>()(iz2);
            
            return h1 ^ (h2 << 1) ^ (h3 << 2) ^ (h4 << 3) ^ (h5 << 4) ^ (h6 << 5);
        }
    };
}

// 重叠边检测函数
std::tuple<std::vector<std::vector<int>>, double> detect_overlapping_edges_with_timing(
    py::array_t<double> vertices,
    py::array_t<int> faces,
    double tolerance = 1e-5)
{
    auto start = std::chrono::high_resolution_clock::now();
    
    // 获取NumPy数组的缓冲区信息
    auto vertices_buffer = vertices.request();
    auto faces_buffer = faces.request();
    
    double* vertices_ptr = static_cast<double*>(vertices_buffer.ptr);
    int* faces_ptr = static_cast<int*>(faces_buffer.ptr);
    
    int num_vertices = vertices_buffer.shape[0];
    int num_faces = faces_buffer.shape[0];
    
    // 存储边的几何哈希与索引
    std::unordered_map<EdgeKey, std::vector<std::pair<int, int>>> edge_map;
    
    // 遍历所有面片，收集边信息
    for (int face_idx = 0; face_idx < num_faces; ++face_idx) {
        int v1_idx = faces_ptr[face_idx * 3];
        int v2_idx = faces_ptr[face_idx * 3 + 1];
        int v3_idx = faces_ptr[face_idx * 3 + 2];
        
        // 获取面片的三条边
        std::vector<std::pair<int, int>> edges = {
            {v1_idx, v2_idx},
            {v2_idx, v3_idx},
            {v3_idx, v1_idx}
        };
        
        for (const auto& edge : edges) {
            int a = edge.first;
            int b = edge.second;
            
            // 获取顶点坐标
            double x1 = vertices_ptr[a * 3];
            double y1 = vertices_ptr[a * 3 + 1];
            double z1 = vertices_ptr[a * 3 + 2];
            
            double x2 = vertices_ptr[b * 3];
            double y2 = vertices_ptr[b * 3 + 1];
            double z2 = vertices_ptr[b * 3 + 2];
            
            // 创建边的几何键
            EdgeKey key(x1, y1, z1, x2, y2, z2);
            
            // 存储边与其对应的顶点索引
            edge_map[key].push_back({a, b});
        }
    }
    
    // 找出重叠边（出现超过2次的边）
    std::vector<std::vector<int>> overlapping_edges;
    for (const auto& pair : edge_map) {
        if (pair.second.size() > 2) {
            // 使用第一个找到的边作为代表
            overlapping_edges.push_back({pair.second[0].first, pair.second[0].second});
        }
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end - start;
    
    return std::make_tuple(overlapping_edges, elapsed.count());
}

// 创建Python模块
PYBIND11_MODULE(overlapping_edges_cpp, m) {
    m.doc() = "C++ implementation of overlapping edges detection algorithm";
    
    m.def("detect_overlapping_edges_with_timing", &detect_overlapping_edges_with_timing,
          "Detect overlapping edges with timing information",
          py::arg("vertices"), py::arg("faces"), py::arg("tolerance") = 1e-5);
} 