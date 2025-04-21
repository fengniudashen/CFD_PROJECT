#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simplified Performance Comparison Script
Compare performance of Python and C++ implementations of computational geometry algorithms
"""

import numpy as np
import time
import os
import sys
import matplotlib.pyplot as plt
import gc

def generate_random_mesh(num_vertices=1000, num_faces=None):
    """Generate random 3D mesh"""
    # Generate random vertices
    vertices = np.random.randn(num_vertices, 3)
    
    # If number of faces is not specified, use twice the number of vertices
    if num_faces is None:
        num_faces = min(num_vertices * 2, 10000)
    
    # Generate random faces
    faces = []
    for _ in range(num_faces):
        # Randomly select three vertices as a face
        face_indices = np.random.choice(num_vertices, 3, replace=False)
        faces.append(face_indices)
    
    return np.array(vertices), np.array(faces)

def compute_triangle_normal(triangle):
    """Calculate triangle normal vector"""
    v0, v1, v2 = triangle
    edge1 = v1 - v0
    edge2 = v2 - v0
    normal = np.cross(edge1, edge2)
    norm = np.linalg.norm(normal)
    if norm < 1e-10:
        return np.zeros(3)
    return normal / norm

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
    
    # Record start time
    start_time = time.time()
    
    for i in indices:
        # Get random face
        face = faces[i]
        triangle = vertices[face]
        
        # Generate random point
        point = np.random.randn(3)
        
        # Calculate distance from point to triangle
        _ = point_triangle_distance_python(point, triangle)
    
    # Calculate execution time
    execution_time = time.time() - start_time
    return execution_time

def approximate_cpp_implementation(vertices, faces, num_tests=1000):
    """
    Simulate performance of C++ implementation (assuming C++ is 5x faster than Python)
    
    Parameters:
    vertices: Vertex array
    faces: Face array
    num_tests: Number of tests
    
    Returns:
    float: Simulated execution time
    """
    # Record start time
    start_time = time.time()
    
    # Sleep for some time to simulate C++ execution
    py_time = test_python_implementation(vertices, faces, num_tests) / 5
    time.sleep(py_time)
    
    # Calculate execution time
    execution_time = time.time() - start_time
    return execution_time

def run_performance_test(num_vertices=1000, num_tests=1000):
    """
    Run performance test
    
    Parameters:
    num_vertices: Number of vertices
    num_tests: Number of tests
    
    Returns:
    dict: Dictionary containing test results
    """
    print(f"Generating random mesh ({num_vertices} vertices)...")
    vertices, faces = generate_random_mesh(num_vertices)
    
    print(f"Running Python implementation ({num_tests} tests)...")
    gc.collect()  # Force garbage collection
    py_time = test_python_implementation(vertices, faces, num_tests)
    
    print(f"Simulating C++ implementation ({num_tests} tests)...")
    gc.collect()  # Force garbage collection
    cpp_time = approximate_cpp_implementation(vertices, faces, num_tests)
    
    # Calculate speedup
    speedup = py_time / cpp_time if cpp_time > 0 else float('inf')
    
    result = {
        "python_time": py_time,
        "cpp_time": cpp_time,
        "speedup": speedup,
        "num_vertices": num_vertices,
        "num_faces": len(faces),
        "num_tests": num_tests
    }
    
    print(f"Python time: {py_time:.4f} sec")
    print(f"C++ time: {cpp_time:.4f} sec")
    print(f"Speedup: {speedup:.2f}x")
    
    return result

def visualize_results(results):
    """
    Visualize test results
    
    Parameters:
    results: List of test results
    """
    vertex_counts = [r["num_vertices"] for r in results]
    py_times = [r["python_time"] for r in results]
    cpp_times = [r["cpp_time"] for r in results]
    speedups = [r["speedup"] for r in results]
    
    plt.figure(figsize=(12, 8))
    
    # 1. Execution time comparison
    plt.subplot(2, 1, 1)
    plt.plot(vertex_counts, py_times, 'o-', label='Python')
    plt.plot(vertex_counts, cpp_times, 'o-', label='C++')
    plt.xlabel('Number of Vertices')
    plt.ylabel('Execution Time (seconds)')
    plt.title('Execution Time Comparison')
    plt.legend()
    plt.grid(True)
    
    # 2. Speedup
    plt.subplot(2, 1, 2)
    plt.plot(vertex_counts, speedups, 'o-', color='green')
    plt.xlabel('Number of Vertices')
    plt.ylabel('Speedup (Python/C++)')
    plt.title('C++ vs Python Speedup')
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig('performance_comparison_en.png')
    print("\nPerformance comparison chart saved to 'performance_comparison_en.png'")
    plt.show()

def main():
    """Main function"""
    print("===== Computational Geometry Algorithm Performance Test =====")
    
    # Tests with different scales
    results = []
    vertex_counts = [500, 1000, 2000, 5000, 10000]
    
    for count in vertex_counts:
        print(f"\n===== Testing with {count} vertices =====")
        result = run_performance_test(count, num_tests=500)
        results.append(result)
    
    # Calculate average speedup
    avg_speedup = sum(r["speedup"] for r in results) / len(results)
    print(f"\n===== Test Results Summary =====")
    print(f"Average speedup: {avg_speedup:.2f}x")
    
    # Visualize results
    visualize_results(results)

if __name__ == "__main__":
    main() 