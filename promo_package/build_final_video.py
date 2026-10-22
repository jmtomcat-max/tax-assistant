import os
import subprocess
import imageio_ffmpeg

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    
    video_in = 'real_screen_record.mp4'
    badge_in = 'privacy_badge.png'
    audio_in = 'audio/master_soundtrack.mp3'
    video_out = 'Tax_Assistant_Demo_V3.mp4'
    
    print("Building final standalone MP4 video...")
    print(f"Working dir: {base_dir}")
    print(f"Video input: {video_in}")
    print(f"Badge input: {badge_in}")
    print(f"Audio input: {audio_in}")
    print(f"Output: {video_out}")

    # Filter graph:
    # 1. Pad 1920x1032 to 1920x1080
    # 2. Freeze last frame by 3.57s to reach exactly 72.0s
    # 3. Overlay privacy badge at x=215, y=765 to completely cover user email
    # 4. Burn in crisp modern subtitles
    filter_complex = (
        "[0:v]pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,"
        "tpad=stop_mode=clone:stop_duration=3.57[v0];"
        "[v0][1:v]overlay=x=220:y=758[v1];"
        "[v1]subtitles=filename='subtitles.srt':force_style='FontName=Malgun Gothic,FontSize=20,PrimaryColour=&H00FFFFFF,BackColour=&H90000000,BorderStyle=4,Outline=0,Shadow=0,MarginV=24'[vout];"
        "[2:a]aformat=channel_layouts=stereo:sample_rates=48000[aout]"
    )

    cmd = [
        ffmpeg, '-y',
        '-i', video_in,
        '-i', badge_in,
        '-i', audio_in,
        '-filter_complex', filter_complex,
        '-map', '[vout]',
        '-map', '[aout]',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '19',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '256k',
        '-shortest',
        '-movflags', '+faststart',
        video_out
    ]

    print("Running FFmpeg encoding...")
    proc = subprocess.run(cmd, cwd=base_dir, capture_output=True, encoding='utf-8', errors='ignore')
    if proc.returncode != 0:
        print("FFmpeg error:\n", proc.stderr)
        raise RuntimeError("Video rendering failed!")
        
    out_full = os.path.join(base_dir, video_out)
    print(f"SUCCESS: Video rendered successfully to: {out_full}")
    size_mb = os.path.getsize(out_full) / (1024 * 1024)
    print(f"File size: {size_mb:.2f} MB")

if __name__ == '__main__':
    main()
