#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <stack>
#include <chrono>

namespace py = pybind11;

// Define edge as a pair of ints
typedef std::pair<int, int> Edge;

// Edge hash function
struct EdgeHash {
    std::size_t operator()(const Edge& e) const {
        return std::hash<int>()(e.first) ^ (std::hash<int>()(e.second) << 1);
    }
};

// Edge equality function
struct EdgeEqual {
    bool operator()(const Edge& e1, const Edge& e2) const {
        return e1.first == e2.first && e1.second == e2.second;
    }
};

// Non-manifold vertex detection implementation
// 非流形顶点检测实现
// 定义：当一个点连接了4条（包括4条）以上的自由边时，这个点就是重叠点
std::pair<std::vector<int>, double> detect_non_manifold_vertices_with_timing(
    py::array_t<double> vertices,
    py::array_t<int> faces,
    double tolerance) {
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Get vertex and face data
    auto vertices_buf = vertices.request();
    auto faces_buf = faces.request();
    
    double* vertices_ptr = static_cast<double*>(vertices_buf.ptr);
    int* faces_ptr = static_cast<int*>(faces_buf.ptr);
    
    int num_vertices = vertices_buf.shape[0];
    int num_faces = faces_buf.shape[0];
    
    // 步骤1：找出所有边及其连接的面片数量
    std::unordered_map<Edge, std::vector<int>, EdgeHash, EdgeEqual> edges;
    for (int face_idx = 0; face_idx < num_faces; ++face_idx) {
        for (int i = 0; i < 3; ++i) {
            int v1 = faces_ptr[face_idx * 3 + i];
            int v2 = faces_ptr[face_idx * 3 + (i + 1) % 3];
            Edge edge(std::min(v1, v2), std::max(v1, v2));
            edges[edge].push_back(face_idx);
        }
    }
    
    // 步骤2：找出自由边（只连接了一个面片的边）
    std::unordered_set<Edge, EdgeHash, EdgeEqual> free_edges;
    for (const auto& pair : edges) {
        if (pair.second.size() == 1) {
            free_edges.insert(pair.first);
        }
    }
    
    // 步骤3：计算每个顶点连接的自由边数量
    std::unordered_map<int, int> vertex_free_edge_count;
    for (const Edge& edge : free_edges) {
        vertex_free_edge_count[edge.first]++;
        vertex_free_edge_count[edge.second]++;
    }
    
    // 步骤4：找出连接了4条或以上自由边的顶点
    std::vector<int> non_manifold_vertices;
    for (const auto& pair : vertex_free_edge_count) {
        if (pair.second >= 4) {  // 定义：连接4条或以上自由边的点是非流形顶点
            non_manifold_vertices.push_back(pair.first);
        }
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    double detection_time = std::chrono::duration<double>(end_time - start_time).count();
    
    return std::make_pair(non_manifold_vertices, detection_time);
}

PYBIND11_MODULE(non_manifold_vertices_cpp, m) {
    m.doc() = "C++ implementation for non-manifold vertex detection";
    
    m.def("detect_non_manifold_vertices_with_timing", 
          &detect_non_manifold_vertices_with_timing,
          "Detect non-manifold vertices and return detection time",
          py::arg("vertices"),
          py::arg("faces"),
          py::arg("tolerance"));
} 