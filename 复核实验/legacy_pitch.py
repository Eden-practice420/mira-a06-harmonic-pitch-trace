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


def analyze(path):
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
    return dict(summary, status="steady", fundamental_hz=hz, spread_cents=max(cents)-min(cents))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to the input fixture or user data")
    parser.add_argument("--out", type=Path, required=True, help="Destination JSON result")
    args = parser.parse_args()
    try:
        result = analyze(args.input)
        record = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
        args.out.write_text(record + "\n", encoding="utf-8")
    except (ValueError, TypeError, KeyError, IndexError, OSError, EOFError, OverflowError, RuntimeError, struct.error, wave.Error) as exc:
        parser.exit(2, f"Cannot complete analysis: {exc}\n")
    print(f"Result saved to {args.out}")


if __name__ == "__main__":
    main()
