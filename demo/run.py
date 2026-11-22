"""Replay the local demonstration from any working directory (Python 3.10+)."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("stage", choices=["input", "run", "challenge"])
stage = parser.parse_args().stage
import wave
import math
import struct
import hashlib

PACKAGE = ROOT / "harmonic-pitch-trace"
import json
import subprocess
import sys
import tempfile


def analyze(input_file, *flags):
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "result.json"
        subprocess.run([sys.executable, "-B", PACKAGE / "scripts/analyze.py", input_file, *flags, "--out", output],
                       capture_output=True, check=True)
        return json.loads(output.read_text(encoding="utf-8"))

sample = PACKAGE / "assets/case2.wav"
if stage == "input":
    with wave.open(str(sample)) as f:
        print("sample   case2.wav")
        print(f"PCM      {8*f.getsampwidth()} bit / {f.getnchannels()} ch")
        print(f"rate     {f.getframerate()} Hz")
        print(f"length   {f.getnframes()/f.getframerate():.3f} s")
elif stage == "run":
    result = analyze(sample)
    print("mode     acoustic repetition")
    print("status  ", result["status"])
    print(f"pitch    {result['fundamental_hz']:.3f} Hz")
    print(f"frames   {result['accepted_frames']}/{len(result['starts_s'])}")
else:
    twin = DEMO / "twin-360.wav"
    with wave.open(str(twin)) as wav:
        actual = wav.readframes(wav.getnframes())
    # The same samples arise from note 180 Hz with only harmonic 2.
    alternate = b"".join(struct.pack("<h",round(9000 * math.sin(2 * math.pi * (2 * 180) * i / 8000))) for i in range(4000))
    assert actual == alternate
    result = analyze(twin, "--source-identity")
    print("360 Hz / 180 Hz x 2 : PCM equal")
    print("status   " + result["status"])
    print("candidates " + ", ".join(f"{v:.1f}" for v in result["candidates_hz"])+" Hz")
    print("PCM hash " + hashlib.sha256(actual).hexdigest()[:16])
