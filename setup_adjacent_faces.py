from setuptools import setup, Extension
import pybind11
import sys

# 创建C++扩展
ext_module = Extension(
    'adjacent_faces_cpp',
    sources=['src/algorithms/adjacent_faces_detector.cpp'],
    include_dirs=[pybind11.get_include()],
    language='c++',
    extra_compile_args=['/std:c++17', '/O2'] if sys.platform.startswith('win') else ['-std=c++17', '-O3'],
)

# 设置模块信息
setup(
    name='adjacent_faces_cpp',
    version='0.1',
    ext_modules=[ext_module],
) 