cmake_minimum_required(VERSION 3.10)
project(CFD_PROJECT)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(Eigen3 3.3 REQUIRED)
find_package(pybind11 REQUIRED)

# Add source files for the Python module
set(MODULE_SOURCES
    src/mesh_reader.cpp
    src/mesh_reader_py.cpp
)

# Create Python module directly from sources
pybind11_add_module(mesh_reader_cpp ${MODULE_SOURCES})

# Link libraries to the module
target_link_libraries(mesh_reader_cpp PRIVATE Eigen3::Eigen)

# Include directories for the module
target_include_directories(mesh_reader_cpp PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${EIGEN3_INCLUDE_DIR}
) 