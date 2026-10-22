from pathlib import Path
import subprocess
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FFMPEG = ROOT / ".venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries" / "ffmpeg-win-x86_64-v7.1.exe"
OLD = Path(r"C:\Users\jongmin98\Downloads\TAX_ASSISTANT_FINAL_NEW_VIDEO_V7_AUDIO.mp4")
NEW = Path(r"C:\Users\jongmin98\Downloads\Untitled_Scene_10-07_04_13_54_20261007133857.mp4")
W, H = 64, 36

def frames(path):
    data = subprocess.check_output([
        str(FFMPEG), "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-vf", f"fps=1,scale={W}:{H},format=gray", "-f", "rawvideo", "-"
    ])
    return np.frombuffer(data, dtype=np.uint8).reshape(-1, H * W).astype(np.float32)

old = frames(OLD)
new = frames(NEW)
print(f"old_frames={len(old)} new_frames={len(new)}")

# Compare both plausible alignments: same timestamp and +10 seconds.
rows = []
for t in range(min(len(old), len(new) - 10)):
    same = float(np.mean(np.abs(old[t] - new[t])))
    plus10 = float(np.mean(np.abs(old[t] - new[t + 10])))
    rows.append((t, same, plus10, plus10 - same))

# A sustained change from same-time match to +10-second match marks insertion.
best = None
for split in range(5, len(rows) - 5):
    cost = sum(r[1] for r in rows[:split]) + sum(r[2] for r in rows[split:])
    if best is None or cost < best[0]:
        best = (cost, split)

print(f"estimated_insert_start={best[1]}s")
for row in rows[max(0, best[1]-5):best[1]+6]:
    print(f"t={row[0]:3d} same={row[1]:7.2f} plus10={row[2]:7.2f} delta={row[3]:7.2f}")
