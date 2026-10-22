# -*- coding: utf-8 -*-
"""
V3 FINAL: Microsoft Edge Neural Voice 한국어 정밀 나레이션 생성
- 과세관청의 논거와 납세자의 대응 논리 비교
- 전문적이고 차분한 B2B SaaS 톤앤매너
"""
import os
import asyncio
import edge_tts
from mutagen.mp3 import MP3

VOICE = "ko-KR-SunHiNeural"

lines = [
    # Scene 1: Problem (0.0 ~ 7.8s)
    ("v3_s1_01", "하나의 세무 이슈를 검토하기 위해, 우리는 법령, 판례, 과거 검토자료를 다시 찾습니다."),
    
    # Scene 2: Solution (7.8 ~ 13.0s)
    ("v3_s2_01", "Tax Assistant는 이 과정을 하나의 Workflow로 연결합니다."),
    
    # Scene 3: Demo (13.0 ~ 38.0s)
    ("v3_s3_01", "질문을 입력하면 관련 근거를 찾고 검토 결과를 정리합니다."),
    ("v3_s3_02", "과세관청의 논거와 납세자의 대응 논리를 비교하고, 관련 근거를 직접 확인합니다."),
    ("v3_s3_03", "그리고 이 모든 검토 과정은 기록으로 이어집니다."),
    
    # Scene 4: Review History (38.0 ~ 48.0s)
    ("v3_s4_01", "검토가 끝나도 지식은 사라지지 않습니다. 수행한 검토는 Review History에 자동으로 축적됩니다."),
    
    # Scene 5: Vault (48.0 ~ 55.0s)
    ("v3_s5_01", "중요한 판례와 자료는 별도로 선별해 다시 활용합니다."),
    
    # Scene 6: Knowledge DB (55.0 ~ 63.0s)
    ("v3_s6_01", "한 사람의 검토가 조직의 세무 지식으로 축적됩니다."),
    
    # Scene 7: Ending (63.0 ~ 72.0s)
    ("v3_s7_01", "검색에서 끝나는 AI가 아니라, 검토 경험이 쌓이는 세무 업무 플랫폼."),
    ("v3_s7_02", "Tax Assistant.")
]

out_dir = os.path.join(os.path.dirname(__file__), "audio")
os.makedirs(out_dir, exist_ok=True)

async def generate():
    print(f"Generating V3 FINAL Neural Audio using [{VOICE}]...")
    durations = {}
    for key, text in lines:
        fpath = os.path.join(out_dir, f"{key}.mp3")
        print(f"Synthesizing [{key}]: {text}")
        communicate = edge_tts.Communicate(text, VOICE, rate="+1%", pitch="-2Hz")
        await communicate.save(fpath)
        audio = MP3(fpath)
        durations[key] = audio.info.length
        print(f"  -> Saved {key}.mp3 ({audio.info.length:.2f}s)")
    
    print("\n=== V3 Audio Durations Summary ===")
    for k, d in durations.items():
        print(f"{k}: {d:.2f}s")

if __name__ == "__main__":
    asyncio.run(generate())
