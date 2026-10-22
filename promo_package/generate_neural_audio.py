# -*- coding: utf-8 -*-
"""
V2 70초 단축 버전: Microsoft Edge Neural Voice 한국어 나레이션 생성
"""
import os
import asyncio
import edge_tts

VOICE = "ko-KR-SunHiNeural"

# 70초 V2 정밀 대본 (초 단위 발화 최적화)
lines = [
    # Scene 1: Problem (0~7s)
    ("v2_s1_01", "하나의 세무 이슈를 검토하기 위해, 우리는 법령, 판례, 과거 검토자료를 다시 찾습니다."),
    
    # Scene 2: Solution (7~12s)
    ("v2_s2_01", "Tax Assistant는 이 과정을 하나의 Workflow로 연결합니다."),
    
    # Scene 3: Demo (12~37s)
    ("v2_s3_01", "질문을 입력하면 관련 근거를 찾고 검토 결과를 정리합니다."),
    ("v2_s3_02", "처분청의 과세 논거와 납세자의 방어 논리를 대조하고, 실제 판례 근거를 직접 확인합니다."),
    ("v2_s3_03", "그리고 이 모든 검토 과정은 기록으로 이어집니다."),
    
    # Scene 4: Review History (37~47s)
    ("v2_s4_01", "검토가 끝나도 지식은 사라지지 않습니다. 수행한 검토는 Review History에 자동으로 축적됩니다."),
    
    # Scene 5: Vault (47~54s)
    ("v2_s5_01", "중요한 판례와 자료는 별도로 선별해 다시 활용합니다."),
    
    # Scene 6: Knowledge DB (54~63s)
    ("v2_s6_01", "한 사람의 검토가 조직의 세무 지식으로 축적됩니다."),
    
    # Scene 7: Ending (63~70s)
    ("v2_s7_01", "검색에서 끝나는 AI가 아니라, 검토 경험이 쌓이는 세무 업무 플랫폼."),
    ("v2_s7_02", "Tax Assistant.")
]

out_dir = os.path.join(os.path.dirname(__file__), "audio")
os.makedirs(out_dir, exist_ok=True)

async def generate():
    print(f"Generating V2 70s Neural Audio using [{VOICE}]...")
    for key, text in lines:
        fpath = os.path.join(out_dir, f"{key}.mp3")
        print(f"Synthesizing [{key}]: {text}")
        communicate = edge_tts.Communicate(text, VOICE, rate="+3%", pitch="-1Hz")
        await communicate.save(fpath)
    print("All V2 Neural audio files successfully generated!")

if __name__ == "__main__":
    asyncio.run(generate())
