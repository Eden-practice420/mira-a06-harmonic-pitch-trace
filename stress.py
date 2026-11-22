"""Run supplementary deterministic stress cases; retain each input specification and result."""
import argparse
from fractions import Fraction
import itertools
import json
import math
from pathlib import Path
import random
import statistics
import struct
import subprocess
import sys
import tempfile
import wave

def trial(rng, index, folder):
    fs=8000
    f0=rng.uniform(145,445)
    amps=[rng.choice([0,.15,.8]),1,rng.uniform(.20,.9),.15]
    raw=folder/"trial.wav"
    samples=[]
    for j in range(2400):
        v=sum(a*math.sin(2*math.pi*(k+1)*f0*j/fs) for k,a in enumerate(amps))
        samples.append(round(8000*v+rng.uniform(-150,150)))
    with wave.open(str(raw),"wb") as w:
        w.setparams((1,2,fs,2400,"NONE","not compressed"))
        w.writeframes(struct.pack("<2400h",*samples))
    res=run_tool(raw,folder)
    err=abs(1200*math.log2(res["fundamental_hz"]/f0)) if res["status"]=="steady" else None
    return dict(trial=index,target_hz=f0,amplitudes=amps,status=res["status"],error_cents=err)

def summarize(records):
    errors=[r["error_cents"] for r in records if r["error_cents"] is not None]
    return dict(n=len(records),steady=len(errors),within_10_cents=sum(x<10 for x in errors),
                worst_accepted_error_cents=max(errors,default=None))

def run_tool(path,folder):
    dest=folder/"result.json"
    script=Path(__file__).resolve().parent/"harmonic-pitch-trace"/"scripts"/"analyze.py"
    subprocess.run([sys.executable,"-B",str(script),str(path),"--out",str(dest)],check=True,capture_output=True)
    return json.loads(dest.read_text(encoding="utf-8"))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=Path("扩展实验.json"))
    args=parser.parse_args()
    seed=59281
    rng=random.Random(seed)
    with tempfile.TemporaryDirectory() as dirname:
        records=[trial(rng,i+1,Path(dirname)) for i in range(36)]
    summary=summarize(records)
    args.out.write_text(json.dumps(dict(seed=seed,summary=summary,records=records),ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary))

if __name__=="__main__":
    main()
