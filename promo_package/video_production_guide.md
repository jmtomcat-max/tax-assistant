# 📦 TAX ASSISTANT 사내 홍보영상 제작 패키지 가이드 (75초)

본 문서는 사내 발표 및 홍보 영상 제작을 위한 편집 타임라인, BGM/SFX 음향 사양, 사용 에셋 목록, 그리고 최종 렌더링을 손쉽게 완료하기 위한 원스톱 프로덕션 가이드입니다.

---

## 1. 영상 스펙 요약 (Technical Specifications)

* **해상도**: 1920 × 1080 (FHD, 16:9 Cinema Aspect Ratio)
* **프레임레이트**: 30fps 또는 60fps (UI 줌/슬라이드 시 60fps 권장)
* **총 러닝타임**: **75.0초 (01:15)**
* **비디오 포맷**: MP4 (H.264 / AAC)
* **비주얼 톤앤매너**: Enterprise SaaS, Deep Blue & Slate Gray Palette, Dark Mode Accent, Apple Keynote Style Smooth Zoom & Transitions

---

## 2. BGM 및 효과음(SFX) 연출 방향

### [BGM 트랙 구성 가이드]
* **장르**: Cinematic Minimal Ambient & Smart Corporate Tech
* **레퍼런스 무드**: Max Richter 스타일의 미니멀 피아노 아르페지오 + 현대적 펄스 비트 (Linear, Notion, Apple Keynote B2B 발표 영상 스타일)
* **추천 무료/사내 라이브러리 검색 키워드**:
  * *Corporate Technology, Minimal Ambient Pulse, Trustworthy Finance, Inspiring Innovation, Modern SaaS*

| 구간 | 음악 전개 (Dynamics) | 분위기 및 악기 구성 |
| :--- | :--- | :--- |
| **00:00 ~ 00:10** (Scene 1) | **Intriguing / Subdued** | 차분하고 긴장감이 도는 로우 피아노, 서늘한 패드 사운드로 흩어진 문제점 묘사 |
| **00:10 ~ 00:18** (Scene 2) | **Clarity / Impact** | 부드러운 스위핑 사운드와 함께 피아노 코드 체인지, 정갈한 킥 드럼 등장 |
| **00:18 ~ 00:40** (Scene 3) | **Driving / Intelligent** | 속도감 있는 펄스 베이스와 가벼운 하이햇, 스마트하고 효율적인 분위기 조성 |
| **00:40 ~ 00:58** (Scene 4~5)| **Steady / Trustworthy** | 안정적이고 묵직한 베이스 전개, 아카이브와 지식이 착실히 쌓이는 느낌 |
| **00:58 ~ 01:08** (Scene 6) | **Climax / Expanding** | 신스 패드가 넓게 펼쳐지며 지식 DB의 확장성과 사내 전사적 자산화 강조 |
| **01:08 ~ 01:15** (Scene 7) | **Resolve / Grand Ending** | 명확한 피아노 끝음과 함께 여운을 남기는 서라운드 리버브 테일 |

### [SFX 효과음 큐시트]
1. **(00:02) UI 팝업음 (Soft Pop/Click)**: 흩어진 브라우저 창 3개가 차례로 뜰 때 미세한 팝 사운드
2. **(00:10) 스위시/흡입음 (Deep Whoosh/Swoosh)**: 복잡한 창들이 사라지고 Tax Assistant 로고가 중앙에 집중될 때
3. **(00:19) 키보드 타이핑음 (Mechanical Type Sound)**: 검색창에 질문이 2초간 타이핑되는 사운드
4. **(00:23) 스캔/처리음 (Digital Shimmer/Scan)**: AI가 사실관계를 분해하고 판례 DB를 탐색하는 찰나의 효과음
5. **(00:26) 2단 대조 강조음 (Double Ding/Thud)**: 국세청 논거(좌)와 납세자 논거(우) 카드가 차례로 줌인될 때
6. **(00:34) 체크마크음 (Clean Check/Click)**: 필수 증빙 체크리스트에 녹색 체크가 붙는 사운드
7. **(00:41) 카드 슬라이드음 (Smooth Slide)**: 검토 결과가 Review History 최상단 카드로 안착될 때
8. **(00:52) 북마크 클릭음 (Soft Bookmark Click)**: 보관함(Vault) 아이콘 활성화음
9. **(01:00) 네트워크 펄스음 (Ambient Data Pulse)**: Knowledge DB 중앙 노드가 박동하며 연결선이 빛날 때
10. **(01:12) 시그니처 차임음 (Corporate Chime)**: 엔딩 로고가 최종 고정될 때 신뢰감을 주는 종소리/차임

---

## 3. 영상 편집 타임라인 (Multi-Track Timeline Guide)

```
[Time]  00:00       00:10       00:18                 00:40       00:50       00:58       01:08  01:15
Track V1 [Scene 1:문제] [Scene 2:솔루션] [Scene 3: 세무 검토]       [Scene 4:이력] [Scene 5:보관] [Scene 6:지식] [Scene 7:엔딩]
Track V2 [블러 오버레이] [로고 글로우]   [좌우 2단 대조 줌인]      [신규카드 펄스] [메모 하이라이트] [데이터 연결모션] [슬로건 페이드]
Track A1 [차분한 인트로] [비트 전환]    [경쾌한 스마트 펄스 BGM]   [깊이감 전개]   [클라이맥스 고조]       [그랜드 엔딩]
Track A2 [창 팝업 SFX]  [스우시 SFX]    [타이핑/스캔/체크 SFX]    [슬라이드 SFX]  [클릭 SFX]     [펄스 SFX]     [차임 SFX]
Track A3 [Narration 1] [Narration 2]   [Narration 3]           [Narration 4]  [Narration 5]  [Narration 6]  [Narration 7]
Track Sub [자막 01~05]  [자막 06~07]    [자막 08~11]            [자막 12~13]   [자막 14]      [자막 15~17]   [자막 18]
```

