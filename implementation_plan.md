# 세무·조세 판례/예규 AI 검색 및 요약 비서 구축 계획

국가법령정보센터(law.go.kr)의 판례·행정해석·심판례 Open API와 AI(Gemini)를 연동하여, 키워드 검색 한 번으로 관련 세무 판례/예규를 수집하고 핵심 쟁점(과세관청 vs 납세자, 결론, 실무 시사점)을 자동 요약해 주는 실무 도구를 제작합니다.

## User Review Required

> [!IMPORTANT]
> **국가법령정보센터 API 키 발급 여부**
> - 국가법령정보센터 Open API는 [open.law.go.kr](https://open.law.go.kr)에서 누구나 무료로 1분 만에 발급받을 수 있습니다.
> - **API 키가 아직 없으셔도 바로 프로그램을 체험해보실 수 있도록**, 프로그램 내에 "샘플(모의) 데이터 모드"와 "실제 API 모드"를 둘 다 지원하도록 구현하겠습니다.

## Proposed Changes

프로젝트 디렉토리: `C:\Users\jongmin98\.gemini\antigravity\scratch\tax_law_assistant`

### 1. 백엔드 & API 연동 모듈

#### [NEW] `law_api.py`
- 국가법령정보센터 Open API(`DRF` 서비스) 클라이언트
- 검색 대상:
  - 조세 판례 (대법원, 하급심)
  - 조세심판원 결정례 / 행정심판례
  - 법령해석례 (기획재정부·국세청 질의회신 및 예규)
- 검색 키워드, 결과 건수, 정렬(최신순 등) 파라미터 처리
- API 키 미입력 시 테스트용 실무 샘플 데이터(예: "가지급금 인정이자", "주식매수선택권 행사이익", "가업상속공제") 반환 기능

#### [NEW] `summarizer.py`
- 수집된 판례/예규 본문 분석 프롬프트
- 구조화 요약:
  1. **사건 개요 및 핵심 쟁점**
  2. **과세관청 입장 vs 납세자(청구인) 주장**
  3. **판결/결정 요지 (인용 / 기각)**
  4. **회계·세무 실무자 관점의 체크포인트/시사점**

---

### 2. 웹 대시보드 UI (Streamlit)

#### [NEW] `app.py`
- **사이드바**:
  - API Key 입력창 (법제처 API Key, Gemini API Key 입력 지원 / 미입력 시 모의 테스트 모드 활성화)
  - 검색 구분 선택 (전체, 법원 판례, 조세심판원 결정례, 국세청/기재부 법령해석)
  - 조회 건수 설정 (기본 5건~20건)
- **메인 화면**:
  - 검색어 입력창 (예: `"법인세 손금산입"`, `"부가가치세 사실과 다른 세금계산서"`, `"가지급금"`)
  - 검색 결과 카드 뷰 (사건명, 사건번호, 선고일자/생산일자, 법원/처분청)
  - 원문 보기 토글 & **AI 원클릭 분석 버튼**
  - AI 분석 결과 카드 (핵심 쟁점 비교표, 실무 체크리스트)
  - 엑셀(Excel) 및 마크다운 보고서 다운로드 기능

---

### 3. 프로젝트 설정

#### [NEW] `requirements.txt`
- `streamlit`
- `requests`
- `pandas`
- `openpyxl`
- `google-genai`

## Verification Plan

### Automated / Command Verification
1. 파이썬 가상환경 생성 및 의존성 설치 검증:
   ```powershell
   python -m venv venv
   .\venv\Scripts\pip install -r requirements.txt
   ```
2. API 연동 및 모의 데이터 응답 테스트 스크립트 실행.

### Manual Verification
1. `streamlit run app.py` 명령으로 로컬 웹 서버 구동 (기본 포트: 8501).
2. 브라우저에서 키워드 검색 테스트 ("가지급금 인정이자", "스타트업 스톡옵션" 등).
3. 판례 리스트 정상 표출 및 AI 요약 생성 확인.
4. 엑셀 다운로드 동작 검증.
