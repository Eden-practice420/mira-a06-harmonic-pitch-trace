"""Synthesize a portable reference tone (or silence) to an explicitly chosen WAV file."""
import argparse
import math
from pathlib import Path
import struct
import wave

TONES = {
    "case1": (196, [1.0]),
    "case2": (277.18, [0.22, 1.0, 0.30]),
    "case3": (329.63, [0.0, 1.0, 0.75, 0.20]),
    "boundary": (0, [0])
}


def write_tone(name, destination):
    rate = 8000
    freq, amps = TONES[name]
    samples = []
    for i in range(4000):
        t = i / rate
        envelope = min(1.0, i/200, (4000-i)/200)
        signal = sum(a*math.sin(2*math.pi*(h+1)*freq*t) for h,a in enumerate(amps))
        samples.append(round(10000*envelope*signal))
    with wave.open(str(destination), "wb") as stream:
        stream.setparams((1, 2, rate, len(samples), "NONE", "not compressed"))
        stream.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=TONES)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        write_tone(args.case, args.out)
    except (OSError, wave.Error) as exc:
        parser.exit(2, f"Cannot save WAV: {exc}\n")
    print(f"Saved {args.case} to {args.out}")


if __name__ == "__main__":
    main()
