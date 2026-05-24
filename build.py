"""Build DMX调试助手 into a single-file exe with PyInstaller."""
import os, sys, subprocess, shutil

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

APP_NAME = "DMX调试助手"
BUILD_DIR = os.path.join(script_dir, "build")            # final output root
DIST_DIR = os.path.join(BUILD_DIR, APP_NAME)              # exe output dir
WORK_DIR = os.path.join(script_dir, "_buildtemp")         # PyInstaller temp work

# Clean previous build artifacts
for p in ["dist", f"{APP_NAME}_build", WORK_DIR, f"{APP_NAME}.spec"]:
    if os.path.isdir(p):
        shutil.rmtree(p)
    elif os.path.exists(p):
        os.remove(p)
# Clean output subdir but keep build/ itself (PyInstaller uses it too)
out_subdir = os.path.join(BUILD_DIR, APP_NAME)
if os.path.isdir(out_subdir):
    shutil.rmtree(out_subdir)

os.makedirs(DIST_DIR, exist_ok=True)

args = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--clean", "-y",
    "--distpath", DIST_DIR,
    "--workpath", WORK_DIR,
    "--icon", "icon.ico",
    "--name", APP_NAME,
    "main.py",
]

print("Running:", " ".join(args))
subprocess.check_call(args)

out = os.path.join(DIST_DIR, f"{APP_NAME}.exe")

# Create scenes folder alongside the exe (for settings/scenes persistence)
scenes_dir = os.path.join(DIST_DIR, "scenes")
os.makedirs(scenes_dir, exist_ok=True)

# Clean up PyInstaller intermediates
if os.path.isdir(WORK_DIR):
    shutil.rmtree(WORK_DIR)
spec_file = os.path.join(script_dir, f"{APP_NAME}.spec")
if os.path.exists(spec_file):
    os.remove(spec_file)

print(f"\nDone: {out} ({os.path.getsize(out) / 1024 / 1024:.1f} MB)")
print(f"Output: build/{APP_NAME}/")
