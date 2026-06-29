from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qaoa_dtn.utils.config import load_config
from qaoa_dtn.experiment.runner import run_experiment

if __name__ == "__main__":
    paths = run_experiment(load_config("configs/quick.yaml"))
    for k, v in paths.items():
        print(f"{k}: {v}")
