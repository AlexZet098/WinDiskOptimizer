# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


def _analysis_for(script: str, console: bool, name: str):
    a = Analysis(
        [script],
        pathex=["src"],
        binaries=[],
        datas=[],
        hiddenimports=[
            "matplotlib.backends.backend_tkagg",
            "matplotlib.pyplot",
        ],
        hookspath=[],
        runtime_hooks=[],
        excludes=[],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
        cipher=block_cipher,
        noarchive=False,
    )
    pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=console,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,
    )
    return exe


gui_exe = _analysis_for("src/windiskoptimizer/gui.py", console=False, name="WinDiskOptimizer")
cli_exe = _analysis_for("src/windiskoptimizer/cli.py", console=True, name="WinDiskOptimizerCLI")
