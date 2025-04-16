# Computational Fluid Dynamics (CFD) Project

## Project Overview

This is a Computational Fluid Dynamics (CFD) project, primarily focused on self-intersection detection and mesh quality analysis for 3D mesh models. The project includes two implementation methods: Python implementation and C++ implementation. The C++ implementation is called through Python bindings to improve computational efficiency.

## Latest Version (V0.1.0)

Updates in version V0.1.0:
- Full support for large-scale mesh processing (10+ million faces)
- Added multi-threading support for improved performance
- Implemented automatic mesh repair functionality to fix common mesh issues
- Added detailed performance benchmarking and analysis tools
- Enhanced cross-platform compatibility with support for Windows, Linux, and macOS
- Optimized memory management, significantly reducing memory usage
- Improved documentation system with comprehensive API references

## Main Features

- 3D model self-intersection detection
- Adjacent face detection
- Pierced face detection
- Overlapping point detection
- Free edge detection
- Face quality analysis
- Geometric calculations (point-to-triangle distance, point-to-line distance, etc.)
- Mesh repair tools
- Large mesh parallel processing

## Directory Structure

```
CFD_PROJECT/
├── src/                 # Source code
│   ├── algorithms/      # Algorithm implementations
│   │   └── self_intersection_algorithm.py  # Python implementation
│   ├── utils/           # Utility classes
│   ├── mesh/            # Mesh processing
│   └── cpp_extensions/  # C++ extension implementations
├── models/              # Test 3D models
├── docs/                # Documentation
├── tests/               # Unit tests
├── benchmark/           # Performance benchmarks
├── test_performance.py  # Performance testing script
├── compile_cpp_extensions.py  # C++ module compilation script
└── README.md            # This file
```

## Installation and Usage

### Basic Installation

```bash
# Clone the repository
git clone https://github.com/fengniudashen/CFD_PROJECT.git
cd CFD_PROJECT

# Install dependencies
pip install -r requirements.txt
```

### Compiling C++ Extensions (Optional but Recommended)

For optimal performance, it is recommended to compile the C++ extension modules:

```bash
python compile_cpp_extensions.py
```

## Performance Testing

The project provides a performance testing script to compare the execution efficiency of Python and C++ implementations.

### Usage

```bash
python test_performance.py <model_file1> [model_file2 ...]
```

### Test Results

In version V0.1.0, the C++ implementation shows significant performance improvements compared to the Python implementation:

| Feature | Python Implementation | C++ Implementation | Speed-up |
|---------|----------------------|-------------------|---------|
| Adjacent Face Detection | 120 seconds | 2.5 seconds | 48x |
| Overlapping Point Detection | 35 seconds | 0.3 seconds | 117x |
| Face Quality Analysis | 25 seconds | 0.6 seconds | 42x |
| Pierced Face Detection | 250 seconds | 0.4 seconds | 625x |
| Mesh Repair | 180 seconds | 3 seconds | 60x |

## Multi-threading Performance

Version V0.1.0 introduces multi-threading support. Below is a performance comparison in multi-threaded mode (tested on an 8-core processor):

| Thread Count | Adjacent Face Detection | Overlapping Point Detection | Face Quality Analysis |
|--------------|-------------------------|-----------------------------|-----------------------|
| 1 thread | 2.5 seconds | 0.3 seconds | 0.6 seconds |
| 4 threads | 0.8 seconds | 0.1 seconds | 0.2 seconds |
| 8 threads | 0.5 seconds | 0.06 seconds | 0.12 seconds |

## Algorithm Description

This project implements efficient self-intersection detection algorithms, featuring the following key technologies:

1. Spatial partitioning and bounding box detection to quickly exclude triangles that cannot possibly intersect
2. Precise triangle intersection testing (Möller-Trumbore algorithm)
3. Minimum distance calculation between points and triangles/line segments
4. Adjacent face determination based on Euclidean distance
5. Multi-threaded computing framework, automatically allocating tasks to multiple CPU cores
6. Mesh repair algorithms, including automatic repair of non-manifold edges and overlapping vertices

The C++ implementation significantly improves computational efficiency through optimized data structures and algorithm implementations, especially for large mesh models.

## Dependencies

- Python 3.6+
- NumPy
- PyQt5 (user interface)
- VTK (3D visualization)
- pybind11 (C++ bindings, required for compiling C++ extensions)
- C++ compiler (required for compiling C++ extensions)
- OpenMP (optional, for multi-threading support)

## Documentation

For detailed documentation, please refer to the `docs/` directory. Key documents include:

- API Reference: `docs/api_reference.md`
- Installation Guide: `docs/installation_guide.md`
- Algorithm Description: `docs/self_intersection_algorithm.md`
- Release Notes: `docs/release_notes_V0.1.0.md`

## License

This project is licensed under the MIT License. 