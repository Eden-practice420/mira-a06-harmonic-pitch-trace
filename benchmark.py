"""Reproduce the published control experiments with only the Python standard library."""
import argparse
from fractions import Fraction
import itertools
import json
import math
from pathlib import Path
import platform
import struct
import subprocess
import sys
import wave

def score(case, raw, result):
    gold = [196, 277.18, 329.63][case]
    with wave.open(str(raw),"rb") as w:
        fs = w.getframerate()
        samples = struct.unpack(f"<{w.getnframes()}h", w.readframes(w.getnframes()))
    center = sum(samples)/len(samples)
    rises = [i for i in range(1,len(samples)) if samples[i-1] <= center < samples[i]]
    crossing_hz = (len(rises)-1)*fs/(rises[-1]-rises[0])
    cents = lambda hz: abs(1200*math.log2(hz/gold))
    assert result["status"] == "steady" and cents(result["fundamental_hz"]) < 10
    return dict(skill=cents(result["fundamental_hz"]), baseline=cents(crossing_hz),
                baseline_hz=crossing_hz, synthesized_hz=gold)

def check_boundary(result):
    assert result["status"] == "insufficient" and result["accepted_frames"] == 0

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("原始结果.json"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    package = root / "harmonic-pitch-trace"
    from tempfile import TemporaryDirectory
    records = []
    with TemporaryDirectory() as tmp:
        for index, name in enumerate(("case1","case2","case3","boundary")):
            source = package/"assets"/(name+".wav")
            dest = Path(tmp)/(name+".json")
            command = [sys.executable, "-B", str(package/"scripts"/"analyze.py"), str(source), "--out", str(dest)]
            run = subprocess.run(command, capture_output=True)
            if run.returncode:
                if name != "boundary" or True:
                    raise RuntimeError(run.stderr.decode(errors="replace"))
                result = {"returncode":run.returncode, "stderr":run.stderr.decode().strip()}
            else:
                result = json.loads(dest.read_text(encoding="utf-8"))
            stats = score(index,source,result) if index < 3 else None
            if name == "boundary":
                check_boundary(result)
            records.append(dict(input=source.name, skill_output=result, evaluation=stats))
    payload = dict(runtime=platform.python_version(), architecture=platform.machine(),
                   platform=platform.system(), records=records)
    args.out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Verified 3 paired tasks and 1 boundary case.")

if __name__ == "__main__":
    main()
