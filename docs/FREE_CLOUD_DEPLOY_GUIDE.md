# 🌐 CJ프레시웨이 세무 판례 AI 비서 - 무료 클라우드 원클릭 배포 가이드

본 문서는 사내 전용 서버 구축 권한이 없는 환경에서, **비용이 전혀 들지 않는 100% 영구 무료 클라우드(Streamlit Community Cloud 또는 Hugging Face Spaces)**를 활용하여 24시간 안정적으로 접속 가능한 웹 서비스를 구축하는 전체 절차를 안내합니다.

외부 클라우드 배포 시에도 사내 회계·세무 지식 보호를 위해 **아이디/비밀번호 보안 인증(Gatekeeper)**이 기본 적용되어 있습니다.

---

## 📌 무료 클라우드 플랫폼 비교

| 구분 | **Streamlit Community Cloud (권장 1순위)** | **Hugging Face Spaces (대안 2순위)** |
| :--- | :--- | :--- |
| **비용** | **완전 영구 무료 ($0)** | **완전 영구 무료 ($0)** |
| **메모리 / CPU** | 1GB RAM, 고속 글로벌 CDN | **16GB RAM, 2 vCPU** (대용량 메모리) |
| **보안 연결** | 무료 고유 HTTPS 도메인 (`*.streamlit.app`) | 무료 고유 HTTPS 도메인 (`*.hf.space`) |
| **배포 방식** | GitHub Private 저장소 연동 원클릭 자동 배포 | Git 푸시 또는 웹 드래그앤드롭 |
| **비밀키 관리** | 웹 대시보드 내 암호화 `Secrets` GUI 제공 | 웹 대시보드 내 `Repository Secrets` 제공 |
| **권장 대상** | 가장 빠르고 직관적인 배포를 원하는 경우 | 비공개 Space 또는 대용량 메모리가 필요한 경우 |

---

## 🚀 1단계: GitHub 비공개(Private) 저장소 생성 및 코드 업로드

Streamlit Cloud 배포를 위해 코드를 GitHub에 업로드합니다. 사내 코드 보안을 위해 반드시 **Private(비공개)**로 설정합니다.

