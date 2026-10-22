# -*- coding: utf-8 -*-
"""
Google TTS (gTTS)를 사용하여 Tax Assistant 홍보영상 대본을 MP3 음성 파일로 생성
"""
import os
from gtts import gTTS

lines = [
    ("s1_01", "하나의 세무 이슈를 검토하기 위해"),
    ("s1_02", "우리는 법령을 찾고, 판례를 검색하고, 과거 검토자료를 다시 찾아봅니다."),
    ("s1_03", "세무 검토에 필요한 정보는 많지만, 검토 과정은 언제나 흩어져 있습니다."),
    ("s2_01", "이 과정을 하나의 워크플로우로 연결한다면 어떨까요?"),
    ("s2_02", "택스 어시스턴트."),
    ("s3_01", "자연어로 세무 질문을 입력하면"),
    ("s3_02", "인공지능이 사실관계를 분석하고 공식 판례를 실시간 탐색합니다."),
    ("s3_03", "국세청의 과세 논거와 납세자의 방어 논리를 즉시 대조하고,"),
    ("s3_04", "세무조사에 대비한 필수 증빙까지 명확하게 제시합니다."),
    ("s4_01", "검토가 끝나도 지식은 사라지지 않습니다."),
    ("s4_02", "수행한 모든 검토는 리뷰 히스토리에 자동으로 축적되고,"),
    ("s5_01", "핵심 판례는 보관함에 선별하여 체계적으로 관리합니다."),
    ("s6_01", "한 사람의 검토가 전사의 지식이 되는 구조."),
    ("s6_02", "택스 리뷰 놀리지 데이터베이스."),
    ("s6_03", "반복되는 세무 검토를 조직의 지식으로."),
    ("s7_01", "검색에서 끝나는 인공지능이 아니라, 검토 경험이 쌓이는 세무 업무 플랫폼."),
    ("s7_02", "택스 어시스턴트.")
]

out_dir = os.path.join(os.path.dirname(__file__), "audio")
os.makedirs(out_dir, exist_ok=True)

print("Starting Google TTS generation...")
for key, text in lines:
    fpath = os.path.join(out_dir, f"{key}.mp3")
    print(f"Generating [{key}]: {text}")
    tts = gTTS(text=text, lang="ko", slow=False)
    tts.save(fpath)

print("All Google TTS files generated successfully in promo_package/audio/!")
