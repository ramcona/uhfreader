import os
import sys
import shutil
import subprocess
import platform

def build_app():
    # Define the name of the application
    app_name = "RFID Reader"
    
    # Create a temporary directory for the build
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    
    # Determine the current operating system
    system = platform.system()
    
    # Create the spec file for PyInstaller
    spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['app.py'],
             pathex=[os.path.abspath(os.getcwd())],
             binaries=[],
             datas=[
                ('templates', 'templates'),
                ('static', 'static')
             ],
             hiddenimports=['engineio.async_drivers.threading'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
"""
    
    if system == "Darwin":  # macOS
        spec_content += f"""
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='{app_name}',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='{app_name}')
app = BUNDLE(coll,
             name='{app_name}.app',
             icon='./icons/logo.icns',
             bundle_identifier='uhfreader.rafli',
             info_plist={{'NSHighResolutionCapable': 'True'}})
"""
    elif system == "Windows":  # Windows
        spec_content += f"""
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='{app_name}',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          icon='./icons/logo.ico',
          console=False )
"""
    
    # Write the spec file
    with open("app.spec", "w") as f:
        f.write(spec_content)
    
    # Run PyInstaller
    subprocess.run(["pyinstaller", "app.spec"], check=True)
    
    print(f"Build completed. The application is in the 'dist' folder.")

if __name__ == "__main__":
    build_app()