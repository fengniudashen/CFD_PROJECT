#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <vector>
#include <set>
#include <map>
#include <cmath>
#include <chrono>
#include <algorithm>
#include <array>
#include <limits>
#include <functional>
#include <tuple>

namespace py = pybind11;
using namespace std;

// 一些用于浮点比较的常量
constexpr double EPSILON = 1e-10;
constexpr double ALMOST_ZERO = 1e-8;

// 定义三维向量类型
struct Vector3d {
    double x, y, z;
    
    Vector3d() : x(0), y(0), z(0) {}
    Vector3d(double x, double y, double z) : x(x), y(y), z(z) {}
    
    Vector3d operator+(const Vector3d& other) const {
        return Vector3d(x + other.x, y + other.y, z + other.z);
    }
    
    Vector3d operator-(const Vector3d& other) const {
        return Vector3d(x - other.x, y - other.y, z - other.z);
    }
    
    Vector3d operator*(double scalar) const {
        return Vector3d(x * scalar, y * scalar, z * scalar);
    }
    
    Vector3d operator/(double scalar) const {
        if (std::abs(scalar) < ALMOST_ZERO) {
            return Vector3d();
        }
        return Vector3d(x / scalar, y / scalar, z / scalar);
    }
    
    double dot(const Vector3d& other) const {
        return x * other.x + y * other.y + z * other.z;
    }
    
    Vector3d cross(const Vector3d& other) const {
        return Vector3d(
            y * other.z - z * other.y,
            z * other.x - x * other.z,
            x * other.y - y * other.x
        );
    }
    
    double norm() const {
        return std::sqrt(x * x + y * y + z * z);
    }
    
    Vector3d normalized() const {
        double length = norm();
        if (length < ALMOST_ZERO) {
            return Vector3d();
        }
        return *this / length;
    }
    
    bool isZero(double eps = ALMOST_ZERO) const {
        return std::abs(x) < eps && std::abs(y) < eps && std::abs(z) < eps;
    }
    
    static Vector3d Zero() {
        return Vector3d();
    }
};

// 三角形结构
struct Triangle {
    array<Vector3d, 3> vertices;

    Triangle(const Vector3d& v0, const Vector3d& v1, const Vector3d& v2) {
        vertices = {v0, v1, v2};
    }
};

// AABB包围盒
struct AABB {
    Vector3d min;
    Vector3d max;

    AABB(const Vector3d& min_point, const Vector3d& max_point) 
        : min(min_point), max(max_point) {}

    bool intersects(const AABB& other) const {
        return (min.x <= other.max.x && max.x >= other.min.x &&
                min.y <= other.max.y && max.y >= other.min.y &&
                min.z <= other.max.z && max.z >= other.min.z);
    }
};

// 获取三角形的法向量
Vector3d get_normal(const Triangle& tri) {
    Vector3d v1 = tri.vertices[1] - tri.vertices[0];
    Vector3d v2 = tri.vertices[2] - tri.vertices[0];
    Vector3d normal = v1.cross(v2);
    double norm = normal.norm();
    
    if (norm < ALMOST_ZERO) {
        return Vector3d::Zero();
    }
    return normal / norm;
}

// 获取三角形的边
vector<Vector3d> get_edges(const Triangle& tri) {
    return {
        tri.vertices[1] - tri.vertices[0],
        tri.vertices[2] - tri.vertices[1],
        tri.vertices[0] - tri.vertices[2]
    };
}

// 将三角形投影到轴上
pair<double, double> project_triangle(const Triangle& tri, const Vector3d& axis) {
    double min_proj = axis.dot(tri.vertices[0]);
    double max_proj = min_proj;
    
    for (int i = 1; i < 3; ++i) {
        double proj = axis.dot(tri.vertices[i]);
        min_proj = min(min_proj, proj);
        max_proj = max(max_proj, proj);
    }
    
    return {min_proj, max_proj};
}

