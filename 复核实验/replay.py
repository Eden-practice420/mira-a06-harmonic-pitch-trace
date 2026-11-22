"""Reproduce the version 1.1 application audit. Run with Python 3.10+."""
import argparse
from fractions import Fraction
import importlib.util
import itertools
import json
import math
from pathlib import Path
import random
import statistics
import struct
import sys
import tempfile
import wave

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
PACKAGE = PROJECT / "harmonic-pitch-trace"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name,path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tool = load_module("current_solver", PACKAGE/"scripts"/"analyze.py")


def read_input(d, folder):
    path = folder/"input.json"
    path.write_text(json.dumps(d,ensure_ascii=False),encoding="utf-8")
    return tool.analyze(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=HERE/"results.json")
    args=parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        out=experiment(Path(tmp))
    args.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out["summary"],ensure_ascii=True))

def render(folder, hz, amps, rng, noise):
    fs=8000
    path=folder/"input.wav"
    values=[]
    for j in range(2400):
        signal=sum(a*math.sin(2*math.pi*(k+1)*hz*j/fs) for k,a in enumerate(amps))
        values.append(round(8000*signal+rng.uniform(-noise,noise)))
    with wave.open(str(path),"wb") as w:
        w.setparams((1,2,fs,len(values),"NONE","not compressed"))
        w.writeframes(struct.pack(f"<{len(values)}h",*values))
    return path


def grade(result,truth):
    err=abs(1200*math.log2(result["fundamental_hz"]/truth)) if result["status"]=="steady" else None
    return dict(status=result["status"],error_cents=err,candidates=result.get("candidates_hz"),
                ratio=result.get("octave_evidence",{}).get("median_ratio"))


def summarize(rows,key):
    accepted=[r[key]["error_cents"] for r in rows if r[key]["error_cents"] is not None]
    return dict(n=len(rows),accepted=len(accepted),abstained=len(rows)-len(accepted),
                errors_over_10=sum(e>10 for e in accepted),octave_errors=sum(e>900 for e in accepted))


def experiment(folder):
    legacy=load_module("legacy_solver",HERE/"legacy_pitch.py")
    records=[]
    for family,seed,n in [("original36",59281,36),("challenge60",98107,60),("holdout50",77541,50)]:
        rng=random.Random(seed)
        for i in range(n):
            if family=="original36":
                f=rng.uniform(145,445)
                amps=[rng.choice([0,.15,.8]),1,rng.uniform(.20,.9),.15]
                noise=150
            elif family=="challenge60":
                f=rng.uniform(140,242)
                # Include very weak odd partials, around the gate, and strong ones.
                base=[.01,.035,.075,.14,.30,.8][i%6]
                amps=[base*rng.uniform(.4,1),1,base*rng.uniform(.7,1.2),.22]
                noise=rng.choice([40,150,350])
            else:
                f=rng.uniform(135,245)
                # Continuous distribution plus zero-sideband cases and stronger hiss.
                odd=rng.choice([0,10**rng.uniform(-3,-.1)])
                amps=[odd,1,odd*rng.uniform(.2,1.3),rng.uniform(.1,.3)]
                noise=rng.uniform(100,600)
            path=render(folder,f,amps,rng,noise)
            old=grade(legacy.analyze(path),f)
            new=grade(tool.analyze(path),f)
            strict=grade(tool.analyze(path,source_identity=True),f)
            records.append(dict(bank=family,i=i+1,f0=f,amps=amps,noise=noise,legacy=old,current=new,strict_source=strict))
    # 360 Hz sine and a 180 Hz source containing only harmonic 2 generate identical samples.
    path=render(folder,360,[1],random.Random(0),0)
    bytes1=path.read_bytes()
    path=render(folder,180,[0,1],random.Random(0),0)
    assert path.read_bytes()==bytes1
    source=tool.analyze(path,source_identity=True)
    assert source["status"]=="source_not_identifiable"
    grouped={bank:{key:summarize([r for r in records if r["bank"]==bank],key) for key in ("legacy","current","strict_source")}
             for bank in ["original36","challenge60","holdout50"]}
    return dict(summary=grouped,identical_waveform=dict(source_a_hz=360,source_b_hz=180,
                    identical_pcm=True,strict_output=source,usual_output=tool.analyze(path)),
                seed_by_bank={"original36":59281,"challenge60":98107,"holdout50":77541},records=records)

if __name__=="__main__":
    main()
