# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_dynamic_libs
from PyInstaller.utils.hooks import collect_all

datas = [('worker_entry.py', '.'), ('function', 'function'), ('ui', 'ui')]
binaries = []
hiddenimports = ['billiard', 'billiard.pool', 'billiard.connection', 'billiard.managers', 'billiard.synchronize', 'billiard.heap', 'billiard.queues', 'billiard.process', 'billiard.socket', 'billiard.forking', 'billiard.spawn', 'billiard.util', 'billiard.compat', 'multiprocessing', 'multiprocessing.pool', 'multiprocessing.managers', 'multiprocessing.synchronize', 'multiprocessing.heap', 'multiprocessing.queues', 'multiprocessing.process', 'multiprocessing.socket', 'multiprocessing.forking', 'multiprocessing.spawn', 'multiprocessing.util', 'multiprocessing.compat', 'function', 'ui', 'worker_threads', 'worker_entry']
binaries += collect_dynamic_libs('worker_threads_cy')
binaries += collect_dynamic_libs('numpy.core._multiarray_umath')
binaries += collect_dynamic_libs('numpy.core._multiarray_tests')
binaries += collect_dynamic_libs('numpy.linalg._umath_linalg')
binaries += collect_dynamic_libs('numpy.fft._pocketfft_internal')
binaries += collect_dynamic_libs('numpy.random._common')
binaries += collect_dynamic_libs('numpy.random._bounded_integers')
binaries += collect_dynamic_libs('numpy.random._mt19937')
binaries += collect_dynamic_libs('numpy.random._philox')
binaries += collect_dynamic_libs('numpy.random._pcg64')
binaries += collect_dynamic_libs('numpy.random._sfc64')
binaries += collect_dynamic_libs('numpy.random._generator')
tmp_ret = collect_all('numpy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pandas')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PyQt5')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('billiard')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('psutil')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('worker_threads_cy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
