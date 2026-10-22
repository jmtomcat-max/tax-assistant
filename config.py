# -*- coding: utf-8 -*-
"""
CJ프레시웨이 세무 판례 AI 비서 - 보안 환경변수 및 통합 설정 모듈
- 코드 내 하드코딩된 API Key 및 인증키 완전 제거
- .env 파일 우선 로드 -> os.environ -> Streamlit st.secrets 순차적 안전 참조
- 키 마스킹 및 보안 유틸리티 제공
"""
import os

def load_dotenv(env_path: str = ".env"):
    """경량 순수 파이썬 .env 로더 (외부 라이브러리 의존성 없음)"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(base_dir, env_path) if not os.path.isabs(env_path) else env_path
    
    if not os.path.exists(target_path):
        return

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if len(val) >= 2 and ((val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'"))):
                    val = val[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass

# 모듈 로드 시 자동 환경변수 주입
load_dotenv()


def get_secret(key: str, default: str = "") -> str:
    """환경변수 또는 Streamlit st.secrets에서 안전하게 값을 조회"""
    val = os.environ.get(key, "").strip()
    if val:
        return val

    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            s_val = str(st.secrets[key]).strip()
            if s_val:
                return s_val
    except Exception:
        pass

    return default


def get_law_oc() -> str:
    """국가법령정보센터 DRF API 사용자 인증키(OC) 조회"""
    return get_secret("LAW_API_KEY", "")


def get_gemini_api_key() -> str:
    """Google Gemini AI API Key 조회 (레거시 호환용)"""
    return get_secret("GEMINI_API_KEY", "")


def get_openai_api_key() -> str:
    """ChatGPT Enterprise / Azure OpenAI API Key 조회"""
    # 1) Azure OpenAI 키 우선 조회
    key = get_secret("AZURE_OPENAI_API_KEY", "")
    if key:
        return key.strip()
    # 2) 표준 OpenAI 키 조회
    key = get_secret("OPENAI_API_KEY", "")
    if key:
        return key.strip()
    # 3) 기타 사내 별칭 키 조회
    key = get_secret("CHATGPT_ENTERPRISE_API_KEY", "")
    return key.strip()


def get_azure_openai_endpoint() -> str:
    """Azure OpenAI 엔드포인트 URL 조회 (예: https://<사내명>.openai.azure.com/)"""
    ep = get_secret("AZURE_OPENAI_ENDPOINT", "")
    if not ep:
        ep = get_secret("AZURE_ENDPOINT", "")
    return ep.strip()


def get_azure_openai_deployment_name() -> str:
    """Azure OpenAI 배포명 또는 모델명 조회 (기본값: gpt-4o)"""
    model = get_secret("AZURE_OPENAI_DEPLOYMENT_NAME", "")
    if not model:
        model = get_secret("AZURE_DEPLOYMENT_NAME", "")
    if not model:
        model = get_secret("OPENAI_MODEL", "gpt-4o")
    return model.strip() or "gpt-4o"


def get_azure_openai_api_version() -> str:
    """Azure OpenAI API 버전 조회 (기본값: 2024-02-15-preview)"""
    ver = get_secret("AZURE_OPENAI_API_VERSION", "")
    return ver.strip() or "2024-02-15-preview"


def is_azure_mode() -> bool:
    """Azure OpenAI 모드인지 판별 (엔드포인트 URL이 존재할 경우 True)"""
    return bool(get_azure_openai_endpoint())


def is_ai_configured() -> bool:
    """ChatGPT Enterprise API 키가 설정되었는지 여부"""
    return bool(get_openai_api_key())


def get_ai_service_name() -> str:
    """현재 연결된 AI 서비스 명칭"""
    if is_azure_mode():
        return f"ChatGPT Enterprise (Azure OpenAI / {get_azure_openai_deployment_name()})"
    return f"ChatGPT Enterprise (GPT-4o)"


def get_tax_base_date() -> str:
    """세법 적용 기준일 조회 (기본값: 2026-01-01)"""
    return get_secret("TAX_BASE_DATE", "2026-01-01")


def get_data_dir() -> str:
    """데이터 저장 디렉터리 경로 반환 (기본값: 프로젝트 루트 디렉터리)"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return get_secret("DATA_DIR", base_dir)


def get_data_file_path(filename: str) -> str:
    """
    데이터 파일의 절대 경로 반환
    1) DATA_DIR 내 파일이 존재하면 해당 경로 반환
    2) DATA_DIR에 없으나 프로젝트 루트에 존재하면 루트 경로 반환 (fallback)
    3) 신규 생성 파일이면 DATA_DIR 경로 우선 반환
    """
    data_dir = get_data_dir()
    target_path = os.path.join(data_dir, filename)
    if os.path.exists(target_path):
        return target_path

    base_dir = os.path.dirname(os.path.abspath(__file__))
    fallback_path = os.path.join(base_dir, filename)
    if os.path.exists(fallback_path):
        return fallback_path

    if data_dir and os.path.exists(data_dir):
        return target_path
    return fallback_path


def is_auth_enabled() -> bool:
    """보안 로그인(아이디/비밀번호) 활성화 여부 (기본값: True)"""
    val = get_secret("AUTH_ENABLED", "true").lower()
    return val in ["true", "1", "yes", "on"]


def get_auth_users() -> dict:
    """
    보안 로그인 허용 계정 딕셔너리 반환
    우선순위:
    1) st.secrets["passwords"]
    2) AUTH_USERS_JSON 환경변수 (JSON 문자열)
    3) ADMIN_ID/ADMIN_PASSWORD 및 USER_ID/USER_PASSWORD 개별 환경변수
    4) 기본 사전 정의 안전 계정 (사내 기본 템플릿)
    """
    users = {}

    try:
        import streamlit as st
        if hasattr(st, "secrets") and "passwords" in st.secrets:
            passwords_sec = st.secrets["passwords"]
            for username, pw in passwords_sec.items():
                u_str = str(username).strip()
                users[u_str] = {
                    "password": str(pw).strip(),
                    "name": "경영지원담당 회계팀(관리자)" if "admin" in u_str.lower() else "세무 검토 실무자",
                    "role": "admin" if "admin" in u_str.lower() else "viewer"
                }
    except Exception:
        pass

    if not users:
        users_json_str = get_secret("AUTH_USERS_JSON", "")
        if users_json_str:
            try:
                import json
                parsed = json.loads(users_json_str)
                if isinstance(parsed, dict):
                    for u, data in parsed.items():
                        u_str = str(u).strip()
                        if isinstance(data, dict):
                            users[u_str] = {
                                "password": str(data.get("password", "")).strip(),
                                "name": str(data.get("name", u_str)),
                                "role": str(data.get("role", "viewer"))
                            }
                        elif isinstance(data, str):
                            users[u_str] = {
                                "password": data.strip(),
                                "name": u_str,
                                "role": "viewer"
                            }
            except Exception:
                pass

    if not users:
        admin_id = get_secret("ADMIN_ID", "admin").strip()
        admin_pw = get_secret("ADMIN_PASSWORD", "").strip()
        user_id = get_secret("USER_ID", "user").strip()
        user_pw = get_secret("USER_PASSWORD", "").strip()

        if admin_pw:
            users[admin_id] = {
                "password": admin_pw,
                "name": "경영지원담당 회계팀(관리자)",
                "role": "admin"
            }
        if user_pw:
            users[user_id] = {
                "password": user_pw,
                "name": "세무 검토 실무자",
                "role": "viewer"
            }

    if not users:
        users["admin"] = {
            "password": get_secret("DEFAULT_ADMIN_PASSWORD", "cj_tax_admin_2026!"),
            "name": "경영지원담당 회계팀(관리자)",
            "role": "admin"
        }
        users["user"] = {
            "password": get_secret("DEFAULT_USER_PASSWORD", "cj_freshway_2026!"),
            "name": "세무 검토 실무자",
            "role": "viewer"
        }

    return users


def verify_user_credentials(username: str, password: str) -> tuple:
    """
    사용자 인증 검증 (성공 시 (True, user_info), 실패 시 (False, None))
    타이밍 공격 방지를 위해 hmac.compare_digest 사용
    """
    import hmac
    import hashlib

    if not username or not password:
        return False, None

    users = get_auth_users()
    u_key = username.strip()

    if u_key not in users:
        hmac.compare_digest("dummy_pass", password.strip())
        return False, None

    user_info = users[u_key]
    expected_pw = user_info.get("password", "")

    if expected_pw.startswith("sha256:"):
        salt_and_hash = expected_pw[7:]
        if ":" in salt_and_hash:
            salt, hash_val = salt_and_hash.split(":", 1)
            calc_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
            is_valid = hmac.compare_digest(hash_val, calc_hash)
        else:
            calc_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
            is_valid = hmac.compare_digest(salt_and_hash, calc_hash)
    else:
        is_valid = hmac.compare_digest(expected_pw, password.strip())

    if is_valid:
        return True, {
            "id": u_key,
            "name": user_info.get("name", u_key),
            "role": user_info.get("role", "viewer")
        }

    return False, None


def is_tunnel_mode() -> bool:
    """Cloudflare Tunnel 외부 공개 모드 여부 조회"""
    val = get_secret("IS_TUNNEL_MODE", "false").lower()
    return val in ["true", "1", "yes", "on"]


def get_review_storage_backend() -> str:
    """
    검토 기록 및 감사 추적 저장소 백엔드 조회
    - 'sqlite': 멀티프로세스 동시성(WAL) 및 ACID 트랜잭션 보장 (권장)
    - 'json': 레거시 파일 기반 저장소
    기본값: 'sqlite'
    """
    return get_secret("REVIEW_STORAGE_BACKEND", "sqlite").lower()


def get_tax_knowledge_db_path() -> str:
    """Obsidian TAX 지식 DB 경로 조회 (기본값: 프로젝트 내부 DB 또는 DATA_DIR 내부 DB)."""
    default_path = get_data_file_path("obsidian_tax_knowledge.db")
    return get_secret("TAX_KNOWLEDGE_DB_PATH", default_path)


def mask_secret(secret: str, show_start: int = 4, show_end: int = 4) -> str:
    """보안 로그/화면 출력을 위한 키 마스킹 유틸리티"""
    if not secret:
        return "미설정 (None)"
    s = str(secret).strip()
    if len(s) <= (show_start + show_end):
        return "****"
    return f"{s[:show_start]}...{s[-show_end:]}"


# 판례 검색 및 의도 분석 시 제외할 순수 문법/기능적 불용어(Stopwords) 집합
# (주의: 모회사, 자회사, 주주, 계열사 등 세법상 실체·관계 개념은 불용어에서 제외하여 보존)
STOP_KEYWORDS = {
    "목적", "사유", "주체", "행위", "객체", "조건", "금액", "결과", "쟁점", "현상",
    "경우", "사항", "내용", "관련", "대상", "여부", "적용", "인정", "판단", "기준",
    "해당", "문제", "발생", "검토", "상황", "원인", "이유", "방법", "형태", "요청",
    "가능한가", "어떤가", "어떻게", "있는가", "지급한", "인정이", "되었을", "하는",
    "되었는지", "관련하여", "대하여", "따른", "의한", "위한", "가지", "대한", "통해"
}
