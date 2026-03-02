import pathlib
import shutil

for p in pathlib.Path(".").rglob("__pycache__"):
    shutil.rmtree(p)

for name in [".pytest_cache", ".ruff_cache"]:
    shutil.rmtree(name, ignore_errors=True)
