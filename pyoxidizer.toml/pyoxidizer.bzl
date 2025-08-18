# This file defines how PyOxidizer application building and packaging is
# performed. See PyOxidizer's documentation at
# https://gregoryszorc.com/docs/pyoxidizer/stable/pyoxidizer.html for details
# of this configuration file format.

# Configuration files consist of functions which define build "targets."
# This function creates a Python executable and installs it in a destination
# directory.
def make_exe():
    # Obtain the default PythonDistribution for our build target. We link
    # this distribution into our produced executable and extract the Python
    # standard library from it.
    dist = default_python_distribution()

    # This function creates a `PythonPackagingPolicy` instance, which
    # influences how executables are built and how resources are added to
    # the executable. You can customize the default behavior by assigning
    # to attributes and calling functions.
    policy = dist.make_python_packaging_policy()

    # Enable support for non-classified "file" resources to be added to
    # resource collections.
    policy.allow_files = True

    # Control support for loading Python extensions and other shared libraries
    # from memory. This is only supported on Windows and is ignored on other
    # platforms.
    policy.allow_in_memory_shared_library_loading = True

    # Control whether to generate Python bytecode at various optimization
    # levels. The default optimization level used by Python is 0.
    policy.bytecode_optimize_level_zero = True

    # Package all available Python extensions in the distribution.
    policy.extension_module_filter = "all"

    # Toggle whether Python module source code for modules in the Python
    # distribution's standard library are included.
    policy.include_distribution_sources = False

    # Toggle whether Python package resource files for the Python
    # standard library are included.
    policy.include_distribution_resources = False

    # Controls the `add_include` attribute of `File` resources.
    policy.include_file_resources = True

    # Controls the `add_include` attribute of `PythonModuleSource` not in
    # the standard library.
    policy.include_non_distribution_sources = True

    # Toggle whether files associated with tests are included.
    policy.include_test = False

    # Use filesystem-relative location for adding resources by default.
    # This is important for multiprocessing support
    policy.resources_location = "filesystem-relative:prefix"

    # Attempt to add resources relative to the built binary when
    # `resources_location` fails.
    policy.resources_location_fallback = "filesystem-relative:prefix"

    # Create a PythonExecutable from a PythonDistribution, applying
    # the packaging policy to determine what resources to include in
    # the executable and where to store them.
    exe = dist.to_python_executable(
        name = "stock_analysis",
        packaging_policy = policy,
    )

    # Add Python modules from the current directory
    exe.add_python_resources(exe.read_package_root(
        path = "..",
        packages = ["function", "ui", "worker_threads"],
    ))
    
    # Add individual Python files
    exe.add_python_resources(exe.read_package_root(
        path = "..",
        packages = ["main", "eastmoney_api", "process_stock_data", "runtime_hook"],
    ))
    
    # Add required packages using pip install
    exe.add_python_resources(exe.pip_install(["numpy", "pandas", "PyQt5", "billiard", "psutil"]))
    
    # 添加运行时钩子，确保多进程正常工作
    exe.add_python_resources(exe.read_package_root(
        path = "..",
        packages = ["runtime_hook_multiprocessing"],
    ))
    
    # 设置环境变量，确保多进程支持
    exe.add_python_resources(exe.read_package_root(
        path = "..",
        packages = ["runtime_hook"],
    ))
    
    # 添加Cython编译的模块
    if exe.read_file(path = "../worker_threads_cy.pyd"):
        exe.add_python_resources(exe.read_file(path = "../worker_threads_cy.pyd"))
    
    # 设置启动脚本，确保多进程环境正确初始化
    exe.add_python_resources(exe.read_package_root(
        path = "..",
        packages = ["main"],
    ))
    
    # Install the executable into a destination directory.
    return exe

# Tell PyOxidizer to never attempt to copy files from the source tree.
# This is important for multiprocessing support
def make_embedded_resources(exe):
    return exe.to_embedded_resources()

# Tell PyOxidizer to never attempt to copy files from the source tree.
# This is important for multiprocessing support
def make_install(exe):
    # Create an object that represents the installed application file layout.
    files = FileManifest()
    
    # Add the generated executable to the file manifest. The exe must be built
    # before we can install it.
    exe = exe.build()
    files.add_python_resource(".", exe)
    
    # 添加必要的运行时文件
    files.add_file("runtime_hook.py", exe.read_file(path = "../runtime_hook.py"))
    files.add_file("runtime_hook_multiprocessing.py", exe.read_file(path = "../runtime_hook_multiprocessing.py"))
    
    return files

# Tell PyOxidizer about the build targets defined above.
register_target("exe", make_exe)
register_target("resources", make_embedded_resources, depends=["exe"], default_build_script=True)
register_target("install", make_install, depends=["exe"], default=True)

# Resolve whatever targets the invoker of this configuration file is requesting
# be resolved.
resolve_targets()
