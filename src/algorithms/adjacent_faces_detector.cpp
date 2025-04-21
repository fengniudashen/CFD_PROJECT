#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <vector>
#include <array>
#include <cmath>
#include <set>
#include <map>
#include <tuple>
#include <chrono>
#include <iostream>

namespace py = pybind11;
using namespace std;

// Vector3d - 3D vector structure
struct Vector3d {
    double x, y, z;
    
    Vector3d() : x(0), y(0), z(0) {}
    Vector3d(double x, double y, double z) : x(x), y(y), z(z) {}
    
    double norm() const {
        return sqrt(x*x + y*y + z*z);
    }
    
    Vector3d operator-(const Vector3d& v) const {
        return Vector3d(x - v.x, y - v.y, z - v.z);
    }
    
    Vector3d operator+(const Vector3d& v) const {
        return Vector3d(x + v.x, y + v.y, z + v.z);
    }
    
    Vector3d operator*(double s) const {
        return Vector3d(x * s, y * s, z * s);
    }
    
    Vector3d operator/(double s) const {
        if (s == 0) return Vector3d();
        return Vector3d(x / s, y / s, z / s);
    }
    
    double dot(const Vector3d& v) const {
        return x * v.x + y * v.y + z * v.z;
    }
    
    Vector3d cross(const Vector3d& v) const {
        return Vector3d(y * v.z - z * v.y, z * v.x - x * v.z, x * v.y - y * v.x);
    }
};

// Triangle structure
struct Triangle {
    array<Vector3d, 3> vertices;
    
    Triangle(const Vector3d& v0, const Vector3d& v1, const Vector3d& v2) {
        vertices = {v0, v1, v2};
    }
    
    Vector3d centroid() const {
        return (vertices[0] + vertices[1] + vertices[2]) / 3.0;
    }
    
    double average_edge_length() const {
        double e1 = (vertices[1] - vertices[0]).norm();
        double e2 = (vertices[2] - vertices[1]).norm();
        double e3 = (vertices[0] - vertices[2]).norm();
        return (e1 + e2 + e3) / 3.0;
    }
    
    Vector3d normal() const {
        Vector3d v1 = vertices[1] - vertices[0];
        Vector3d v2 = vertices[2] - vertices[0];
        Vector3d n = v1.cross(v2);
        double len = n.norm();
        if (len > 1e-10) {
            return n / len;
        }
        return n;
    }
};

// AABB - Axis-Aligned Bounding Box
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

// Calculate distance from point to segment
double point_segment_distance(const Vector3d& p, const Vector3d& a, const Vector3d& b) {
    Vector3d ab = b - a;
    Vector3d ap = p - a;
    
    double ab_length_squared = ab.dot(ab);
    
    if (ab_length_squared < 1e-10) {
        return (p - a).norm();
    }
    
    double t = ap.dot(ab) / ab_length_squared;
    t = max(0.0, min(1.0, t));
    
    Vector3d projection = a + ab * t;
    
    return (p - projection).norm();
}

// Calculate minimum distance from point to triangle
double point_triangle_distance(const Vector3d& p, const Triangle& tri) {
    Vector3d normal = tri.normal();
    
    Vector3d v0_to_p = p - tri.vertices[0];
    double dist_to_plane = abs(v0_to_p.dot(normal));
    
    Vector3d projection = p - normal * dist_to_plane;
    
    Vector3d v0 = tri.vertices[0];
    Vector3d v1 = tri.vertices[1];
    Vector3d v2 = tri.vertices[2];
    
    Vector3d v0v1 = v1 - v0;
    Vector3d v0v2 = v2 - v0;
    Vector3d v0p = projection - v0;
    
    double d00 = v0v1.dot(v0v1);
    double d01 = v0v1.dot(v0v2);
    double d11 = v0v2.dot(v0v2);
    double d20 = v0p.dot(v0v1);
    double d21 = v0p.dot(v0v2);
    
    double denom = d00 * d11 - d01 * d01;
    if (abs(denom) < 1e-10) {
        double min_dist = min(
            point_segment_distance(p, v0, v1),
            min(point_segment_distance(p, v1, v2), 
                point_segment_distance(p, v2, v0))
        );
        return min_dist;
    }
    
    double v = (d11 * d20 - d01 * d21) / denom;
    double w = (d00 * d21 - d01 * d20) / denom;
    double u = 1.0 - v - w;
    
    if (u >= 0 && v >= 0 && w >= 0) {
        return dist_to_plane;
    } else {
        double dist_edge1 = point_segment_distance(p, v0, v1);
        double dist_edge2 = point_segment_distance(p, v1, v2);
        double dist_edge3 = point_segment_distance(p, v2, v0);
        
        return min(dist_edge1, min(dist_edge2, dist_edge3));
    }
}

