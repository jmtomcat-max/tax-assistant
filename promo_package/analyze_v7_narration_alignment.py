from pathlib import Path
import subprocess
import wave
import numpy as np

ROOT = Path(__file__).resolve().parent
FFMPEG = ROOT.parent / ".venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries" / "ffmpeg-win-x86_64-v7.1.exe"
V7 = ROOT.parent / "presentation_launcher" / "media" / "TAX_ASSISTANT_V7_ENDING_BOOST.mp4"
TMP = ROOT / "alignment_tmp"
TMP.mkdir(exist_ok=True)
RATE = 4000

CUES = [
    "v3_s1_01", "v3_s2_01", "v3_s3_01", "v3_s3_02", "v3_s3_03",
    "v3_s4_01", "v3_s5_01", "v3_s6_01", "v3_s7_01", "v3_s7_02",
]

def convert(src: Path, dst: Path):
    subprocess.run([
        str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
        "-ac", "1", "-ar", str(RATE), "-c:a", "pcm_s16le", str(dst)
    ], check=True)

def read_wav(path: Path):
    with wave.open(str(path), "rb") as f:
        data = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float64)
    data -= data.mean()
    return data

def best_match(signal, template):
    n, m = len(signal), len(template)
    size = 1 << (n + m - 1).bit_length()
    conv = np.fft.irfft(np.fft.rfft(signal, size) * np.fft.rfft(template[::-1], size), size)
    corr = conv[m - 1:n]
    sq = np.concatenate(([0.0], np.cumsum(signal * signal)))
    energy = sq[m:] - sq[:-m]
    denom = np.sqrt(np.maximum(energy, 1.0) * max(float(np.dot(template, template)), 1.0))
    score = corr / denom
    idx = int(np.argmax(score))
    return idx / RATE, float(score[idx])

v7wav = TMP / "v7.wav"
convert(V7, v7wav)
signal = read_wav(v7wav)

for cue in CUES:
    src = ROOT / "audio" / f"{cue}.mp3"
    wav = TMP / f"{cue}.wav"
    convert(src, wav)
    start, score = best_match(signal, read_wav(wav))
    print(f"{cue}: start={start:.3f}s score={score:.4f}")
