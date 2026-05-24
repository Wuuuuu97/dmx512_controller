"""Build DMX调试助手 into a single-file exe with PyInstaller."""
import os, sys, subprocess, shutil

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Clean old build artifacts
for p in ["build", "DMX调试助手.spec"]:
    p = os.path.join(script_dir, p)
    if os.path.isdir(p):
        shutil.rmtree(p)
    elif os.path.exists(p):
        os.remove(p)

# Build into DMX调试助手_build/DMX调试助手/DMX调试助手.exe
dist_subdir = os.path.join(script_dir, "DMX调试助手_build", "DMX调试助手")
args = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--clean",
    "-y",
    "--distpath", dist_subdir,
    "--icon", "icon.ico",
    "--name", "DMX调试助手",
    "main.py",
]

print("Running:", " ".join(args))
subprocess.check_call(args)

out = os.path.join(dist_subdir, "DMX调试助手.exe")

# Create scenes directory alongside the exe
scenes_dir = os.path.join(dist_subdir, "scenes")
os.makedirs(scenes_dir, exist_ok=True)

print(f"\nDone: {out} ({os.path.getsize(out) / 1024 / 1024:.1f} MB)")
print(f"Scenes dir: {scenes_dir}")