// 检查在给定轴上是否分离
bool check_separation(const Triangle& tri1, const Triangle& tri2, const Vector3d& axis) {
    if (axis.isZero()) {
        return false;
    }
    
    // 改用传统写法替代结构化绑定
    pair<double, double> p1_proj = project_triangle(tri1, axis);
    double p1_min = p1_proj.first;
    double p1_max = p1_proj.second;
    
    pair<double, double> p2_proj = project_triangle(tri2, axis);
    double p2_min = p2_proj.first;
    double p2_max = p2_proj.second;
    
    return p1_max < p2_min || p2_max < p1_min;
}

// 使用分离轴定理检查两个三角形是否相交
bool check_triangle_intersection(const Triangle& tri1, const Triangle& tri2) {
    // 1. 检查面法向量轴
    Vector3d normal1 = get_normal(tri1);
    Vector3d normal2 = get_normal(tri2);
    
    if (!normal1.isZero() && check_separation(tri1, tri2, normal1)) {
        return false;
    }
    
    if (!normal2.isZero() && check_separation(tri1, tri2, normal2)) {
        return false;
    }
    
    // 2. 检查边叉积轴
    vector<Vector3d> edges1 = get_edges(tri1);
    vector<Vector3d> edges2 = get_edges(tri2);
    
    for (const auto& e1 : edges1) {
        for (const auto& e2 : edges2) {
            Vector3d cross = e1.cross(e2);
            if (!cross.isZero()) {
                Vector3d axis = cross.normalized();
                if (check_separation(tri1, tri2, axis)) {
                    return false;
                }
            }
        }
    }
    
    // 没有找到分离轴，三角形相交
    return true;
}

// 计算三角形的AABB包围盒
AABB compute_triangle_aabb(const Triangle& tri) {
    Vector3d min_point = tri.vertices[0];
    Vector3d max_point = tri.vertices[0];
    
    for (int i = 1; i < 3; ++i) {
        min_point.x = min(min_point.x, tri.vertices[i].x);
        min_point.y = min(min_point.y, tri.vertices[i].y);
        min_point.z = min(min_point.z, tri.vertices[i].z);
        
        max_point.x = max(max_point.x, tri.vertices[i].x);
        max_point.y = max(max_point.y, tri.vertices[i].y);
        max_point.z = max(max_point.z, tri.vertices[i].z);
    }
    
    return AABB(min_point, max_point);
}

// 八叉树节点
struct OctreeNode {
    Vector3d center;
    double size;
    int depth;
    vector<int> face_indices;
    array<shared_ptr<OctreeNode>, 8> children;
    
    OctreeNode(const Vector3d& center, double size, int depth)
        : center(center), size(size), depth(depth) {
        for (auto& child : children) {
            child = nullptr;
        }
    }
    
    int get_octant(const Vector3d& point) const {
        int octant = 0;
        if (point.x >= center.x) octant |= 1;
        if (point.y >= center.y) octant |= 2;
        if (point.z >= center.z) octant |= 4;
        return octant;
    }
};

// 构建八叉树
shared_ptr<OctreeNode> build_octree(const vector<Triangle>& triangles, 
                                  const vector<int>& face_indices,
                                  const Vector3d& center, double size, 
                                  int depth, int max_depth, int min_faces) {
    auto node = make_shared<OctreeNode>(center, size, depth);
    node->face_indices = face_indices;
    
    // 基本终止条件
    if (depth >= max_depth || face_indices.size() <= min_faces) {
        return node;
    }
    
    // 根据八叉树节点划分面片
    array<vector<int>, 8> child_faces;
    
    for (int face_idx : face_indices) {
        const Triangle& tri = triangles[face_idx];
        Vector3d tri_center(
            (tri.vertices[0].x + tri.vertices[1].x + tri.vertices[2].x) / 3.0,
            (tri.vertices[0].y + tri.vertices[1].y + tri.vertices[2].y) / 3.0,
            (tri.vertices[0].z + tri.vertices[1].z + tri.vertices[2].z) / 3.0
        );
        int octant = node->get_octant(tri_center);
        child_faces[octant].push_back(face_idx);
    }
    
    // 创建子节点
    double half_size = size / 2.0;
    
    for (int i = 0; i < 8; ++i) {
        if (child_faces[i].empty()) {
            continue;
        }
        
        Vector3d child_center = center;
        if (i & 1) child_center.x += half_size; else child_center.x -= half_size;
        if (i & 2) child_center.y += half_size; else child_center.y -= half_size;
        if (i & 4) child_center.z += half_size; else child_center.z -= half_size;
        
        node->children[i] = build_octree(triangles, child_faces[i], 
                                        child_center, half_size, 
                                        depth + 1, max_depth, min_faces);
    }
    
    return node;
}

