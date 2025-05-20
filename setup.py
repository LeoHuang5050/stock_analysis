from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np

ext_modules = [
    Extension(
        "worker_threads_cy",
        ["worker_threads_cy.pyx"],
        include_dirs=[np.get_include()],
        extra_compile_args=['-fopenmp'],
        extra_link_args=['-fopenmp'],
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