### 1-1. GitHub에서 새 저장소 생성
1. [GitHub](https://github.com)에 로그인 후 우측 상단 **[+] ➜ [New repository]** 클릭
2. **Repository name**: `cj-tax-law-assistant` (원하는 이름 입력)
3. **공개 범위**: 반드시 **Private (비공개)** 선택
4. `Add .gitignore`나 `README` 체크는 해제한 상태로 **[Create repository]** 클릭

### 1-2. 로컬 프로젝트에서 Git 초기화 및 푸시 (PowerShell)
프로젝트 폴더(`tax_law_assistant`)에서 터미널을 열고 아래 명령어를 순서대로 실행합니다:

```powershell
# 1. Git 초기화
git init

# 2. 브랜치명을 main으로 지정
git branch -M main

# 3. .gitignore 확인 (.env 및 민감한 시크릿 파일은 이미 제외 처리되어 있습니다)
git status

# 4. 전체 파일 스테이징 및 커밋
git add .
git commit -m "feat: 세무 판례 AI 비서 무료 클라우드 배포 준비 완료"

# 5. GitHub 원격 저장소 연결 (본인의 GitHub 주소로 변경)
git remote add origin https://github.com/YOUR_GITHUB_ID/cj-tax-law-assistant.git

# 6. 푸시 실행
git push -u origin main
```

> [!TIP]
> `.gitignore` 파일에 `.env` 및 `secrets.toml`, 대용량 영상 파일이 등록되어 있으므로, 중요한 API 키나 비밀번호가 GitHub로 유출되지 않습니다.

---

## ☁️ 2단계: Streamlit Community Cloud 배포 (3분 완성)

### 2-1. Streamlit Cloud 로그인 및 앱 생성
1. [share.streamlit.io](https://share.streamlit.io/)에 접속하여 GitHub 계정으로 로그인합니다.
2. 메인 대시보드 우측 상단의 **[Create app]** 버튼을 클릭합니다.
3. 배포 옵션에서 **[Deploy a public/private app from GitHub]**를 선택합니다:
   - **Repository**: 방금 생성한 `YOUR_GITHUB_ID/cj-tax-law-assistant` 선택
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL**: 원하는 도메인 입력 (예: `cj-tax-assistant`)

### 2-2. API 키 및 로그인 계정 비밀번호 등록 (Secrets)
> [!IMPORTANT]
> **배포 전 반드시 Secrets를 입력해야 합니다!**

1. 설정 창 하단의 **[Advanced settings...]**를 클릭합니다.
2. **Secrets** 입력창에 프로젝트 내 [`.streamlit/secrets.toml.example`](file:///c:/Users/jongmin98/.gemini/antigravity/scratch/tax_law_assistant/.streamlit/secrets.toml.example) 내용을 복사하여 붙여넣고, 실제 키와 사용할 비밀번호로 수정합니다:

```toml
# 1. 국가법령정보센터 DRF API 키
LAW_API_KEY = "발급받은_법령센터_인증키"

# 2. ChatGPT Enterprise / OpenAI API 키
OPENAI_API_KEY = "sk-proj-..."
OPENAI_MODEL = "gpt-4o"

# 3. 보안 로그인 계정 및 비밀번호 설정 (아이디 = "비밀번호")
[passwords]
admin = "cj_tax_admin_2026!"
user = "cj_freshway_2026!"

# 4. 보안 로그인 활성화 플래그
AUTH_ENABLED = "true"
```

3. **[Save]**를 누른 뒤 **[Deploy!]** 버튼을 클릭합니다.

### 2-3. 배포 완료 확인
- 약 1~2분 후 빌드가 완료되며 고유 HTTPS URL(`https://cj-tax-assistant.streamlit.app`)로 접속됩니다.
- 접속 시 바로 본문이 보이지 않고 **CJ CI/BI 스타일의 보안 로그인 카드**가 나타납니다.
- `admin` / `cj_tax_admin_2026!`를 입력하여 정상 로그인을 확인합니다.

---

## 🔒 3단계: 보안 로그인 및 계정 관리 요령

### 3-1. 사용자 계정 추가 및 비밀번호 변경
사내 동료나 다른 실무자에게 계정을 추가로 발급하려면, Streamlit Cloud 대시보드에서:
1. 앱 우측 하단 **[Manage app] ➜ [Settings] ➜ [Secrets]** 메뉴로 이동합니다.
2. `[passwords]` 섹션에 원하는 계정과 비밀번호를 줄 단위로 추가합니다:
   ```toml
   [passwords]
   admin = "새로운_관리자_비밀번호!"
   tax_team1 = "실무자1_비밀번호!"
   audit_team = "감사팀_비밀번호!"
   ```
3. **[Save]**를 누르면 앱이 새로고침 없이 몇 초 안에 새 비밀번호를 자동 적용합니다.

### 3-2. 권한 체계
- **아이디에 `admin`이 포함된 계정**: 세무팀 관리자 권한 (모든 판례 검색, AI 검토, 지식 승인센터 관리, **데이터 백업 및 복원**)
- **그 외 일반 계정**: 실무 조회자 권한 (판례 검색, AI 검토, 가산세 계산기 활용)

---

## 💾 4단계: 클라우드 데이터 영속성 관리 (백업 & 복원)

무료 클라우드(Streamlit Cloud)는 리소스 절약을 위해 서버가 업데이트되거나 장기간 미사용 시 컨테이너가 재시작될 수 있습니다. 이때 로컬 파일이 초기화되는 것을 방지하기 위해 **원클릭 백업/복원 기능**을 내장했습니다.

### 백업 (다운로드) 방법
1. 시스템 상단 또는 사이드바에서 **[⚙️ 시스템 설정]** 메뉴로 이동합니다.
2. **`💾 4. 데이터 백업 및 복원 (클라우드 영속성)`** 탭을 클릭합니다.
3. **[📦 전체 데이터 백업 ZIP 다운로드]** 버튼을 클릭하여 현재까지 축적된 검토 이력(`review_history.db`)과 관심 판례 보관함(`saved_cases.json`)을 내 컴퓨터에 안전하게 저장합니다.

### 복원 (업로드) 방법
1. 앱이 재배포되었거나 데이터를 복구해야 할 때, **`admin` 계정으로 로그인**합니다.
2. **[⚙️ 시스템 설정 ➜ 4. 데이터 백업 및 복원]** 탭으로 이동합니다.
3. **[백업 ZIP 파일 선택]**에 보관해 둔 zip 파일을 업로드한 후 **[복원 실행]**을 클릭하면 즉시 모든 과거 검토 이력과 승인 지식이 1초 만에 원상 복구됩니다.

---

## 💡 대안: Hugging Face Spaces로 배포하는 경우

만약 회사 정책상 GitHub 저장소를 공개할 수 없거나 16GB의 더 큰 메모리가 필요한 경우:
1. [huggingface.co](https://huggingface.co) 회원가입 및 로그인
2. **[New Space]** 클릭 ➜ Space SDK로 **Streamlit** 선택
3. Space 권한을 **Private**으로 설정
4. Space Settings ➜ **Variables and secrets** 메뉴에서 `LAW_API_KEY`, `OPENAI_API_KEY`, `AUTH_USERS_JSON` 등록
5. 로컬 터미널에서 `git remote add space https://huggingface.co/spaces/YOUR_ID/YOUR_SPACE` 후 `git push space main`으로 배포 완료
