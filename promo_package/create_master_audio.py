import os
import subprocess
import wave
import numpy as np
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SAMPLE_RATE = 48000
TOTAL_DURATION = 72.0
TOTAL_SAMPLES = int(SAMPLE_RATE * TOTAL_DURATION)

def mp3_to_wav(mp3_path, wav_path):
    cmd = [
        FFMPEG, '-y', '-v', 'error',
        '-i', mp3_path,
        '-ar', str(SAMPLE_RATE),
        '-ac', '2',
        wav_path
    ]
    subprocess.run(cmd, check=True)

def read_wav(wav_path):
    with wave.open(wav_path, 'rb') as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
    if sampwidth == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")
    return data.reshape(-1, n_channels)

def write_mp3(data, out_path):
    temp_wav = out_path + '.temp.wav'
    clipped = np.clip(data, -1.0, 1.0)
    int_data = (clipped * 32767.0).astype(np.int16)
    with wave.open(temp_wav, 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(int_data.tobytes())
    
    cmd = [
        FFMPEG, '-y', '-v', 'error',
        '-i', temp_wav,
        '-b:a', '320k',
        out_path
    ]
    subprocess.run(cmd, check=True)
    if os.path.exists(temp_wav):
        os.remove(temp_wav)
    print(f"Master soundtrack saved: {out_path}")

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(base_dir, 'audio')
    temp_dir = os.path.join(base_dir, 'temp_audio')
    os.makedirs(temp_dir, exist_ok=True)
    
    # 1. Convert & Load BGM
    bgm_mp3 = os.path.join(audio_dir, 'tax_assistant_bgm.mp3')
    bgm_wav = os.path.join(temp_dir, 'bgm.wav')
    print("Converting BGM...")
    mp3_to_wav(bgm_mp3, bgm_wav)
    bgm = read_wav(bgm_wav)
    
    if len(bgm) < TOTAL_SAMPLES:
        pad = np.zeros((TOTAL_SAMPLES - len(bgm), 2), dtype=np.float32)
        bgm = np.vstack([bgm, pad])
    else:
        bgm = bgm[:TOTAL_SAMPLES]
        
    # Fade out last 2.5s
    fade_samples = int(SAMPLE_RATE * 2.5)
    fade_curve = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32).reshape(-1, 1)
    bgm[-fade_samples:] *= fade_curve

    # 2. Narration cues
    cues = [
        (0.0, 'v3_s1_01.mp3'),
        (7.9, 'v3_s2_01.mp3'),
        (13.2, 'v3_s3_01.mp3'),
        (19.0, 'v3_s3_02.mp3'),
        (27.0, 'v3_s3_03.mp3'),
        (38.0, 'v3_s4_01.mp3'),
        (48.0, 'v3_s5_01.mp3'),
        (55.0, 'v3_s6_01.mp3'),
        (63.0, 'v3_s7_01.mp3'),
        (69.7, 'v3_s7_02.mp3')
    ]

    voice_track = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    speech_mask = np.zeros(TOTAL_SAMPLES, dtype=np.float32)

    for i, (start_sec, filename) in enumerate(cues):
        fpath = os.path.join(audio_dir, filename)
        if not os.path.exists(fpath):
            print(f"Warning: {filename} not found!")
            continue
        twav = os.path.join(temp_dir, f'cue_{i}.wav')
        mp3_to_wav(fpath, twav)
        v_data = read_wav(twav)
        
        start_idx = int(start_sec * SAMPLE_RATE)
        end_idx = min(start_idx + len(v_data), TOTAL_SAMPLES)
        length = end_idx - start_idx
        voice_track[start_idx:end_idx] += v_data[:length]
        
        margin_before = int(0.15 * SAMPLE_RATE)
        margin_after = int(0.25 * SAMPLE_RATE)
        mask_start = max(0, start_idx - margin_before)
        mask_end = min(TOTAL_SAMPLES, end_idx + margin_after)
        speech_mask[mask_start:mask_end] = 1.0

    # Fast smooth speech mask with cumsum (box blur in 0.005s)
    kernel_size = int(SAMPLE_RATE * 0.25)
    cs = np.cumsum(np.pad(speech_mask, (kernel_size // 2, kernel_size // 2), mode='edge'))
    smoothed_mask = (cs[kernel_size:] - cs[:-kernel_size]) / float(kernel_size)
    if len(smoothed_mask) > TOTAL_SAMPLES:
        smoothed_mask = smoothed_mask[:TOTAL_SAMPLES]
    elif len(smoothed_mask) < TOTAL_SAMPLES:
        smoothed_mask = np.pad(smoothed_mask, (0, TOTAL_SAMPLES - len(smoothed_mask)), mode='edge')
    smoothed_mask = np.clip(smoothed_mask, 0.0, 1.0).reshape(-1, 1)

    # Ducking: Voice active = 0.08, Pause = 0.25
    bgm_gain = 0.25 * (1.0 - smoothed_mask) + 0.08 * smoothed_mask
    ducked_bgm = bgm * bgm_gain

    # Final Mix: Voice boost 1.15
    master = ducked_bgm + voice_track * 1.15
    max_val = np.max(np.abs(master))
    if max_val > 0.98:
        master = master * (0.98 / max_val)

    out_file = os.path.join(audio_dir, 'master_soundtrack.mp3')
    write_mp3(master, out_file)
    print("Audio mixing complete!")

if __name__ == '__main__':
    main()
