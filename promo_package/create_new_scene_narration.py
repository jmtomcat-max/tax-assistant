# -*- coding: utf-8 -*-
"""Create a separately narrated copy of the 130-second TAX ASSISTANT video."""

import asyncio
import subprocess
from pathlib import Path

import edge_tts
from mutagen.mp3 import MP3


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\Users\jongmin98\Downloads\Untitled_Scene_10-07_04_13_54_20261007133857.mp4")
BGM = ROOT / "promo_package/audio/v7_bgm_original.wav"
FFMPEG = ROOT / ".venv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
WORK = ROOT / "promo_package/audio/new_scene_narration"
OUTPUT = ROOT / "presentation_launcher/media/TAX_ASSISTANT_NEW_NARRATED_SUNHI.mp4"

VOICE = "ko-KR-SunHiNeural"
RATE = "+1%"
PITCH = "-2Hz"
SCENE_SECONDS = 10.0
START_MARGIN = 0.7
MAX_SPEECH_SECONDS = 8.4

LINES = [
    "세무 판단은 단순한 검색만으로 완성되지 않습니다. 신뢰할 수 있는 근거를 찾는 과정이 필요합니다.",
    "외부의 방대한 세무 자료와 조직 내부의 경험. 택스 어시스턴트는 흩어진 정보를 조직의 지식으로 연결합니다.",
    "한 건의 질문은 검색과 검토, 승인 과정을 거쳐 검증된 지식이 되고, 다음 업무에 다시 활용됩니다.",
    "일회성 답변은 업무가 끝나면 사라집니다. 택스 어시스턴트는 공식 근거와 사람의 승인을 연결해 지식을 축적합니다.",
    "복잡한 검색 조건은 필요하지 않습니다. 궁금한 세무 쟁점을 자연어로 질문하면 분석이 바로 시작됩니다.",
    "질문을 분석하고 사실관계를 구조화한 뒤, 내부 지식과 공식 자료를 검색해 검토 가능한 답변을 작성합니다.",
    "먼저 조직 내부의 유사 검토 사례와 축적된 업무 경험을 탐색해, 과거의 지식을 현재의 판단에 연결합니다.",
    "이어서 판례와 법령, 과세관청의 공식 자료를 확인합니다. 모든 판단은 검증 가능한 근거에서 시작됩니다.",
    "질문과 답변, 참고 근거는 검토 이력으로 자동 저장됩니다. 누가 어떤 근거로 판단했는지 다시 확인할 수 있습니다.",
    "인공지능이 제시한 결과는 사람의 검토를 거칩니다. 담당자는 내용을 승인하고, 추가 검토하거나 반려할 수 있습니다.",
    "승인된 판단은 일회성 답변으로 끝나지 않습니다. 검증된 지식으로 저장되어 후속 업무에 다시 활용됩니다.",
    "택스 어시스턴트의 신뢰는 내부 맥락과 공식 근거, 그리고 사람의 승인이 함께 작동하는 통제 구조에서 나옵니다.",
    "한 사람의 판단을 넘어, 조직의 지식이 움직이기 시작합니다. 택스 어시스턴트입니다.",
]


async def synthesize() -> list[Path]:
    WORK.mkdir(parents=True, exist_ok=True)
    files = []
    for index, text in enumerate(LINES, 1):
        path = WORK / f"scene_{index:02d}.mp3"
        if not path.exists():
            await edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH).save(path)
        files.append(path)
    return files


def render(files: list[Path]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    command = [str(FFMPEG), "-y", "-i", str(SOURCE), "-i", str(BGM)]
    for path in files:
        command += ["-i", str(path)]

    filters = []
    labels = []
    for index, path in enumerate(files, 2):
        duration = MP3(path).info.length
        speed = max(1.0, duration / MAX_SPEECH_SECONDS)
        scene_index = index - 1
        delay = int(((scene_index - 1) * SCENE_SECONDS + START_MARGIN) * 1000)
        label = f"v{scene_index}"
        filters.append(
            f"[{index}:a]atempo={speed:.6f},adelay={delay}|{delay}[{label}]"
        )
        labels.append(f"[{label}]")

    filters += [
        f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,volume=1.08,apad=whole_dur=130,asplit=2[voice_sc][voice_mix]",
        "[1:a]atempo=0.9796,atrim=duration=130,afade=t=out:st=126:d=4,volume=0.25[bgm]",
        "[bgm][voice_sc]sidechaincompress=threshold=0.012:ratio=12:attack=25:release=450[ducked]",
        "[ducked][voice_mix]amix=inputs=2:weights='1 1.15':normalize=0,alimiter=limit=0.95[aout]",
    ]
    command += [
        "-filter_complex", ";".join(filters),
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", "130", "-movflags", "+faststart", str(OUTPUT),
    ]
    subprocess.run(command, check=True)


def main() -> None:
    if not SOURCE.exists() or not BGM.exists():
        raise FileNotFoundError(SOURCE if not SOURCE.exists() else BGM)
    if len(LINES) != 13:
        raise ValueError("The 130-second video requires exactly 13 scene scripts.")
    files = asyncio.run(synthesize())
    render(files)
    print(OUTPUT)


if __name__ == "__main__":
    main()