### [트랙별 상세 구성]
* **V1 (Main Video/UI)**: 각 씬별 16:9 프레임 캡처 또는 영상 클립 배치
* **V2 (Overlays & Motion)**: 텍스트 박스, 확대 크롭(Zoom-in), 포커스 마스크, UI 마우스 커서 이동
* **A1 (BGM)**: 배경음악 트랙 (나레이션 음성과 겹칠 때 **Auto-Ducking -14dB** 적용)
* **A2 (SFX)**: 씬 전환 및 버튼 클릭 인터랙션 효과음 (-6dB ~ -10dB)
* **A3 (Narration)**: 보컬 음성 트랙 (-1dB ~ -3dB, 명료한 컴프레서 및 De-esser 처리)
* **Sub (Subtitles)**: 제공된 `subtitles.srt`를 1클릭 임포트

---

## 4. 에셋 목록 (Assets Checklist)

| 에셋 ID | 파일 유형 | 설명 및 위치 |
| :--- | :--- | :--- |
| **AST-UI-01** | UI HTML/Canvas | Scene 1: 흩어진 법령/예규/엑셀 윈도우 그래픽 |
| **AST-UI-02** | UI Mockup | Scene 2: Tax Assistant 메인 검색 홈 (`render_search_view`) |
| **AST-UI-03A**| UI Mockup | Scene 3: 자연어 세무 질의 입력창 포커스 |
| **AST-UI-03B**| UI Mockup | Scene 3: 국세청 과세논거 vs 납세자 방어논리 2단 대조 카드 |
| **AST-UI-03C**| UI Mockup | Scene 3: 세무조사 대비 4대 필수 증빙 체크리스트 |
| **AST-UI-04** | UI Mockup | Scene 4: Review History KPI 대시보드 및 누적 검토 카드 리스트 |
| **AST-UI-05** | UI Mockup | Scene 5: 선별 보관함(Vault) 쟁점 태그 및 사용자 실무 메모 카드 |
| **AST-UI-06** | Motion Graphic | Scene 6: Tax Review Knowledge DB 중앙 허브 및 오빗 노드 연결 인포그래픽 |
| **AST-UI-07** | Brand Graphic | Scene 7: TAX ASSISTANT 공식 로고 및 엔딩 슬로건 |
| **AST-SUB-01**| Text/SRT | `subtitles.srt` (표준 자막 파일) |
| **AST-NAR-01**| Text/Script | `narration_guide.txt` (한국어 전문 나레이션 대본) |
| **AST-SIM-01**| Web App | `interactive_preview.html` (75초 풀 시뮬레이터) |

---

## 5. 가장 적은 작업으로 최종 영상을 완성하는 3가지 렌더링 방법

### [방법 1: Vrew (가장 추천 — 5분 완성)]
1. [Vrew 프로그램](https://vrew.voyagerx.com/)을 실행합니다.
2. **[자막 파일로 시작하기]**를 누르고 `promo_package/subtitles.srt`를 불러옵니다.
3. Vrew의 **[AI 목소리 삽입]** 기능을 클릭하여 신뢰감 있는 톤(예: 아나운서 '민서' 또는 '준우')을 선택하면 대본 타이밍에 맞춰 초정밀 한국어 나레이션이 1초 만에 자동 생성됩니다.
4. 각 씬 구간에 `promo_package/interactive_preview.html`을 전체화면 캡처한 이미지나 영상 클립을 배치합니다.
5. **[내보내기 -> MP4]**를 누르면 1080p 고화질 영상이 즉시 렌더링됩니다.

### [방법 2: CapCut (모션/효과 최적화 — 10분 완성)]
1. CapCut을 실행하고 16:9 프로젝트를 생성합니다.
2. 텍스트 탭에서 `subtitles.srt`를 임포트하여 자동 자막 스타일을 모던하게 지정합니다.
3. 비디오 트랙에 각 씬별 화면을 배치하고, **[애니메이션 -> 줌인(Zoom-in) / 슬라이드]**를 적용합니다.
4. BGM 검색창에 `Minimal Corporate Tech`를 검색하여 배경음악을 깔고 오토 더킹(Auto-Ducking)을 활성화합니다.
5. 렌더링(Export)을 눌러 MP4로 추출합니다.

### [방법 3: 브라우저 실시간 녹화 (별도 프로그램 설치 불필요 — 2분 완성)]
1. 크롬이나 엣지에서 `promo_package/interactive_preview.html`을 엽니다.
2. `F11`을 눌러 브라우저 전체화면 모드로 전환합니다.
3. 윈도우 기본 녹화 기능(`Win + Alt + R` 또는 OBS/캡처 도구)을 켭니다.
4. `Space` 바를 눌러 75초 시뮬레이터를 재생하면 완벽한 타이밍의 씬 전환과 자막이 실시간으로 녹화됩니다.
5. 녹화를 종료하면 즉시 MP4 파일이 완성됩니다.
