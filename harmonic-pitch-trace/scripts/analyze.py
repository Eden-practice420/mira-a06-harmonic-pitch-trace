"""Estimate a steady monophonic fundamental from PCM audio by periodicity."""
import argparse
import json
import math
from pathlib import Path
from statistics import median
import struct
import wave


def estimate(frame, rate):
    mean = sum(frame) / len(frame)
    x = [v - mean for v in frame]
    if math.sqrt(sum(v*v for v in x) / len(x)) < 100:
        return None
    min_lag = max(2, int(rate / 500))
    max_lag = math.ceil(rate / 130) + 1
    length = len(x) - max_lag
    # Fixed overlap prevents bias toward larger lags.
    norm = [1.0]
    running = 0.0
    for lag in range(1, max_lag + 1):
        d = sum((x[j] - x[j+lag])**2 for j in range(length))
        running += d
        norm.append(d * lag / running if running else 1.0)
    for lag in range(min_lag, max_lag):
        if norm[lag] >= 0.15:
            continue
        while lag < max_lag - 1 and norm[lag+1] < norm[lag]:
            lag += 1
        y0, y1, y2 = norm[lag-1:lag+2]
        curvature = y0 + y2 - 2*y1
        shift = max(-0.5, min(0.5, 0.5*(y0-y2)/curvature)) if curvature > 0 else 0.0
        pitch = rate / (lag + shift)
        if 130 <= pitch <= 500:
            return pitch
        return None
    return None


def octave_evidence(samples, rate, candidate):
    """Contrast weak half-integer content against the candidate's harmonic series."""
    lower = candidate / 2
    if lower < 130:
        return {"tested": False, "reason": "lower_candidate_outside_range"}
    length = min(len(samples), round(0.12*rate))
    taper = [0.5-0.5*math.cos(2*math.pi*i/(length-1)) for i in range(length)]
    centers = [round((len(samples)-length)*j/4) for j in range(5)]
    ratios = []
    frequencies = [lower*k for k in range(1,7) if lower*k < rate/2]
    original_count = len(frequencies)
    # Sample the local noise floor away from the Hann main lobe. Compare odd
    # partial groups with adjacent bins to avoid a universal amplitude gate.
    spacing = 4 * rate / length
    sidebands = [f+offset for f in frequencies[::2] for offset in (-spacing,spacing)]
    frequencies += sidebands
    background = []
    kernels = [[(taper[i]*math.cos(2*math.pi*f*i/rate),
                 taper[i]*math.sin(2*math.pi*f*i/rate)) for i in range(length)]
               for f in frequencies]
    for start in centers:
        frame = samples[start:start+length]
        powers = []
        for kernel in kernels:
            re = sum(s*v[0] for s,v in zip(frame,kernel))
            im = sum(s*v[1] for s,v in zip(frame,kernel))
            powers.append(re*re+im*im)
        band = powers[:original_count]
        odd, even = sum(band[::2]), sum(band[1::2])
        ratios.append(math.sqrt(odd/max(even,1e-20)))
        background.append(math.sqrt(sum(powers[original_count:]) / (2*max(even,1e-20))))
    return {"tested": True, "lower_candidate_hz": lower,
            "half_series_amplitude_ratios": ratios, "median_ratio": median(ratios),
            "local_background": median(background), "gate": max(.005, 4*median(background))}


def analyze(path, source_identity=False):
    with wave.open(str(path), "rb") as w:
        rate = w.getframerate()
        if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getcomptype() != "NONE":
            raise ValueError("use mono signed 16-bit PCM WAV")
        if not 4000 <= rate <= 48000 or not 0.12 <= w.getnframes() / rate <= 15:
            raise ValueError("use 4–48 kHz, 0.12–15 second clips")
        frame_count = w.getnframes()
        raw = w.readframes(frame_count)
        if len(raw) != frame_count * 2:
            raise ValueError("truncated PCM data")
    samples = struct.unpack(f"<{len(raw)//2}h", raw)
    # 12 deterministic, distributed 60-ms frames cap the computational cost.
    length = round(0.06 * rate)
    starts = sorted({round((len(samples)-length)*i/11) for i in range(12)})
    trace = [estimate(samples[i:i+length], rate) for i in starts]
    voiced = [x for x in trace if x is not None]
    summary = dict(frame_hz=trace, starts_s=[s/rate for s in starts], accepted_frames=len(voiced),
                   sample_rate=rate)
    if len(voiced) < 8:
        return dict(summary, status="insufficient")
    hz = median(voiced)
    cents = [1200 * math.log2(x/hz) for x in voiced]
    if max(cents) - min(cents) > 70:
        return dict(summary, status="unstable")
    octave = octave_evidence(samples, rate, hz)
    if octave["tested"] and octave["median_ratio"] >= octave["gate"]:
        candidates = [hz / k for k in range(1, int(hz/130) + 1)] if source_identity else [hz/2, hz]
        return dict(summary, status="octave_ambiguous", candidates_hz=candidates,
                    spread_cents=max(cents)-min(cents), octave_evidence=octave)
    if source_identity:
        candidates = [hz / k for k in range(1, int(hz/130) + 1)]
        if len(candidates) > 1:
            return dict(summary, status="source_not_identifiable", candidates_hz=candidates,
                        acoustic_repeat_hz=hz, octave_evidence=octave)
    return dict(summary, status="steady", fundamental_hz=hz, spread_cents=max(cents)-min(cents),
                octave_evidence=octave)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to the input fixture or user data")
    parser.add_argument("--out", type=Path, required=True, help="Destination JSON result")
    parser.add_argument("--source-identity", action="store_true",
                        help="Distinguish acoustic repetition from a possible source with missing harmonics")
    args = parser.parse_args()
    try:
        result = analyze(args.input, args.source_identity)
        record = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
        args.out.write_text(record + "\n", encoding="utf-8")
    except (ValueError, TypeError, KeyError, IndexError, OSError, EOFError, OverflowError, RuntimeError, struct.error, wave.Error) as exc:
        parser.exit(2, f"Cannot complete analysis: {exc}\n")
    print(f"Result saved to {args.out}")


if __name__ == "__main__":
    main()
