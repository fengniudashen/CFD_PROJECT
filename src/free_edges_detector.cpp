#include <vector>
#include <unordered_map>
#include <algorithm>
#include <chrono>
#include <iostream>
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

namespace py = pybind11;

// EdgeHash - hash structure for edges
struct EdgeHash {
    size_t operator()(const std::pair<int, int>& edge) const {
        return std::hash<int>()(edge.first) ^ std::hash<int>()(edge.second);
    }
};

// Free edge detection function - C++ implementation
std::vector<std::pair<int, int>> detect_free_edges_cpp(
    const std::vector<std::vector<int>>& faces) {
    
    // Map to count occurrences of each edge
    std::unordered_map<std::pair<int, int>, int, EdgeHash> edge_count;
    
    // Process all faces to collect edge information
    for (const auto& face : faces) {
        // For triangular faces, process three edges
        if (face.size() >= 3) {
            // Get three edges (ensure smaller vertex index is first)
            std::pair<int, int> edge1 = {std::min(face[0], face[1]), std::max(face[0], face[1])};
            std::pair<int, int> edge2 = {std::min(face[1], face[2]), std::max(face[1], face[2])};
            std::pair<int, int> edge3 = {std::min(face[2], face[0]), std::max(face[2], face[0])};
            
            // Update edge counts
            edge_count[edge1]++;
            edge_count[edge2]++;
            edge_count[edge3]++;
        }
    }
    
    // Find edges that appear only once (free edges)
    std::vector<std::pair<int, int>> free_edges;
    for (const auto& edge_pair : edge_count) {
        if (edge_pair.second == 1) {
            free_edges.push_back(edge_pair.first);
        }
    }
    
    return free_edges;
}

// Free edge detection function with timing
std::pair<std::vector<std::pair<int, int>>, double> detect_free_edges_with_timing(
    const std::vector<std::vector<int>>& faces) {
    
    // Start timing
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Call detection function
    auto free_edges = detect_free_edges_cpp(faces);
    
    // End timing
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count() / 1000.0;
    
    return {free_edges, duration};
}

// Python module bindings
PYBIND11_MODULE(free_edges_cpp, m) {
    m.doc() = "C++ implementation of free edge detection algorithm";
    
    // Bind free edge detection function
    m.def("detect_free_edges", &detect_free_edges_cpp, 
          "Detect free edges in a mesh", py::arg("faces"));
    
    // Bind timed detection function
    m.def("detect_free_edges_with_timing", &detect_free_edges_with_timing,
          "Detect free edges and return execution time", py::arg("faces"));
} 