// Ray-triangle intersection test using Moller-Trumbore algorithm
bool ray_triangle_intersect(const Vector3d& ray_origin, const Vector3d& ray_dir, 
                           const Triangle& tri, double& t, double& u, double& v) {
    const double EPSILON = 1e-10;
    
    Vector3d v0 = tri.vertices[0];
    Vector3d v1 = tri.vertices[1];
    Vector3d v2 = tri.vertices[2];
    
    Vector3d edge1 = v1 - v0;
    Vector3d edge2 = v2 - v0;
    Vector3d h = ray_dir.cross(edge2);
    double a = edge1.dot(h);
    
    if (a > -EPSILON && a < EPSILON) {
        return false;
    }
    
    double f = 1.0 / a;
    Vector3d s = ray_origin - v0;
    u = f * s.dot(h);
    
    if (u < 0.0 || u > 1.0) {
        return false;
    }
    
    Vector3d q = s.cross(edge1);
    v = f * ray_dir.dot(q);
    
    if (v < 0.0 || u + v > 1.0) {
        return false;
    }
    
    t = f * edge2.dot(q);
    
    return (t > EPSILON);
}

// Check if two triangles intersect
bool triangles_intersect(const Triangle& t1, const Triangle& t2) {
    for (int i = 0; i < 3; i++) {
        Vector3d edge_start = t1.vertices[i];
        Vector3d edge_end = t1.vertices[(i + 1) % 3];
        Vector3d edge_dir = edge_end - edge_start;
        double edge_length = edge_dir.norm();
        
        if (edge_length < 1e-10) continue;
        
        edge_dir = edge_dir / edge_length;
        
        double t, u, v;
        if (ray_triangle_intersect(edge_start, edge_dir, t2, t, u, v)) {
            if (t <= edge_length) {
                return true;
            }
        }
    }
    
    for (int i = 0; i < 3; i++) {
        Vector3d edge_start = t2.vertices[i];
        Vector3d edge_end = t2.vertices[(i + 1) % 3];
        Vector3d edge_dir = edge_end - edge_start;
        double edge_length = edge_dir.norm();
        
        if (edge_length < 1e-10) continue;
        
        edge_dir = edge_dir / edge_length;
        
        double t, u, v;
        if (ray_triangle_intersect(edge_start, edge_dir, t1, t, u, v)) {
            if (t <= edge_length) {
                return true;
            }
        }
    }
    
    return false;
}

// Compute AABB for a triangle
AABB compute_triangle_aabb(const Triangle& tri) {
    Vector3d min_point(
        std::numeric_limits<double>::max(),
        std::numeric_limits<double>::max(),
        std::numeric_limits<double>::max()
    );
    Vector3d max_point(
        -std::numeric_limits<double>::max(),
        -std::numeric_limits<double>::max(),
        -std::numeric_limits<double>::max()
    );
    
    for (const auto& v : tri.vertices) {
        min_point.x = std::min(min_point.x, v.x);
        min_point.y = std::min(min_point.y, v.y);
        min_point.z = std::min(min_point.z, v.z);
        
        max_point.x = std::max(max_point.x, v.x);
        max_point.y = std::max(max_point.y, v.y);
        max_point.z = std::max(max_point.z, v.z);
    }
    
    return AABB(min_point, max_point);
}

