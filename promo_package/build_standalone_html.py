"""
interactive_preview.html + 동영상 + 오디오 = 단일 HTML 파일.

동영상을 <script type='text/plain'> 블록으로 분할 저장하고
JS에서 조립 → 한 번에 atob → Blob → objectURL로 변환한다.
"""
import os, base64, subprocess
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHUNK_SIZE = 768 * 1024  # 768KB 청크 (약 6~7개 청크)

def compress_video(src, dst):
    cmd = [
        FFMPEG, '-y', '-i', src,
        '-vf', 'scale=1280:720',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '28',
        '-an',
        '-movflags', '+faststart',
        dst
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    size_mb = os.path.getsize(dst) / (1024*1024)
    print(f"  Compressed video: {size_mb:.1f} MB")

def file_to_base64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('ascii')

def file_to_data_uri(path, mime):
    return f"data:{mime};base64,{file_to_base64(path)}"

def make_video_chunks_html(b64_str):
    """base64 문자열을 <script type='text/plain'> 블록들로 분할"""
    chunks = []
    idx = 0
    i = 0
    while idx < len(b64_str):
        chunk = b64_str[idx:idx+CHUNK_SIZE]
        chunks.append(f'<script type="text/plain" id="_vc{i}">{chunk}</script>')
        idx += CHUNK_SIZE
        i += 1
    print(f"  Split into {i} chunks")
    return '\n'.join(chunks), i

def main():
    html_path = os.path.join(BASE_DIR, 'interactive_preview.html')
    out_path  = os.path.join(BASE_DIR, 'Tax_Assistant_Demo_V3_Standalone.html')

    # 1. 영상 압축
    src_video = os.path.join(BASE_DIR, 'real_screen_record.mp4')
    compressed = os.path.join(BASE_DIR, 'temp_compressed.mp4')
    print("[1/4] Compressing video...")
    compress_video(src_video, compressed)
    video_b64 = file_to_base64(compressed)
    os.remove(compressed)
    print(f"  Base64 length: {len(video_b64):,} chars")

    # 2. 청크 HTML 생성
    print("[2/4] Creating video chunks...")
    chunks_html, num_chunks = make_video_chunks_html(video_b64)

    # 3. 오디오 파일 수집
    print("[3/4] Encoding audio files...")
    audio_dir = os.path.join(BASE_DIR, 'audio')
    audio_map = {}
    for fname in os.listdir(audio_dir):
        if fname.endswith('.mp3'):
            rel = f"audio/{fname}"
            full = os.path.join(audio_dir, fname)
            audio_map[rel] = file_to_data_uri(full, 'audio/mpeg')
    print(f"  Encoded {len(audio_map)} audio files")

    # 4. HTML 변환
    print("[4/4] Building standalone HTML...")
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # video 태그: src 제거
    html = html.replace(
        '<video id="realDemoVideo" src="real_screen_record.mp4" playsinline muted preload="auto"',
        '<video id="realDemoVideo" playsinline muted preload="auto" data-embedded="true"'
    )

    # </body> 앞에 동영상 청크 + 조립 스크립트 삽입
    loader_script = f'''
<!-- ═══ Embedded Video Data (chunked) ═══ -->
{chunks_html}
<script>
(function() {{
  try {{
    // 1. 청크 조립
    var parts = [];
    for (var i = 0; i < {num_chunks}; i++) {{
      var el = document.getElementById('_vc' + i);
      if (el) {{
        parts.push(el.textContent);
        el.remove(); // 즉시 DOM에서 제거
      }}
    }}
    var fullB64 = parts.join('');
    parts = null;
    
    // 2. Blob 우회: JS에서 직접 data URI로 src 할당 (Teams/제한된 환경 호환성)
    var dataUri = "data:video/mp4;base64," + fullB64;
    fullB64 = null;
    
    // 3. 비디오 요소에 세팅
    var vid = document.getElementById('realDemoVideo');
    if (vid) {{
      vid.src = dataUri;
      vid.load();
      vid.addEventListener('loadeddata', function() {{
        console.log('[Standalone] Video ready via Data URI');
      }});
      vid.addEventListener('error', function(e) {{
        console.error('[Standalone] Video error:', e);
      }});
    }}
  }} catch (err) {{
    console.error('[Standalone] Video init failed:', err);
  }}
}})();
</script>
'''
    html = html.replace('</body>', loader_script + '\n</body>')

    # 오디오 파일 경로 교체
    for rel_path in sorted(audio_map.keys(), key=len, reverse=True):
        html = html.replace(f"'{rel_path}'", f"'{audio_map[rel_path]}'")
        html = html.replace(f'"{rel_path}"', f'"{audio_map[rel_path]}"')

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    size_mb = os.path.getsize(out_path) / (1024*1024)
    print(f"\nDONE: {out_path}")
    print(f"File size: {size_mb:.1f} MB")

if __name__ == '__main__':
    main()
