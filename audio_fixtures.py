"""Regenerate the four bundled examples from the submission's synthesis script."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parent / "harmonic-pitch-trace"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=root / "assets")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("case1", "case2", "case3", "boundary"):
        subprocess.run([sys.executable, str(root / "scripts" / "synthesize.py"), name,
                        "--out", str(args.out_dir / (name + ".wav"))], check=True)


if __name__ == "__main__":
    main()
