from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np
import platform

# 根据操作系统选择不同的编译选项
if platform.system() == 'Windows':
    extra_compile_args = ['/openmp']
    extra_link_args = ['/openmp']
else:
    extra_compile_args = ['-fopenmp']
    extra_link_args = ['-fopenmp']

ext_modules = [
    Extension(
        "worker_threads_cy",
        ["worker_threads_cy.pyx"],
        include_dirs=[np.get_include()],
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
        language='c++'
    )
]

setup(
    ext_modules=cythonize(ext_modules, compiler_directives={
        'language_level': "3",
        'boundscheck': False,
        'wraparound': False,
        'cdivision': True,
        'initializedcheck': False
    })
)