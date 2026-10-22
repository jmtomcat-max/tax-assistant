# TAX ASSISTANT presentation trigger

When the user says exactly `발표 시작해`:

1. Reply in Korean: `네. 지금부터 TAX ASSISTANT를 소개하겠습니다.`
2. Immediately run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\presentation_launcher\start_presentation.ps1` from this repository root.
3. The script opens the approved `presentation_launcher\media\TAX_ASSISTANT_NEW_NARRATED_SUNHI.mp4` directly in VLC with native full-screen and play-and-exit options. Do not use a browser, HTML page, Windows Media Player, or simulated keyboard input. Do not modify, rebuild, or substitute the video.
4. VLC enters full screen automatically and closes when playback ends. Do not perform a second full-screen action.

For any other request, follow the normal project workflow.
