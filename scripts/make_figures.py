from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


import argparse
from qaoa_dtn.analysis.plots import make_figures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--figures", required=True)
    parser.add_argument("--primary-topology", default="linear")
    args = parser.parse_args()
    paths = make_figures(args.results, args.figures, args.primary_topology)
    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
