# 사내 AX 공모전 제출용: ChatGPT Enterprise (Azure OpenAI / GPT-4o) AI 엔진 전환 완료 보고서

회사의 **ChatGPT 엔터프라이즈(Azure OpenAI / GPT-4o) 기반 AX 공모전 규격**에 부합하도록, AI 엔진 아키텍처 및 전 UI 브랜딩을 성공적으로 전환하였습니다.

---

## 🏛️ 주요 전환 및 업그레이드 내역

### 1. 🤖 ChatGPT Enterprise (Azure OpenAI & OpenAI) 듀얼 엔진 탑재
- `summarizer.py` 내 모든 AI 엔진을 **ChatGPT Enterprise (GPT-4o)**로 전면 교체 완료하였습니다:
  1. **사실관계 7대 요소 구조화 추출** (`analyze_tax_situation`)
  2. **다중 문서/계약서 조항별 독소조항 스캔 & 권고 수정안 도출** (`analyze_document_situation`)
  3. **공식 판례 DB 매칭 종합 세무의견서 생성** (`generate_situation_briefing`)
  4. **개별 판례 5대 섹션 심층 분석** (`summarize_case`)
  5. **원문 미제공 예규 판결요지 추출** (`generate_ruling_summary`)
  6. **세무 맥락 기반 후속 Q&A 챗봇** (`generate_followup_answer`)
  7. **문맥 기반 고지능 판례 하이브리드 재정렬** (`rerank_cases_with_ai`)

### 2. 📄 차세대 멀티포맷 문서 파서 (PDF, DOCX, TXT, CSV, 이미지)
- `pypdf`를 탑재하여 계약서 PDF의 페이지별 텍스트를 정확히 추출하여 조항별 세무 리스크 및 권고 수정안을 도출합니다.
- 이미지 파일(.png, .jpg, .jpeg, .webp)은 GPT-4o의 고해상도 Vision API로 전달되어 문서 스캔본과 영수증도 다각도로 분석합니다.

### 3. 🎨 UI 및 사내 엔터프라이즈 브랜딩 전면 개편
- 사이드바 인프라 상태창: **`● ChatGPT Enterprise (연결)`** 또는 **`○ ChatGPT Enterprise (미설정)`**으로 실시간 연동 상태 표시
- 뷰어 및 검색 탭: `🤖 ChatGPT Enterprise 5단 실무 분석 리포트`, `✨ CHATGPT ENTERPRISE 맞춤 세무 진단 솔루션`
- 시스템 설정 창: `ChatGPT Enterprise (Azure OpenAI / GPT-4o)` 연동 상태 및 배포명(Deployment Name), 엔드포인트 마스킹 표출

---

## 🔑 사내 Azure OpenAI API 설정 방법 (`.env`)

공모전 심사 및 사내 시연을 위해 발급받으신 Azure OpenAI 정보를 프로젝트 루트의 [`.env`](file:///c:/Users/jongmin98/.gemini/antigravity/scratch/tax_law_assistant/.env) 파일에 입력해 주시면 즉시 작동합니다.

### [사내 Azure OpenAI 사용 시]
```ini
AZURE_OPENAI_ENDPOINT=https://your-company-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_azure_api_key_here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

### [일반 OpenAI 사용 시 (선택)]
```ini
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o
```

> [!TIP]
> 키를 입력하지 않은 상태에서도 기존 Gemini 키가 남아있으면 시스템이 중단 없이 자동 폴백하여 시연이 유지되며, **Azure OpenAI 키를 넣는 즉시 사내 ChatGPT Enterprise 엔진으로 우선 활성화**됩니다.

---

## 🌐 접속 주소 안내

- **사내 로컬 접속 주소**: [http://localhost:8501](http://localhost:8501)
- **외부 공유 데모 주소 (Cloudflare Tunnel)**: [https://appeals-nyc-indicate-sparc.trycloudflare.com](https://appeals-nyc-indicate-sparc.trycloudflare.com)
