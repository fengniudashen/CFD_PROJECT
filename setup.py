from setuptools import setup, Extension
import pybind11
import sys

# Define compile arguments based on platform
# For Windows (MSVC compiler)
if sys.platform == 'win32':
    cpp_args = ['/std:c++17', '/Ox', '/EHsc'] # Use C++17, optimization, exception handling
# For other platforms (like Linux/macOS with g++/clang++)
else:
    cpp_args = ['-std=c++17', '-O3'] # Use C++17 and optimization

# Define the C++ extension module
sfc_module = Extension(
    'adjacent_faces_cpp',                         # Name of the module in Python
    ['src/algorithms/adjacent_faces_detector.cpp'], # List of source files
    include_dirs=[pybind11.get_include()],        # Include directory for Pybind11 headers
    language='c++',                               # Language is C++
    extra_compile_args=cpp_args,                  # Pass the platform-specific compile arguments
)

# Setup function call
setup(
    name='adjacent_faces_cpp',                     # Package name
    version='0.0.2',                               # Version (incremented)
    description='C++ module for detecting adjacent faces based on proximity P = d / min(L)',
    ext_modules=[sfc_module],                      # List of extensions to build
)

# Optional: Add clean command for convenience
# from setuptools.command.build_ext import build_ext
# class CleanBuildExt(build_ext):
#     def run(self):
#         super().run()
#         # Clean up build artifacts
#         # ... add cleanup logic if needed ...

# setup(
#     ...,
#     cmdclass={'build_ext': CleanBuildExt}
# ) 