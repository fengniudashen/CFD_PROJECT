import os
import platform
import sys
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext

class get_pybind_include(object):
    """Helper class to determine the pybind11 include path
    The purpose of this class is to postpone importing pybind11
    until it is actually installed, so that the ``get_include()``
    method can be invoked. """

    def __init__(self, user=False):
        self.user = user

    def __str__(self):
        import pybind11
        return pybind11.get_include(self.user)

ext_modules = [
    Extension(
        'overlapping_edges_cpp',
        ['overlapping_edges_detector.cpp'],
        include_dirs=[
            get_pybind_include(),
            get_pybind_include(user=True)
        ],
        language='c++'
    ),
]

class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""
    c_opts = {
        'msvc': ['/EHsc'],
        'unix': [],
    }

    if platform.system() == 'Windows':
        if sys.version_info.major == 3 and sys.version_info.minor >= 5:
            c_opts['msvc'].append('/O2')
    else:
        c_opts['unix'].append('-O3')
        c_opts['unix'].append('-std=c++11')

    def build_extensions(self):
        ct = self.compiler.compiler_type
        opts = self.c_opts.get(ct, [])
        for ext in self.extensions:
            ext.extra_compile_args = opts
        build_ext.build_extensions(self)

setup(
    name='overlapping_edges_cpp',
    version='0.1.0',
    author='Your Name',
    author_email='your.email@example.com',
    description='C++ implementation of overlapping edges detection algorithm',
    ext_modules=ext_modules,
    cmdclass={'build_ext': BuildExt},
    zip_safe=False,
) 