// 主函数：检测相交的面片
std::tuple<std::vector<int>, std::map<int, std::vector<int>>, double> detect_pierced_faces_with_timing(py::array_t<int> py_faces, py::array_t<double> py_vertices) {
    auto start = std::chrono::high_resolution_clock::now();
    
    // 转换输入数据
    auto faces_buf = py_faces.unchecked<2>();
    auto vertices_buf = py_vertices.unchecked<2>();
    
    const size_t num_faces = faces_buf.shape(0);
    const size_t num_vertices = vertices_buf.shape(0);
    
    // 创建三角形数组
    vector<Triangle> triangles;
    triangles.reserve(num_faces);
    
    // 创建AABB数组
    vector<AABB> face_bboxes;
    face_bboxes.reserve(num_faces);
    
    // 填充数据
    for (size_t face_idx = 0; face_idx < num_faces; ++face_idx) {
        Vector3d v0(
            vertices_buf(faces_buf(face_idx, 0), 0),
            vertices_buf(faces_buf(face_idx, 0), 1),
            vertices_buf(faces_buf(face_idx, 0), 2)
        );
        
        Vector3d v1(
            vertices_buf(faces_buf(face_idx, 1), 0),
            vertices_buf(faces_buf(face_idx, 1), 1),
            vertices_buf(faces_buf(face_idx, 1), 2)
        );
        
        Vector3d v2(
            vertices_buf(faces_buf(face_idx, 2), 0),
            vertices_buf(faces_buf(face_idx, 2), 1),
            vertices_buf(faces_buf(face_idx, 2), 2)
        );
        
        Triangle tri(v0, v1, v2);
        triangles.push_back(tri);
        
        // 计算AABB包围盒
        face_bboxes.push_back(compute_triangle_aabb(tri));
    }
    
    // 计算八叉树的边界
    Vector3d min_point(
        std::numeric_limits<double>::max(),
        std::numeric_limits<double>::max(),
        std::numeric_limits<double>::max()
    );
    Vector3d max_point(
        std::numeric_limits<double>::lowest(),
        std::numeric_limits<double>::lowest(),
        std::numeric_limits<double>::lowest()
    );
    
    for (const auto& tri : triangles) {
        for (const auto& v : tri.vertices) {
            min_point.x = std::min(min_point.x, v.x);
            min_point.y = std::min(min_point.y, v.y);
            min_point.z = std::min(min_point.z, v.z);
            
            max_point.x = std::max(max_point.x, v.x);
            max_point.y = std::max(max_point.y, v.y);
            max_point.z = std::max(max_point.z, v.z);
        }
    }
    
    Vector3d center(
        (min_point.x + max_point.x) / 2.0,
        (min_point.y + max_point.y) / 2.0,
        (min_point.z + max_point.z) / 2.0
    );
    double size = std::max(std::max(max_point.x - min_point.x, max_point.y - min_point.y), max_point.z - min_point.z) * 1.01; // 稍微扩大一点
    
    // 构建八叉树
    vector<int> all_indices(num_faces);
    for (size_t i = 0; i < num_faces; ++i) {
        all_indices[i] = i;
    }
    
    auto octree = build_octree(triangles, all_indices, center, size, 0, 8, 20);
    
    // 用于存储相交的面片
    set<int> intersecting_faces;
    
    // 添加相交关系映射
    map<int, set<int>> intersection_map;
    
    // 递归查询八叉树
    function<void(const shared_ptr<OctreeNode>&, int)> query_octree;
    query_octree = [&](const shared_ptr<OctreeNode>& node, int face_idx) {
        // 如果节点为空，直接返回
        if (!node) {
            return;
        }
        
        // 如果节点是叶子节点，检查所有面片
        if (all_of(node->children.begin(), node->children.end(), 
                  [](const auto& child) { return child == nullptr; })) {
            const Triangle& tri1 = triangles[face_idx];
            const AABB& bbox1 = face_bboxes[face_idx];
            
            for (int other_idx : node->face_indices) {
                // 跳过自身
                if (other_idx == face_idx) {
                    continue;
                }
                
                // 快速AABB包围盒检测
                const AABB& bbox2 = face_bboxes[other_idx];
                if (bbox1.intersects(bbox2)) {
                    const Triangle& tri2 = triangles[other_idx];
                    
                    // 检查三角形顶点是否共享
                    bool share_vertex = false;
                    for (int i = 0; i < 3 && !share_vertex; ++i) {
                        for (int j = 0; j < 3 && !share_vertex; ++j) {
                            const Vector3d& v1 = tri1.vertices[i];
                            const Vector3d& v2 = tri2.vertices[j];
                            double dist = std::sqrt(
                                (v1.x - v2.x) * (v1.x - v2.x) +
                                (v1.y - v2.y) * (v1.y - v2.y) +
                                (v1.z - v2.z) * (v1.z - v2.z)
                            );
                            if (dist < EPSILON) {
                                share_vertex = true;
                            }
                        }
                    }
                    
                    // 只有当两个面片不共享顶点时才检查相交
                    if (!share_vertex && check_triangle_intersection(tri1, tri2)) {
                        // 记录相交面
                        intersecting_faces.insert(face_idx);
                        intersecting_faces.insert(other_idx);
                        
                        // 记录相交关系
                        if (intersection_map.find(face_idx) == intersection_map.end()) {
                            intersection_map[face_idx] = set<int>();
                        }
                        if (intersection_map.find(other_idx) == intersection_map.end()) {
                            intersection_map[other_idx] = set<int>();
                        }
                        
                        intersection_map[face_idx].insert(other_idx);
                        intersection_map[other_idx].insert(face_idx);
                    }
                }
            }
            return;
        }
        
        // 否则，递归查询子节点
        const AABB& face_bbox = face_bboxes[face_idx];
        double half_size = node->size / 2.0;
        
        for (int i = 0; i < 8; ++i) {
            if (!node->children[i]) {
                continue;
            }
            
            // 计算子节点的包围盒
            Vector3d child_center = node->center;
            if (i & 1) child_center.x += half_size; else child_center.x -= half_size;
            if (i & 2) child_center.y += half_size; else child_center.y -= half_size;
            if (i & 4) child_center.z += half_size; else child_center.z -= half_size;
            
            Vector3d child_min(
                child_center.x - half_size,
                child_center.y - half_size,
                child_center.z - half_size
            );
            Vector3d child_max(
                child_center.x + half_size,
                child_center.y + half_size,
                child_center.z + half_size
            );
            AABB child_bbox(child_min, child_max);
            
            // 检查面片的包围盒是否与子节点的包围盒相交
            if (face_bbox.intersects(child_bbox)) {
                query_octree(node->children[i], face_idx);
            }
        }
    };
    
    // 对每个面片，在八叉树中查询可能相交的面片
    for (size_t face_idx = 0; face_idx < num_faces; ++face_idx) {
        query_octree(octree, face_idx);
    }
    
    // 计算经过的时间
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end - start;
    
    // 转换为向量
    vector<int> result(intersecting_faces.begin(), intersecting_faces.end());
    
    // 转换相交映射为向量格式
    map<int, vector<int>> result_map;
    for (const auto& pair : intersection_map) {
        result_map[pair.first] = vector<int>(pair.second.begin(), pair.second.end());
    }
    
    // 返回结果tuple：相交面列表、相交关系映射和计算时间
    return std::make_tuple(result, result_map, elapsed.count());
}

PYBIND11_MODULE(pierced_faces_cpp, m) {
    m.doc() = "C++ implementation of pierced faces detection";
    m.def(
        "detect_pierced_faces_with_timing", 
        &detect_pierced_faces_with_timing, 
        "Detect pierced faces and return intersection indices and map with timing",
        py::arg("faces"), 
        py::arg("vertices")
    );
} 