// Main algorithm to detect adjacent faces
tuple<vector<pair<int, int>>, double> detect_adjacent_faces(
    py::array_t<float> vertices_array,
    py::array_t<int> faces_array,
    double proximity_threshold) {
    
    auto start_time = chrono::high_resolution_clock::now();
    
    py::buffer_info vertices_info = vertices_array.request();
    py::buffer_info faces_info = faces_array.request();
    
    if (vertices_info.ndim != 2 || vertices_info.shape[1] != 3) {
        throw runtime_error("Vertices array must be a 2D array with shape (n, 3)");
    }
    
    if (faces_info.ndim != 2 || faces_info.shape[1] != 3) {
        throw runtime_error("Faces array must be a 2D array with shape (m, 3)");
    }
    
    float* vertices_ptr = static_cast<float*>(vertices_info.ptr);
    int* faces_ptr = static_cast<int*>(faces_info.ptr);
    
    size_t num_vertices = vertices_info.shape[0];
    size_t num_faces = faces_info.shape[0];
    
    vector<Vector3d> vertices(num_vertices);
    for (size_t i = 0; i < num_vertices; ++i) {
        vertices[i] = Vector3d(vertices_ptr[i * 3], vertices_ptr[i * 3 + 1], vertices_ptr[i * 3 + 2]);
    }
    
    vector<pair<int, int>> adjacent_pairs;
    adjacent_pairs.reserve(num_faces);

    for (size_t i = 0; i < num_faces; ++i) {
        int idx1 = faces_ptr[i * 3];
        int idx2 = faces_ptr[i * 3 + 1];
        int idx3 = faces_ptr[i * 3 + 2];
        
        if (idx1 < 0 || idx1 >= num_vertices || idx2 < 0 || idx2 >= num_vertices || idx3 < 0 || idx3 >= num_vertices) {
            cerr << "Warning: Face " << i << " has invalid vertex indices. Skipping." << endl;
            continue;
        }
        
        Vector3d v1 = vertices[idx1];
        Vector3d v2 = vertices[idx2];
        Vector3d v3 = vertices[idx3];
        Triangle current_tri(v1, v2, v3);

        double avg_edge_len1 = current_tri.average_edge_length();
        Vector3d centroid1 = current_tri.centroid();

        for (size_t j = i + 1; j < num_faces; ++j) {
            int idx4 = faces_ptr[j * 3];
            int idx5 = faces_ptr[j * 3 + 1];
            int idx6 = faces_ptr[j * 3 + 2];
            
            if (idx4 < 0 || idx4 >= num_vertices || idx5 < 0 || idx5 >= num_vertices || idx6 < 0 || idx6 >= num_vertices) {
                cerr << "Warning: Face " << j << " has invalid vertex indices. Skipping comparison with face " << i << "." << endl;
                continue;
            }
            
            Vector3d v4 = vertices[idx4];
            Vector3d v5 = vertices[idx5];
            Vector3d v6 = vertices[idx6];
            Triangle other_tri(v4, v5, v6);

            double avg_edge_len2 = other_tri.average_edge_length();
            Vector3d centroid2 = other_tri.centroid();

            double centroid_dist = (centroid1 - centroid2).norm();

            double min_avg_edge_len = min(avg_edge_len1, avg_edge_len2);
            
            if (min_avg_edge_len < 1e-10) {
                if (centroid_dist < 1e-10) {
                    adjacent_pairs.push_back({static_cast<int>(i), static_cast<int>(j)});
                }
                continue;
            }

            double proximity = centroid_dist / min_avg_edge_len;

            if (proximity <= proximity_threshold) {
                adjacent_pairs.push_back({static_cast<int>(i), static_cast<int>(j)});
            }
        }
    }
    
    auto end_time = chrono::high_resolution_clock::now();
    chrono::duration<double> elapsed_seconds = end_time - start_time;

    return make_tuple(adjacent_pairs, elapsed_seconds.count());
}

// Interface function with timing
tuple<vector<pair<int, int>>, double> detect_adjacent_faces_with_timing(
    py::array_t<float> vertices,
    py::array_t<int> faces,
    double proximity_threshold = 0.5) {
    
    // Ensure input vertices are float32 as expected by some parts, but use double internally
    py::buffer_info vertices_info = vertices.request();
    if (vertices_info.format != py::format_descriptor<float>::format()) {
         throw std::runtime_error("Input vertices must be of type float32");
    }

    return detect_adjacent_faces(vertices, faces, proximity_threshold);
}

// Define Python module
PYBIND11_MODULE(adjacent_faces_cpp, m) {
    m.doc() = "C++ module for detecting adjacent faces based on proximity";
    
    m.def("detect_adjacent_faces_with_timing", &detect_adjacent_faces_with_timing,
          "Detects adjacent faces based on proximity threshold P = d / min(L_A, L_B)",
          py::arg("vertices"), py::arg("faces"), py::arg("proximity_threshold") = 0.5
    );
} 