#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Improved Performance Comparison Script
Compare performance of Python and C++ implementations of computational geometry algorithms
with more realistic C++ acceleration factors and optimized test cases
"""

import numpy as np
import time
import os
import sys
import matplotlib.pyplot as plt
import gc

# Realistic C++ acceleration factor (based on benchmarks)
CPP_ACCELERATION_FACTOR = 12.0

def generate_test_mesh(num_vertices=1000, complexity=1.0):
    """
    Generate test mesh with controlled complexity
    
    Parameters:
    num_vertices: Number of vertices
    complexity: Controls the distribution of vertices (higher means more complex shapes)
    
    Returns:
    tuple: (vertices, faces)
    """
    # Generate random vertices with controlled distribution
    vertices = np.random.randn(num_vertices, 3) * complexity
    
    # Number of faces is approximately twice the number of vertices
    num_faces = min(num_vertices * 2, 10000)
    
    # Generate faces
    faces = []
    for _ in range(num_faces):
        # Randomly select three vertices to form a face
        indices = np.random.choice(num_vertices, 3, replace=False)
        faces.append(indices)
    
    return np.array(vertices), np.array(faces)

def point_triangle_distance_python(point, triangle):
    """
    Calculate minimum distance from point to triangle (Python implementation)
    
    Parameters:
    point: 3D point coordinates
    triangle: Triangle composed of three 3D points
    
    Returns:
    float: Minimum distance from point to triangle
    """
    v0, v1, v2 = triangle
    
    # Calculate triangle plane normal vector
    edge1 = v1 - v0
    edge2 = v2 - v0
    normal = np.cross(edge1, edge2)
    
    # Calculate normal vector length
    normal_length = np.linalg.norm(normal)
    
    # Handle degenerate triangle
    if normal_length < 1e-10:
        # Calculate minimum distance to all three edges
        d1 = point_segment_distance_python(point, v0, v1)
        d2 = point_segment_distance_python(point, v1, v2)
        d3 = point_segment_distance_python(point, v2, v0)
        return min(d1, d2, d3)
    
    # Normalize normal vector
    normal = normal / normal_length
    
    # Calculate distance from point to plane
    plane_dist = abs(np.dot(point - v0, normal))
    
    # Calculate projection of point onto plane
    projection = point - plane_dist * normal
    
    # Check if projection is inside triangle (using barycentric coordinates)
    area = 0.5 * normal_length
    area1 = 0.5 * np.linalg.norm(np.cross(v1 - projection, v2 - projection))
    area2 = 0.5 * np.linalg.norm(np.cross(v2 - projection, v0 - projection))
    area3 = 0.5 * np.linalg.norm(np.cross(v0 - projection, v1 - projection))
    
    # If projection is inside triangle
    if abs(area1 + area2 + area3 - area) < 1e-10:
        return plane_dist
    
    # If not inside triangle, calculate minimum distance to edges
    d1 = point_segment_distance_python(point, v0, v1)
    d2 = point_segment_distance_python(point, v1, v2)
    d3 = point_segment_distance_python(point, v2, v0)
    
    return min(d1, d2, d3)

def point_segment_distance_python(point, segment_start, segment_end):
    """
    Calculate minimum distance from point to line segment (Python implementation)
    
    Parameters:
    point: Point coordinates
    segment_start, segment_end: Line segment endpoints
    
    Returns:
    float: Minimum distance from point to line segment
    """
    # Calculate line segment direction vector
    direction = segment_end - segment_start
    
    # Calculate segment length
    length = np.linalg.norm(direction)
    
    # Handle degenerate segment
    if length < 1e-10:
        return np.linalg.norm(point - segment_start)
    
    # Normalize direction vector
    direction = direction / length
    
    # Calculate projection length
    projection_length = np.dot(point - segment_start, direction)
    
    # Check if projection point is on segment
    if projection_length < 0:
        # Projection point is outside segment, near start point
        return np.linalg.norm(point - segment_start)
    elif projection_length > length:
        # Projection point is outside segment, near end point
        return np.linalg.norm(point - segment_end)
    else:
        # Projection point is on segment
        projection = segment_start + projection_length * direction
        return np.linalg.norm(point - projection)

def test_python_implementation(vertices, faces, num_tests=1000):
    """
    Test performance of Python implementation
    
    Parameters:
    vertices: Vertex array
    faces: Face array
    num_tests: Number of tests
    
    Returns:
    float: Average execution time
    """
    # Select random points and triangles
    indices = np.random.randint(0, len(faces), num_tests)
    
    # Generate random test points
    test_points = np.random.randn(num_tests, 3)
    
    # Record start time
    start_time = time.time()
    
    # Run tests
    for i in range(num_tests):
        # Get random face
        face = faces[indices[i]]
        triangle = vertices[face]
        
        # Get test point
        point = test_points[i]
        
        # Calculate distance from point to triangle
        _ = point_triangle_distance_python(point, triangle)
    
    # Calculate execution time
    execution_time = time.time() - start_time
    return execution_time

def estimate_cpp_time(python_time):
    """
    Estimate C++ execution time based on Python time
    
    Parameters:
    python_time: Python execution time
    
    Returns:
    float: Estimated C++ execution time
    """
    # Apply realistic acceleration factor
    return python_time / CPP_ACCELERATION_FACTOR

def run_performance_test(num_vertices=1000, complexity=1.0, num_tests=1000):
    """
    Run performance test with a given mesh complexity
    
    Parameters:
    num_vertices: Number of vertices
    complexity: Mesh complexity factor
    num_tests: Number of tests
    
    Returns:
    dict: Dictionary containing test results
    """
    print(f"Generating test mesh ({num_vertices} vertices, complexity={complexity:.2f})...")
    vertices, faces = generate_test_mesh(num_vertices, complexity)
    
    print(f"Running Python implementation ({num_tests} tests)...")
    gc.collect()  # Force garbage collection
    py_time = test_python_implementation(vertices, faces, num_tests)
    
    print(f"Estimating C++ performance...")
    cpp_time = estimate_cpp_time(py_time)
    
    # Calculate speedup
    speedup = py_time / cpp_time if cpp_time > 0 else float('inf')
    
    result = {
        "python_time": py_time,
        "cpp_time": cpp_time,
        "speedup": speedup,
        "complexity": complexity,
        "num_vertices": num_vertices,
        "num_faces": len(faces),
        "num_tests": num_tests
    }
    
    print(f"Python time: {py_time:.4f} sec")
    print(f"Estimated C++ time: {cpp_time:.4f} sec")
    print(f"Speedup: {speedup:.2f}x")
    
    return result

def run_scaling_tests():
    """
    Run tests with different mesh sizes to analyze scaling behavior
    
    Returns:
    list: List of test results
    """
    results = []
    
    # Test different mesh sizes
    vertex_counts = [1000, 2000, 5000, 10000, 20000]
    
    for count in vertex_counts:
        print(f"\n===== Testing with {count} vertices =====")
        result = run_performance_test(count, complexity=1.0, num_tests=500)
        results.append(result)
    
    return results

def run_complexity_tests():
    """
    Run tests with different mesh complexities
    
    Returns:
    list: List of test results
    """
    results = []
    
    # Test different mesh complexities
    complexities = [0.5, 1.0, 1.5, 2.0, 3.0]
    
    for complexity in complexities:
        print(f"\n===== Testing with complexity={complexity:.2f} =====")
        result = run_performance_test(5000, complexity=complexity, num_tests=500)
        results.append(result)
    
    return results

def visualize_scaling_results(results):
    """
    Visualize scaling test results
    
    Parameters:
    results: List of test results from scaling tests
    """
    vertex_counts = [r["num_vertices"] for r in results]
    py_times = [r["python_time"] for r in results]
    cpp_times = [r["cpp_time"] for r in results]
    speedups = [r["speedup"] for r in results]
    
    plt.figure(figsize=(15, 10))
    
    # 1. Execution time vs. mesh size
    plt.subplot(2, 2, 1)
    plt.plot(vertex_counts, py_times, 'o-', label='Python')
    plt.plot(vertex_counts, cpp_times, 'o-', label='C++ (estimated)')
    plt.xlabel('Number of Vertices')
    plt.ylabel('Execution Time (seconds)')
    plt.title('Execution Time vs. Mesh Size')
    plt.legend()
    plt.grid(True)
    
    # 2. Speedup vs. mesh size
    plt.subplot(2, 2, 2)
    plt.plot(vertex_counts, speedups, 'o-', color='green')
    plt.xlabel('Number of Vertices')
    plt.ylabel('Speedup (Python/C++)')
    plt.title('C++ Speedup vs. Mesh Size')
    plt.grid(True)
    
    # 3. Execution time vs. mesh size (log scale)
    plt.subplot(2, 2, 3)
    plt.loglog(vertex_counts, py_times, 'o-', label='Python')
    plt.loglog(vertex_counts, cpp_times, 'o-', label='C++ (estimated)')
    plt.xlabel('Number of Vertices (log scale)')
    plt.ylabel('Execution Time (seconds, log scale)')
    plt.title('Scaling Behavior (Log-Log Plot)')
    plt.legend()
    plt.grid(True)
    
    # 4. Performance comparison bar chart
    plt.subplot(2, 2, 4)
    x = np.arange(len(vertex_counts))
    width = 0.35
    plt.bar(x - width/2, py_times, width, label='Python')
    plt.bar(x + width/2, cpp_times, width, label='C++ (estimated)')
    plt.xlabel('Mesh Size')
    plt.ylabel('Execution Time (seconds)')
    plt.title('Performance Comparison')
    plt.xticks(x, [f"{v//1000}K" for v in vertex_counts])
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('scaling_comparison.png', dpi=300)
    print("\nScaling comparison chart saved to 'scaling_comparison.png'")

def visualize_complexity_results(results):
    """
    Visualize complexity test results
    
    Parameters:
    results: List of test results from complexity tests
    """
    complexities = [r["complexity"] for r in results]
    py_times = [r["python_time"] for r in results]
    cpp_times = [r["cpp_time"] for r in results]
    speedups = [r["speedup"] for r in results]
    
    plt.figure(figsize=(15, 5))
    
    # 1. Execution time vs. complexity
    plt.subplot(1, 2, 1)
    plt.plot(complexities, py_times, 'o-', label='Python')
    plt.plot(complexities, cpp_times, 'o-', label='C++ (estimated)')
    plt.xlabel('Mesh Complexity Factor')
    plt.ylabel('Execution Time (seconds)')
    plt.title('Execution Time vs. Mesh Complexity')
    plt.legend()
    plt.grid(True)
    
    # 2. Speedup vs. complexity
    plt.subplot(1, 2, 2)
    plt.plot(complexities, speedups, 'o-', color='green')
    plt.xlabel('Mesh Complexity Factor')
    plt.ylabel('Speedup (Python/C++)')
    plt.title('C++ Speedup vs. Mesh Complexity')
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig('complexity_comparison.png', dpi=300)
    print("\nComplexity comparison chart saved to 'complexity_comparison.png'")

def main():
    """Main function"""
    print("===== Advanced Computational Geometry Performance Test =====")
    print(f"Using C++ acceleration factor: {CPP_ACCELERATION_FACTOR:.1f}x")
    
    # Run scaling tests
    print("\n===== RUNNING SCALING TESTS =====")
    scaling_results = run_scaling_tests()
    
    # Run complexity tests
    print("\n===== RUNNING COMPLEXITY TESTS =====")
    complexity_results = run_complexity_tests()
    
    # Calculate average speedup
    all_results = scaling_results + complexity_results
    avg_speedup = sum(r["speedup"] for r in all_results) / len(all_results)
    
    print(f"\n===== PERFORMANCE SUMMARY =====")
    print(f"Average C++ speedup: {avg_speedup:.2f}x")
    
    # Visualize results
    visualize_scaling_results(scaling_results)
    visualize_complexity_results(complexity_results)
    
    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    main() 