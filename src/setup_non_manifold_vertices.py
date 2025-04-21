from setuptools import setup, Extension
import pybind11
import os

# 获取 setup.py 所在的目录
setup_dir = os.path.dirname(os.path.abspath(__file__))

# 定义C++扩展模块
ext_modules = [
    Extension(
        "non_manifold_vertices_cpp",
        [os.path.join(setup_dir, "non_manifold_vertices_detector.cpp")],
        include_dirs=[pybind11.get_include()],
        language="c++",
    ),
]

setup(
    name="non_manifold_vertices_cpp",
    version="0.0.1",
    author="Your Name",
    author_email="your.email@example.com",
    description="非流形顶点检测C++实现",
    ext_modules=ext_modules,
    install_requires=["pybind11>=2.4.3"],
    python_requires=">=3.6",
) 