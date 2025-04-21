"""
面片质量分析模块的编译脚本
"""

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import sys
import os

# 获取pybind11头文件位置
try:
    import pybind11
    pybind11_include = pybind11.get_include()
except ImportError:
    print("缺少pybind11库，请先安装: pip install pybind11")
    sys.exit(1)

# 根据不同的编译器调整编译参数
class get_pybind_include:
    def __init__(self, user=False):
        self.user = user

    def __str__(self):
        import pybind11
        return pybind11.get_include(self.user)

# 自定义构建扩展
class BuildExt(build_ext):
    c_opts = {
        'msvc': ['/EHsc', '/O2', '/std:c++14'],
        'unix': ['-O3', '-std=c++14', '-Wall', '-shared', '-fPIC'],
    }
    l_opts = {
        'msvc': [],
        'unix': [],
    }

    def build_extensions(self):
        ct = self.compiler.compiler_type
        opts = self.c_opts.get(ct, [])
        link_opts = self.l_opts.get(ct, [])
        
        # 根据平台添加特定选项
        if ct == 'unix':
            opts.append('-DVERSION_INFO="%s"' % self.distribution.get_version())
            opts.append('-std=c++14')
        elif ct == 'msvc':
            opts.append('/DVERSION_INFO=\\"%s\\"' % self.distribution.get_version())
        
        # 设置扩展模块的编译选项
        for ext in self.extensions:
            ext.extra_compile_args = opts
            ext.extra_link_args = link_opts
        
        build_ext.build_extensions(self)

# 定义C++扩展模块
face_quality_module = Extension(
    'face_quality_cpp',
    sources=['face_quality_detector.cpp'],
    include_dirs=[
        get_pybind_include(),
        get_pybind_include(user=True)
    ],
    language='c++'
)

# 配置setup
setup(
    name='face_quality_cpp',
    version='0.1.0',
    author='CFD Project',
    description='C++实现的面片质量分析算法',
    ext_modules=[face_quality_module],
    cmdclass={'build_ext': BuildExt},
    zip_safe=False,
) 