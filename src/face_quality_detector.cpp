/**
 * 面片质量检测器C++实现
 * 使用STAR-CCM+的面片质量算法
 */

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <vector>
#include <unordered_map>
#include <string>
#include <cmath>
#include <chrono>
#include <iostream>
#include <algorithm>

namespace py = pybind11;

/**
 * 计算单个三角形面片的质量
 * 使用STAR-CCM+的质量度量: quality = 2 * (r/R)
 * 其中r是内接圆半径，R是外接圆半径
 */
float calculate_face_quality(const std::vector<std::vector<float>>& vertices) {
    // 获取三个顶点
    const auto& v1 = vertices[0];
    const auto& v2 = vertices[1];
    const auto& v3 = vertices[2];
    
    // 计算三条边的长度
    float a = std::sqrt(std::pow(v2[0]-v3[0], 2) + std::pow(v2[1]-v3[1], 2) + std::pow(v2[2]-v3[2], 2));
    float b = std::sqrt(std::pow(v1[0]-v3[0], 2) + std::pow(v1[1]-v3[1], 2) + std::pow(v1[2]-v3[2], 2));
    float c = std::sqrt(std::pow(v1[0]-v2[0], 2) + std::pow(v1[1]-v2[1], 2) + std::pow(v1[2]-v2[2], 2));
    
    // 计算半周长
    float s = (a + b + c) / 2.0f;
    
    // 计算面积（使用海伦公式）
    float area = std::sqrt(std::max(0.0f, s * (s - a) * (s - b) * (s - c)));
    
    // 处理退化三角形
    if (area < 1e-10f) {
        return 0.0f;
    }
    
    // 计算内接圆半径
    float r = area / s;
    
    // 计算外接圆半径
    float R = (a * b * c) / (4.0f * area);
    
    // 计算STAR-CCM+质量度量
    float quality = std::min(1.0f, std::max(0.0f, 2.0f * (r / R)));
    
    return quality;
}

/**
 * 分析所有面片质量并返回低质量面片的索引
 */
std::tuple<std::vector<int>, std::unordered_map<std::string, py::object>, double> 
analyze_face_quality_with_timing(const py::array_t<float>& vertices_array, 
                               const py::array_t<int>& faces_array,
                               float threshold = 0.3f) {
    // 记录开始时间
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // 转换输入数组为C++类型
    auto vertices_buffer = vertices_array.unchecked<2>();
    auto faces_buffer = faces_array.unchecked<2>();
    
    // 获取顶点和面片数量
    py::ssize_t num_vertices = vertices_buffer.shape(0);
    py::ssize_t num_faces = faces_buffer.shape(0);
    
    // 结果容器
    std::vector<int> low_quality_faces;
    std::vector<float> quality_values;
    quality_values.reserve(num_faces);
    
    // 质量分布统计
    std::unordered_map<std::string, int> quality_distribution;
    quality_distribution["0.0-0.1"] = 0;
    quality_distribution["0.1-0.2"] = 0;
    quality_distribution["0.2-0.3"] = 0;
    quality_distribution["0.3-0.4"] = 0;
    quality_distribution["0.4-0.5"] = 0;
    quality_distribution["0.5-0.6"] = 0;
    quality_distribution["0.6-0.7"] = 0;
    quality_distribution["0.7-0.8"] = 0;
    quality_distribution["0.8-0.9"] = 0;
    quality_distribution["0.9-1.0"] = 0;
    
    // 分析每个面片
    for (py::ssize_t i = 0; i < num_faces; ++i) {
        // 获取面片的三个顶点索引
        int v1_idx = faces_buffer(i, 0);
        int v2_idx = faces_buffer(i, 1);
        int v3_idx = faces_buffer(i, 2);
        
        // 获取顶点坐标
        std::vector<std::vector<float>> face_vertices = {
            {vertices_buffer(v1_idx, 0), vertices_buffer(v1_idx, 1), vertices_buffer(v1_idx, 2)},
            {vertices_buffer(v2_idx, 0), vertices_buffer(v2_idx, 1), vertices_buffer(v2_idx, 2)},
            {vertices_buffer(v3_idx, 0), vertices_buffer(v3_idx, 1), vertices_buffer(v3_idx, 2)}
        };
        
        // 计算面片质量
        float quality = calculate_face_quality(face_vertices);
        quality_values.push_back(quality);
        
        // 更新质量分布
        if (quality < 0.1f) {
            quality_distribution["0.0-0.1"] += 1;
        } else if (quality < 0.2f) {
            quality_distribution["0.1-0.2"] += 1;
        } else if (quality < 0.3f) {
            quality_distribution["0.2-0.3"] += 1;
        } else if (quality < 0.4f) {
            quality_distribution["0.3-0.4"] += 1;
        } else if (quality < 0.5f) {
            quality_distribution["0.4-0.5"] += 1;
        } else if (quality < 0.6f) {
            quality_distribution["0.5-0.6"] += 1;
        } else if (quality < 0.7f) {
            quality_distribution["0.6-0.7"] += 1;
        } else if (quality < 0.8f) {
            quality_distribution["0.7-0.8"] += 1;
        } else if (quality < 0.9f) {
            quality_distribution["0.8-0.9"] += 1;
        } else {
            quality_distribution["0.9-1.0"] += 1;
        }
        
        // 检查是否低于阈值
        if (quality < threshold) {
            low_quality_faces.push_back(i);
        }
    }
    
    // 计算总体统计信息
    float min_quality = 1.0f;
    float max_quality = 0.0f;
    float avg_quality = 0.0f;
    
    if (!quality_values.empty()) {
        min_quality = *std::min_element(quality_values.begin(), quality_values.end());
        max_quality = *std::max_element(quality_values.begin(), quality_values.end());
        
        float sum = 0.0f;
        for (float q : quality_values) {
            sum += q;
        }
        avg_quality = sum / quality_values.size();
    }
    
    // 统计结果
    std::unordered_map<std::string, py::object> stats;
    stats["total_faces"] = py::cast(num_faces);
    stats["low_quality_faces"] = py::cast(low_quality_faces);
    stats["min_quality"] = py::cast(min_quality);
    stats["max_quality"] = py::cast(max_quality);
    stats["avg_quality"] = py::cast(avg_quality);
    
    // 转换质量分布为Python对象
    std::unordered_map<std::string, py::object> py_quality_distribution;
    for (const auto& kv : quality_distribution) {
        py_quality_distribution[kv.first] = py::cast(kv.second);
    }
    stats["quality_distribution"] = py::cast(py_quality_distribution);
    
    // 计算执行时间
    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end_time - start_time;
    double execution_time = elapsed.count();
    
    return std::make_tuple(low_quality_faces, stats, execution_time);
}

// 模块定义
PYBIND11_MODULE(face_quality_cpp, m) {
    m.doc() = "C++ implementation of face quality analysis";
    
    m.def("analyze_face_quality_with_timing", &analyze_face_quality_with_timing,
          "Analyze face quality and return low quality face indices, statistics and execution time",
          py::arg("vertices"), py::arg("faces"), py::arg("threshold") = 0.3f);
} 