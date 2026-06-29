from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


import importlib

packages = [
    "qiskit",
    "qiskit_aer",
    "numpy",
    "pandas",
    "scipy",
    "networkx",
    "matplotlib",
    "yaml",
    "tqdm",
]

ok = True
for name in packages:
    try:
        module = importlib.import_module(name)
        version = getattr(module, "__version__", "available")
        print(f"[OK] {name}: {version}")
    except Exception as exc:
        ok = False
        print(f"[MISSING] {name}: {exc}")

try:
    import qaoa_dtn
    print(f"[OK] qaoa_dtn: {qaoa_dtn.__version__}")
except Exception as exc:
    ok = False
    print(f"[MISSING] qaoa_dtn import failed: {exc}")

if not ok:
    raise SystemExit("Environment check failed.")
print("Environment check passed.")
