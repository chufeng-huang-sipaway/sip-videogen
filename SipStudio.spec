# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Sip Studio macOS app."""
import os
from pathlib import Path
block_cipher = None
# Project root
ROOT = Path(SPECPATH)
SRC = ROOT / 'src' / 'sip_studio'
STUDIO = SRC / 'studio'
FRONTEND_DIST = STUDIO / 'frontend' / 'dist'

# Collect all frontend files
frontend_datas = []
for root, dirs, files in os.walk(FRONTEND_DIST):
    for file in files:
        src_path = os.path.join(root, file)
        # Destination relative to frontend/dist
        rel_path = os.path.relpath(root, FRONTEND_DIST)
        dst_dir = os.path.join('frontend', 'dist', rel_path) if rel_path != '.' else os.path.join('frontend', 'dist')
        frontend_datas.append((src_path, dst_dir))

# Collect prompt files from agents
prompts_datas = []
prompts_dir = SRC / 'agents' / 'prompts'
if prompts_dir.exists():
    for prompt_file in prompts_dir.glob('*.md'):
        # Preserve package-relative path so runtime code can load via Path(__file__).parent / "prompts"
        prompts_datas.append((str(prompt_file), os.path.join('sip_studio', 'agents', 'prompts')))

# Collect brand agent prompts
brand_prompts_dir = SRC / 'brands' / 'prompts'
if brand_prompts_dir.exists():
    for prompt_file in brand_prompts_dir.glob('*.md'):
        prompts_datas.append((str(prompt_file), os.path.join('sip_studio', 'brands', 'prompts')))

# Collect advisor prompts
advisor_prompts_dir = SRC / 'advisor' / 'prompts'
if advisor_prompts_dir.exists():
    for prompt_file in advisor_prompts_dir.glob('*.md'):
        # Preserve package-relative path so runtime code can load via Path(__file__).parent / "prompts"
        prompts_datas.append((str(prompt_file), os.path.join('sip_studio', 'advisor', 'prompts')))

# Collect advisor skills (SKILL.md + any adjacent files) into package-relative path.
# These are required for Sip Studio's advisor skill-loading in the bundled .app.
advisor_skills_dir = SRC / 'advisor' / 'skills'
advisor_skills_datas = []
if advisor_skills_dir.exists():
    for root, dirs, files in os.walk(advisor_skills_dir):
        for file in files:
            # Only bundle non-code skill resources (e.g., SKILL.md). Python modules are packaged separately.
            if not file.lower().endswith(".md"):
                continue
            src_path = os.path.join(root, file)
            rel_dir = os.path.relpath(root, advisor_skills_dir)
            dst_dir = (os.path.join('sip_studio', 'advisor', 'skills', rel_dir) if rel_dir != '.' else os.path.join('sip_studio', 'advisor', 'skills'))
            advisor_skills_datas.append((src_path, dst_dir))

a = Analysis(
    [str(STUDIO / 'app.py')],
    pathex=[str(ROOT / 'src')],
    binaries=[],
    datas=frontend_datas + prompts_datas + advisor_skills_datas,
    hiddenimports=[
        'sip_studio','sip_studio.studio','sip_studio.studio.bridge','sip_studio.studio.updater',
        'sip_studio.brands','sip_studio.brands.storage','sip_studio.brands.models',
        'sip_studio.brands.memory','sip_studio.brands.context','sip_studio.brands.tools',
        'sip_studio.advisor','sip_studio.advisor.tools','sip_studio.config','sip_studio.config.settings',
        'webview','httpx','pydantic','pydantic_settings','packaging','openai','PIL','PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'numpy',
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='Sip Studio',debug=False,
    bootloader_ignore_signals=False,strip=False,upx=True,console=False,
    disable_windowed_traceback=False,argv_emulation=False,target_arch=None,
    codesign_identity=None,entitlements_file=None,)
coll = COLLECT(exe,a.binaries,a.zipfiles,a.datas,strip=False,upx=True,upx_exclude=[],name='Sip Studio',)
app = BUNDLE(coll,name='Sip Studio.app',icon='assets/SipStudio.icns',
    bundle_identifier='com.sip.sipstudio',
    info_plist={
        'CFBundleName': 'Sip Studio','CFBundleDisplayName': 'Sip Studio',
        'CFBundleVersion': '0.9.4','CFBundleShortVersionString': '0.9.4',
        'NSHighResolutionCapable': True,'LSMinimumSystemVersion': '10.13.0',
        'NSRequiresAquaSystemAppearance': False,
    },)
