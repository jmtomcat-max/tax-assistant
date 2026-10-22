# -*- coding: utf-8 -*-
"""
국가법령정보센터(law.go.kr) 공식 Open API 실시간 연동 모듈
- 인증키: config.get_law_oc() 환경변수 연동
- 실시간 판례, 국세법령정보시스템 연계 판결/결정례 검색
"""
import requests
import xml.etree.ElementTree as ET
import re
import urllib.parse
import logging
import concurrent.futures
import threading
from typing import List, Dict, Any, Optional

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 공용 안정 세션 생성 (Max retries exceeded 방지 및 연결 풀링)
_SESSION = requests.Session()
_retries = Retry(
    total=3,
    backoff_factor=0.3,
    status_forcelist=[500, 502, 503, 504],
    raise_on_status=False
)
_adapter = HTTPAdapter(max_retries=_retries, pool_connections=30, pool_maxsize=30)
_SESSION.mount("https://", _adapter)
_SESSION.mount("http://", _adapter)
_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

# 상세 판례/결정례 인메모리 캐시 (동일 세션 중복 네트워크 호출 0ms 방지)
_PREC_DETAIL_CACHE: Dict[str, Dict[str, Any]] = {}

# 4대 표준 API 오류 분류 상수
ERR_NO_RESULTS = "NO_RESULTS"            # 검색 결과 없음
ERR_AUTH_ERROR = "AUTH_ERROR"            # API 인증 오류
ERR_NETWORK_ERROR = "NETWORK_ERROR"      # 네트워크 오류
ERR_PARSE_ERROR = "PARSE_ERROR"          # 검색 응답 형식 오류
MAX_PRIMARY_QUERIES = 4
MAX_RESCUE_QUERIES = 1

ERROR_CATEGORY_NAMES = {
    ERR_NO_RESULTS: "검색 결과 없음",
    ERR_AUTH_ERROR: "API 인증 오류",
    ERR_NETWORK_ERROR: "네트워크 오류",
    ERR_PARSE_ERROR: "검색 응답 형식 오류"
}


def _has_network_error(errors: list) -> bool:
    return any(error.get("error_type") == ERR_NETWORK_ERROR for error in errors or [])

DRF_SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
DRF_SERVICE_URL = "https://www.law.go.kr/DRF/lawService.do"
import config
DEFAULT_OC = config.get_law_oc()

def _record_error(error_list: Optional[list], err_type: str, message: str, query: str = "", target: str = ""):
    """API 호출 중 발생한 오류를 유형별로 수집하고 안전하게 로깅합니다."""
    err_info = {
        "error_type": err_type,
        "category": ERROR_CATEGORY_NAMES.get(err_type, err_type),
        "message": message,
        "query": query,
        "target": target
    }
    if error_list is not None:
        error_list.append(err_info)
    logging.getLogger(__name__).warning(
        f"[DRF API 오류] [{err_info['category']}] {message} (query: '{query}', target: '{target}')"
    )


def _determine_final_error(api_errors: list) -> tuple:
    """수집된 API 에러 목록을 분석하여 최종 4대 에러 유형(type, category, msg)을 판별합니다."""
    if not api_errors:
        return (ERR_NO_RESULTS, ERROR_CATEGORY_NAMES[ERR_NO_RESULTS], "입력하신 조건에 부합하는 공식 판례가 없습니다.")

    auth_errs = [e for e in api_errors if e.get("error_type") == ERR_AUTH_ERROR]
    net_errs = [e for e in api_errors if e.get("error_type") == ERR_NETWORK_ERROR]
    parse_errs = [e for e in api_errors if e.get("error_type") == ERR_PARSE_ERROR]

    if auth_errs:
        return (ERR_AUTH_ERROR, ERROR_CATEGORY_NAMES[ERR_AUTH_ERROR], auth_errs[0]["message"])
    elif net_errs:
        # 단일 보조 채널(ntsCgmExpc 등)만의 에러는 제외하고, 핵심 채널(판례, 심판례, 복합 검색) 에러 위주로 최종 판정
        core_net_errs = [e for e in net_errs if e.get("target") in ("prec", "ttSpecialDecc", "drf_multi")]
        if core_net_errs:
            return (ERR_NETWORK_ERROR, ERROR_CATEGORY_NAMES[ERR_NETWORK_ERROR], core_net_errs[0]["message"])
        # 만약 보조 채널만의 일시적 이슈였다면 정상적인 '검색 결과 없음'으로 우아하게 폴백
        return (ERR_NO_RESULTS, ERROR_CATEGORY_NAMES[ERR_NO_RESULTS], "입력하신 조건에 부합하는 공식 판례가 없습니다.")
    elif parse_errs:
        return (ERR_PARSE_ERROR, ERROR_CATEGORY_NAMES[ERR_PARSE_ERROR], parse_errs[0]["message"])
    else:
        return (ERR_NO_RESULTS, ERROR_CATEGORY_NAMES[ERR_NO_RESULTS], "검색 결과가 없습니다.")

STRONG_TAX_TERMS = {
    "손금산입", "손금불산입", "익금산입", "익금불산입", "경정청구", "환급가산금",
    "국세환급금", "장애인고용부담금", "판매장려금", "부당행위계산", "부당행위계산부인",
    "업무무관", "대손금", "접대비", "세금계산서", "매입세액", "공동경비", "가지급금",
    "인정이자", "원천징수", "고유목적사업준비금", "감가상각비", "상표권", "사용료"
}

QUERY_SYNONYMS = {
    # 1. 합병·기업구조조정 전문 도메인 동의어 (국가법령센터 판례 색인 최적화)
    "무증자합병": ["완전자회사 합병", "합병신주", "포합주식 합병", "합병대가 주식", "피합병법인 주식", "무증자 합병", "간이합병"],
    "무증자": ["완전자회사 합병", "합병신주", "포합주식", "신주 미교부", "무증자 합병"],
    "포합주식": ["포합주식 합병", "포합주식", "합병대가 주식", "합병신주"],
    "적격합병": ["적격합병", "합병대가 주식", "지분연속성", "사업목적 합병", "합병과세특례"],
    "완전자회사": ["완전자회사 합병", "모자회사 합병", "피합병법인 주식 100%"],
    "간이합병": ["간이합병", "소규모합병", "합병신주"],
    "물적분할": ["물적분할", "분할신설법인", "적격분할"],
    "인적분할": ["인적분할", "분할신설법인", "주식배정"],
    # 2. 법인세·일반 세무 쟁점 동의어
    "장애인고용부담금": ["장애인고용부담금", "장애인고용 부담금", "고용부담금"],
    "환급금": ["국세환급금", "환급가산금", "환급금"],
    "경정청구": ["경정청구", "법인세환급", "환급"],
    "손금산입": ["손금산입", "손금", "필요경비"],
    "손금불산입": ["손금불산입", "손금", "비용"],
    "익금불산입": ["익금불산입", "익금"],
    "판매장려금": ["판매장려금", "장려금", "매출에누리"],
    "부당행위계산부인": ["부당행위계산부인", "부당행위계산", "시가", "정상가격"],
    "부당행위": ["부당행위계산부인", "부당행위계산", "시가"],
    "세금계산서": ["세금계산서", "매입세액", "공급시기"],
    "가지급금": ["가지급금 인정이자", "업무무관가지급금", "가지급금"],
    "대손금": ["대손상각비", "대손금", "소멸시효"],
}

# 광의의 기본어 (단독 검색 시 무관한 판례가 대량 유입되므로 수식어가 있을 때 단독 쿼리 방지)
BROAD_BASE_WORDS = {"합병", "분할", "양도", "증여", "상속", "출자", "감자", "증자", "배당", "처분", "대여"}

# 5대 입체 검색 경로 표준 명칭 및 우선순위 매핑
ROUTE_PATH_MAP = {
    "direct": "직접 검색 결과",
    "synonym": "유사어 검색 결과",
    "risk": "리스크 검색 결과",
    "opposite": "리스크 검색 결과",
    "evidence": "증빙 검색 결과",
    "fallback": "자동 복원 검색 결과",
    "rescue": "자동 복원 검색 결과",
    "rescue_fallback": "자동 복원 검색 결과",
}

ROUTE_PRIORITY = {
    "direct": 5,
    "synonym": 4,
    "risk": 3,
    "opposite": 3,
    "evidence": 2,
    "fallback": 1,
    "rescue": 0,
    "rescue_fallback": 0,
}


def _clean_token(token: str) -> str:
    """검색 품질을 떨어뜨리는 조사와 일반 표현을 제거한 키워드."""
    if not token:
        return ""
    token = str(token).strip()
    token = re.sub(r'(은|는|이|가|을|를|에|의|과|와|으로|로|에서|에게|한테|도|만|까지|부터|으로서|으로써)$', '', token)
    return token.strip()


def _append_unique(seq: List[str], value: str, max_len: Optional[int] = None) -> None:
    value = _clean_token(value)
    if not value or len(value) < 2:
        return
    if value not in seq:
        seq.append(value)
    if max_len and len(seq) > max_len:
        del seq[max_len:]

def detect_tax_category(title: str, case_no: str = "", full_text: str = "") -> str:
    """
    사건명, 사건번호, 요지 텍스트를 기반으로 세목(법인세/부가가치세/소득세 등)을 자동 분류
    """
    combined = f"{title} {case_no} {full_text}".lower()
    
    # 1. 부가가치세
    if any(k in combined for k in [
        "부가가치세", "부가세", "매입세액", "매출세액", "세금계산서", 
        "영세율", "의제매입", "신용카드매출전표", "간이과세", "대손세액",
        "에누리", "공급가액", "매출에누리"
    ]):
        return "부가가치세"
    
    # 2. 법인세
    if any(k in combined for k in [
        "법인세", "법인세등", "가지급금", "인정이자", "손금", "익금", 
        "부당행위", "부당행위계산", "대손금", "대손", "감가상각", "접대비", 
        "업무용승용차", "유보", "사외유출", "기타사외유출", "연구개발비", 
        "이월결손금", "특수관계인", "합병평가차익", "고유목적사업준비금", "외국법인",
        "매출누락", "추계", "추계산정", "추계결정", "추계과세", "판매장려금"
    ]):
        return "법인세"
    
    # 3. 소득세·원천세
    if any(k in combined for k in [
        "소득세", "원천징수", "원천세", "종합소득세", "양도소득세", "근로소득", 
        "퇴직소득", "배당소득", "이자소득", "인정상여", "기타소득", "사업소득", 
        "연말정산", "지급명세서", "사례금", "배당"
    ]):
        return "소득세·원천세"
    
    # 4. 상속·증여세
    if any(k in combined for k in ["상속세", "증여세", "증여의제", "명의신탁"]):
        return "상속·증여세"

    # 5. 지방세
    if any(k in combined for k in ["지방세", "취득세", "재산세", "등록면허세", "주민세"]):
        return "지방세"

    return "조세일반"


def fetch_prec_from_drf(query: str, oc: str, display: int = 30, error_list: Optional[list] = None) -> List[Dict[str, Any]]:
    """DRF 판례(prec) API 단일 검색 실행 및 파싱 헬퍼 (오류 유형별 수집 및 기록 지원)"""
    if not oc or not oc.strip():
        _record_error(error_list, ERR_AUTH_ERROR, "국가법령정보센터 Open API 사용자 인증키(OC)가 설정되지 않았습니다.", query, "prec")
        return []

    params = {
        "OC": oc.strip(),
        "target": "prec",
        "type": "XML",
        "query": query,
        "display": min(display, 100)
    }
    items = []
    try:
        resp = _SESSION.get(DRF_SEARCH_URL, params=params, headers=_DEFAULT_HEADERS, timeout=(4.0, 15.0))
    except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout):
        _record_error(error_list, ERR_NETWORK_ERROR, f"국가법령정보센터 서버 응답 시간 초과 (Timeout, 검색어: '{query}')", query, "prec")
        return []
    except requests.exceptions.ConnectionError:
        _record_error(error_list, ERR_NETWORK_ERROR, "국가법령정보센터 서버에 연결할 수 없습니다 (Connection Error)", query, "prec")
        return []
    except requests.exceptions.RequestException as e:
        _record_error(error_list, ERR_NETWORK_ERROR, f"네트워크 통신 오류: {str(e)[:80]}", query, "prec")
        return []

    if resp.status_code in (401, 403):
        _record_error(error_list, ERR_AUTH_ERROR, f"국가법령정보센터 API 접근 권한 거부 (HTTP {resp.status_code})", query, "prec")
        return []
    elif resp.status_code != 200:
        _record_error(error_list, ERR_NETWORK_ERROR, f"국가법령정보센터 서버 오류 (HTTP {resp.status_code})", query, "prec")
        return []

    raw_text = resp.text.strip() if resp.text else ""
    if raw_text.startswith("<!DOCTYPE html") or "<html" in raw_text[:120].lower():
        if any(k in raw_text for k in ["미신청", "인증", "OC", "key", "권한", "신청"]):
            _record_error(error_list, ERR_AUTH_ERROR, "판례(prec) API 서비스 미신청 또는 인증키 권한 부족", query, "prec")
        else:
            _record_error(error_list, ERR_PARSE_ERROR, "XML 대신 HTML 서버 오류 페이지 수신", query, "prec")
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        _record_error(error_list, ERR_PARSE_ERROR, f"응답 XML 파싱 실패: {str(e)[:80]}", query, "prec")
        return []

    if root.tag in ("Response", "error", "fault", "Error"):
        msg = root.findtext("msg") or root.findtext("message") or root.findtext("result") or ""
        if any(k in msg for k in ["인증", "OC", "키", "IP", "권한", "미신청"]):
            _record_error(error_list, ERR_AUTH_ERROR, f"API 인증 오류: {msg}", query, "prec")
        else:
            _record_error(error_list, ERR_PARSE_ERROR, f"DRF 응답 오류: {msg or root.tag}", query, "prec")
        return []

    try:
        for p in root.findall("prec"):
            prec_id = p.findtext("판례일련번호") or ""
            title = p.findtext("사건명") or "제목 없음"
            case_no = p.findtext("사건번호") or "번호 없음"
            date_str = p.findtext("선고일자") or "일자 미상"
            court = p.findtext("법원명") or ""
            case_type = p.findtext("사건종류명") or "조세/행정"
            source = p.findtext("데이터출처명") or "국가법령정보센터"
            detail_link = p.findtext("판례상세링크") or ""
            
            display_court = court
            if not display_court:
                if "행정법원" in case_no:
                    display_court = "서울행정법원"
                elif "고법" in case_no or "고등법원" in case_no:
                    display_court = "고등법원"
                elif "대법원" in case_no or "두" in case_no or "다" in case_no:
                    display_court = "대법원"
                elif "심사" in case_no:
                    display_court = "국세청"
                elif "조심" in case_no:
                    display_court = "조세심판원"
                else:
                    display_court = source

            is_tribunal = ("조심" in case_no or "조세심판" in display_court or "조세심판" in source)
            is_nts_review = ("심사" in case_no or "국세청" in display_court or "국세청" in source) and not ("법원" in display_court or "대법원" in display_court)

            if is_tribunal:
                cat_name = "조세심판례"
                data_type = "조세심판례"
                doc_label = "청구번호"
                date_label = "의결일자"
                court_label = "재결청"
            elif is_nts_review:
                cat_name = "국세청 심사·결정례"
                data_type = "국세청 심사·결정례"
                doc_label = "결정번호"
                date_label = "결정일자"
                court_label = "결정기관"
            else:
                cat_name = "판례"
                data_type = "법원 판례"
                doc_label = "사건번호"
                date_label = "선고일자"
                court_label = "선고법원"

            if prec_id:
                web_link = f"https://www.law.go.kr/LSW/precInfoP.do?precSeq={prec_id}"
            elif detail_link.startswith("/"):
                web_link = f"https://www.law.go.kr{detail_link}"
            else:
                q_safe = urllib.parse.quote(case_no if case_no != "번호 없음" else title)
                web_link = f"https://www.law.go.kr/precSc.do?menuId=1&query={q_safe}"

            tax_cat = detect_tax_category(title, case_no)

            items.append({
                "category": cat_name,
                "data_type": data_type,
                "data_type_label": data_type,
                "title": title,
                "case_number": case_no,
                "doc_no_label": doc_label,
                "date": date_str,
                "date_label": date_label,
                "court": display_court,
                "court_label": court_label,
                "source": source,
                "prec_id": str(prec_id) if prec_id else f"prec:{case_no or title}",
                "link": web_link,
                "tax_category": tax_cat,
                "summary": title,
                "full_text": f"【자료유형】 {data_type}\n【사건명】 {title}\n【{doc_label}】 {case_no}\n【{date_label}】 {date_str}\n【{court_label}】 {display_court}\n【세목】 {tax_cat}\n【출처】 {source}\n【상세링크】 {web_link}"
            })
    except Exception as e:
        _record_error(error_list, ERR_PARSE_ERROR, f"판례 파싱 루프 내부 오류: {str(e)[:80]}", query, "prec")

    return items


def fetch_decc_from_drf(query: str, oc: str, display: int = 30, error_list: Optional[list] = None) -> List[Dict[str, Any]]:
    """
    조세심판원 특별행정심판재결례(ttSpecialDecc) API 단일 검색 실행 및 파싱 헬퍼
    - 대상: 조세심판원 국세/지방세/관세 불복 심판결정례
    """
    if not oc or not oc.strip():
        _record_error(error_list, ERR_AUTH_ERROR, "국가법령정보센터 Open API 사용자 인증키(OC)가 설정되지 않았습니다.", query, "ttSpecialDecc")
        return []

    params = {
        "OC": oc.strip(),
        "target": "ttSpecialDecc",
        "type": "XML",
        "query": query,
        "display": min(display, 100)
    }
    items = []
    try:
        resp = _SESSION.get(DRF_SEARCH_URL, params=params, headers=_DEFAULT_HEADERS, timeout=(4.0, 15.0))
    except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout):
        _record_error(error_list, ERR_NETWORK_ERROR, f"조세심판례 API 서버 응답 시간 초과 (Timeout, 검색어: '{query}')", query, "ttSpecialDecc")
        return []
    except requests.exceptions.ConnectionError:
        _record_error(error_list, ERR_NETWORK_ERROR, "조세심판례 API 서버에 연결할 수 없습니다 (Connection Error)", query, "ttSpecialDecc")
        return []
    except requests.exceptions.RequestException as e:
        _record_error(error_list, ERR_NETWORK_ERROR, f"조세심판례 네트워크 통신 오류: {str(e)[:80]}", query, "ttSpecialDecc")
        return []

    if resp.status_code in (401, 403):
        _record_error(error_list, ERR_AUTH_ERROR, f"조세심판례 API 접근 권한 거부 (HTTP {resp.status_code})", query, "ttSpecialDecc")
        return []
    elif resp.status_code != 200:
        _record_error(error_list, ERR_NETWORK_ERROR, f"조세심판례 서버 오류 (HTTP {resp.status_code})", query, "ttSpecialDecc")
        return []

    raw_text = resp.text.strip() if resp.text else ""
    if raw_text.startswith("<!DOCTYPE html") or "<html" in raw_text[:120].lower():
        if any(k in raw_text for k in ["미신청", "인증", "OC", "key", "권한", "신청"]):
            _record_error(error_list, ERR_AUTH_ERROR, "조세심판례(ttSpecialDecc) API 서비스 미신청 또는 인증키 권한 부족", query, "ttSpecialDecc")
        else:
            _record_error(error_list, ERR_PARSE_ERROR, "XML 대신 HTML 서버 오류 페이지 수신", query, "ttSpecialDecc")
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        _record_error(error_list, ERR_PARSE_ERROR, f"조세심판례 응답 XML 파싱 실패: {str(e)[:80]}", query, "ttSpecialDecc")
        return []

    if root.tag in ("Response", "error", "fault", "Error"):
        msg = root.findtext("msg") or root.findtext("message") or root.findtext("result") or ""
        if any(k in msg for k in ["인증", "OC", "키", "IP", "권한", "미신청"]):
            _record_error(error_list, ERR_AUTH_ERROR, f"API 인증 오류: {msg}", query, "ttSpecialDecc")
        else:
            _record_error(error_list, ERR_PARSE_ERROR, f"DRF 응답 오류: {msg or root.tag}", query, "ttSpecialDecc")
        return []

    try:
        for p in root.findall("decc"):
            decc_id = p.findtext("특별행정심판재결례일련번호") or ""
            title = p.findtext("사건명") or "사건명 없음"
            case_no = p.findtext("청구번호") or p.findtext("사건번호") or "청구번호 미기재"
            date_str = p.findtext("의결일자") or p.findtext("처분일자") or "일자 미상"
            court = p.findtext("재결청") or "조세심판원"
            detail_link = p.findtext("행정심판재결례상세링크") or ""

            if detail_link.startswith("http"):
                web_link = detail_link
            elif detail_link.startswith("/"):
                web_link = f"https://www.law.go.kr{detail_link}"
            else:
                q_safe = urllib.parse.quote(case_no if case_no != "청구번호 미기재" else title)
                web_link = f"https://www.law.go.kr/ttSpecialDeccSc.do?menuId=1&query={q_safe}"

            tax_cat = detect_tax_category(title, case_no)
            unique_id = f"decc:{decc_id or case_no or f'{title}_{date_str}'}"

            items.append({
                "category": "조세심판례",
                "data_type": "조세심판례",
                "data_type_label": "조세심판례",
                "title": title,
                "case_number": case_no,
                "doc_no_label": "청구번호",
                "date": date_str,
                "date_label": "의결일자",
                "court": court,
                "court_label": "재결청",
                "source": "조세심판원",
                "prec_id": unique_id,
                "link": web_link,
                "tax_category": tax_cat,
                "summary": title,
                "full_text": f"【자료유형】 조세심판례\n【사건명】 {title}\n【청구번호】 {case_no}\n【의결일자】 {date_str}\n【재결청】 {court}\n【세목】 {tax_cat}\n【상세링크】 {web_link}"
            })
    except Exception as e:
        _record_error(error_list, ERR_PARSE_ERROR, f"조세심판례 파싱 루프 내부 오류: {str(e)[:80]}", query, "ttSpecialDecc")

    return items


def fetch_expc_from_drf(query: str, oc: str, display: int = 30, error_list: Optional[list] = None) -> List[Dict[str, Any]]:
    """
    국세청 세법해석례(ntsCgmExpc) 및 법제처 법령해석례(expc) API 통합 검색 실행 및 파싱 헬퍼
    - 1순위: 국세청 세법해석례 (질의회신, 사전답변, 기준자문) -> 실무 세무 질의의 핵심 근거
    - 2순위: 법제처 법령해석례 (정부 유권해석)
    """
    if not oc or not oc.strip():
        _record_error(error_list, ERR_AUTH_ERROR, "국가법령정보센터 Open API 사용자 인증키(OC)가 설정되지 않았습니다.", query, "ntsCgmExpc")
        return []

    items = []
    seen_ids = set()

    # 1. 국세청 법령해석 (ntsCgmExpc) 호출
    params_nts = {
        "OC": oc.strip(),
        "target": "ntsCgmExpc",
        "type": "XML",
        "query": query,
        "display": min(display, 100)
    }
    try:
        resp_nts = _SESSION.get(DRF_SEARCH_URL, params=params_nts, headers=_DEFAULT_HEADERS, timeout=(4.0, 15.0))
        if resp_nts.status_code == 200 and resp_nts.content:
            raw_text = resp_nts.text.strip()
            if not (raw_text.startswith("<!DOCTYPE html") or "<html" in raw_text[:120].lower()):
                root = ET.fromstring(resp_nts.content)
                candidates = list(root.findall("cgmExpc")) or list(root.findall("row")) or list(root.findall("item"))
                for p in candidates:
                    expc_id = p.findtext("법령해석일련번호") or ""
                    title = p.findtext("안건명") or p.findtext("제목") or "제목 없음"
                    case_no = p.findtext("안건번호") or p.findtext("문서번호") or "문서번호 미기재"
                    date_str = p.findtext("해석일자") or p.findtext("회신일자") or "일자 미상"
                    org = p.findtext("해석기관명") or p.findtext("질의기관명") or "국세청"
                    detail_link = p.findtext("법령해석상세링크") or ""

                    if detail_link.startswith("http"):
                        web_link = detail_link
                    elif detail_link.startswith("/"):
                        web_link = f"https://taxlaw.nts.go.kr{detail_link}"
                    else:
                        q_safe = urllib.parse.quote(case_no if case_no != "문서번호 미기재" else title)
                        web_link = f"https://taxlaw.nts.go.kr/qt/USEQTA001L.do?query={q_safe}"

                    tax_cat = detect_tax_category(title, case_no)
                    unique_id = f"expc:{expc_id or case_no or f'{title}_{date_str}'}"
                    if unique_id not in seen_ids:
                        seen_ids.add(unique_id)
                        items.append({
                            "category": "예규/해석례",
                            "data_type": "예규·법령해석",
                            "data_type_label": "예규·법령해석",
                            "title": title,
                            "case_number": case_no,
                            "doc_no_label": "문서번호",
                            "date": date_str,
                            "date_label": "회신일자",
                            "court": org,
                            "court_label": "해석기관",
                            "source": f"{org}(세법해석)",
                            "prec_id": unique_id,
                            "link": web_link,
                            "tax_category": tax_cat,
                            "summary": title,
                            "full_text": f"【자료유형】 예규·법령해석\n【안건명】 {title}\n【문서번호】 {case_no}\n【회신일자】 {date_str}\n【해석기관】 {org}\n【세목】 {tax_cat}\n【상세링크】 {web_link}"
                        })
    except Exception as e:
        logging.getLogger(__name__).warning(f"[국세청 법령해석 API 일시 오류] {e} (query: '{query}')")

    # 2. 법제처 법령해석례 (expc) 보조 호출
    params_expc = {
        "OC": oc.strip(),
        "target": "expc",
        "type": "XML",
        "query": query,
        "display": min(display, 100)
    }
    try:
        resp_expc = _SESSION.get(DRF_SEARCH_URL, params=params_expc, headers=_DEFAULT_HEADERS, timeout=(3.5, 10.0))
        if resp_expc.status_code == 200 and resp_expc.content:
            raw_text = resp_expc.text.strip()
            if not (raw_text.startswith("<!DOCTYPE html") or "<html" in raw_text[:120].lower()):
                root = ET.fromstring(resp_expc.content)
                candidates = list(root.findall("expc")) or list(root.findall("row")) or list(root.findall("item"))
                for p in candidates:
                    expc_id = p.findtext("해석례일련번호") or ""
                    title = p.findtext("안건명") or p.findtext("제목") or "제목 없음"
                    case_no = p.findtext("문서번호") or "문서번호 미기재"
                    date_str = p.findtext("회신일자") or "일자 미상"
                    org = p.findtext("기관명") or p.findtext("소관부처명") or "법제처"
                    detail_link = p.findtext("해석례상세링크") or p.findtext("상세링크") or ""

                    if detail_link.startswith("http"):
                        web_link = detail_link
                    elif detail_link.startswith("/"):
                        web_link = f"https://www.law.go.kr{detail_link}"
                    else:
                        q_safe = urllib.parse.quote(case_no if case_no != "문서번호 미기재" else title)
                        web_link = f"https://www.law.go.kr/expcSc.do?menuId=1&query={q_safe}"

                    tax_cat = detect_tax_category(title, case_no)
                    unique_id = f"expc:{expc_id or case_no or f'{title}_{date_str}'}"
                    if unique_id not in seen_ids:
                        seen_ids.add(unique_id)
                        items.append({
                            "category": "예규/해석례",
                            "data_type": "예규·법령해석",
                            "data_type_label": "예규·법령해석",
                            "title": title,
                            "case_number": case_no,
                            "doc_no_label": "문서번호",
                            "date": date_str,
                            "date_label": "회신일자",
                            "court": org,
                            "court_label": "해석기관",
                            "source": f"{org}(법령해석)",
                            "prec_id": unique_id,
                            "link": web_link,
                            "tax_category": tax_cat,
                            "summary": title,
                            "full_text": f"【자료유형】 예규·법령해석\n【안건명】 {title}\n【문서번호】 {case_no}\n【회신일자】 {date_str}\n【해석기관】 {org}\n【세목】 {tax_cat}\n【상세링크】 {web_link}"
                        })
    except Exception:
        pass

    return items


def search_real_law_data(
    query: str,
    category: str = "전체",
    tax_type: str = "전체",
    oc_key: Optional[str] = None,
    limit: int = 15,
    **kwargs
) -> Dict[str, Any]:
    """
    국가법령정보센터 DRF API를 실시간 호출하여 실제 판례/결정례를 가져오고 세목별로 정밀 필터링합니다.
    """
    oc = (config.get_law_oc() if oc_key is None else oc_key).strip()
    if not oc:
        return {
            "total": 0,
            "items": [],
            "error_type": ERR_AUTH_ERROR,
            "error_category": ERROR_CATEGORY_NAMES[ERR_AUTH_ERROR],
            "error": "[국가법령정보센터 API 설정 오류] 법제처 Open API 사용자 인증키(OC)가 설정되지 않았습니다. .env 파일에 LAW_API_KEY를 입력해 주세요."
        }
    clean_query = query.strip()
    if not clean_query:
        return {"total": 0, "items": [], "error": None, "error_type": None, "error_category": None}

    api_errors = []
    try:
        items_dict = {}
        # 1. 판례, 조세심판례, 예규·법령해석 3대 채널 동시 호출
        first_prec = fetch_prec_from_drf(clean_query, oc, display=30, error_list=api_errors)
        first_decc = fetch_decc_from_drf(clean_query, oc, display=20, error_list=api_errors)
        first_expc = fetch_expc_from_drf(clean_query, oc, display=20, error_list=api_errors)

        for it in first_prec + first_decc + first_expc:
            key = it.get("prec_id") or f"{it.get('category')}:{it.get('case_number')}:{it.get('title')}"
            it["matched_routes"] = ["direct"]
            it["matched_queries"] = [clean_query]
            it["search_path"] = "직접 검색 결과"
            it["search_path_code"] = "direct"
            items_dict[key] = it

        if tax_type != "전체":
            tax_keyword_map = {"법인세": "법인세", "부가가치세": "부가가치세", "소득세·원천세": "소득세"}
            mapped_kw = tax_keyword_map.get(tax_type, tax_type)
            if mapped_kw not in clean_query:
                sec_query = f"{mapped_kw} {clean_query}"
                sec_prec = fetch_prec_from_drf(sec_query, oc, display=15, error_list=api_errors)
                sec_decc = fetch_decc_from_drf(sec_query, oc, display=10, error_list=api_errors)
                sec_expc = fetch_expc_from_drf(sec_query, oc, display=10, error_list=api_errors)
                for it in sec_prec + sec_decc + sec_expc:
                    key = it.get("prec_id") or f"{it.get('category')}:{it.get('case_number')}:{it.get('title')}"
                    if key not in items_dict:
                        it["matched_routes"] = ["direct"]
                        it["matched_queries"] = [sec_query]
                        it["search_path"] = "직접 검색 결과"
                        it["search_path_code"] = "direct"
                        items_dict[key] = it

        all_items = list(items_dict.values())
        filtered_by_cat = []
        for it in all_items:
            court = it.get("court", "")
            it_cat = it.get("category", "")
            if category in ("전체", "🏛️ 전체 자료", "🏛️ 전체 기관"):
                filtered_by_cat.append(it)
            elif "판례" in category and not ("조세심판" in category or "결정례" in category):
                if it_cat == "판례" or ("법원" in court or "대법원" in court):
                    filtered_by_cat.append(it)
            elif "조세심판" in category or "결정례" in category or "행정청" in category:
                if it_cat in ("조세심판례", "국세청 심사·결정례") or ("국세청" in court or "조세심판원" in court or "행정안전부" in court):
                    filtered_by_cat.append(it)
            elif "예규" in category or "해석" in category:
                if it_cat == "예규/해석례" or "해석" in court:
                    filtered_by_cat.append(it)
            else:
                filtered_by_cat.append(it)

        if tax_type == "전체":
            final_items = filtered_by_cat
        else:
            matched_tax = [it for it in filtered_by_cat if it.get("tax_category") == tax_type]
            final_items = matched_tax if matched_tax else filtered_by_cat

        total_cnt = len(final_items) if tax_type != "전체" else max(len(final_items), len(all_items))
        
        err_type = None
        err_cat = None
        err_msg = None
        if total_cnt == 0:
            err_type, err_cat, err_msg = _determine_final_error(api_errors)

        enriched_items = enrich_cases_with_details(final_items[:limit], oc, max_items=limit)

        return {
            "total": total_cnt,
            "items": enriched_items,
            "api_errors": api_errors,
            "error_type": err_type,
            "error_category": err_cat,
            "error": err_msg
        }
    except Exception as e:
        return {
            "total": 0,
            "items": [],
            "error_type": ERR_NETWORK_ERROR,
            "error_category": ERROR_CATEGORY_NAMES[ERR_NETWORK_ERROR],
            "error": f"[국가법령정보센터 DRF API 통신 오류] {str(e)}"
        }


def decompose_tax_compound(token: str) -> List[str]:
    """
    복합 명사(예: 무증자합병, 적격합병, 부당행위계산, 대손상각비, 접대비한도)를
    국가법령정보센터 DRF 색인 단위(1~2단어)로 분해합니다.
    """
    if not token or len(token) < 2:
        return []
    clean = re.sub(r'[\d%]+', '', token).strip()
    results = [clean] if len(clean) >= 2 else []
    known_roots = [
        "무증자", "합병", "분할", "양도", "증여", "상속", "출자", "감자", "증자", 
        "배당", "처분", "대여", "가지급", "가지급금", "접대비", "대손", "대손상각", 
        "부당행위", "부당행위계산", "특수관계", "특수관계인", "자회사", "모회사", 
        "연구개발", "외국납부", "이월결손", "결손금", "명의신탁", "간주임대", 
        "원천징수", "적격증빙", "손금산입", "익금산입", "세무조정"
    ]
    for root in known_roots:
        if root in clean and root != clean:
            if root not in results:
                results.append(root)
            rem = clean.replace(root, "").strip()
            if len(rem) >= 2:
                spaced = f"{root} {rem}"
                if spaced not in results:
                    results.append(spaced)
                if rem not in results:
                    results.append(rem)
    return results


def clean_drf_query(query: str) -> str:
    """
    DRF API 검색에 최적화된 1~2어절 정제 쿼리를 반환합니다.
    특수기호, 불용 쟁점어(과세여부, 검토 등)를 제거합니다.
    """
    if not query:
        return ""
    q = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', query)
    tokens = [t.strip() for t in q.split() if t.strip() and len(t.strip()) >= 2]
    stop_query_words = {"여부", "검토", "과세여부", "인정여부", "세무조정", "관련", "경우", "사항"}
    filtered = [t for t in tokens if t not in stop_query_words]
    final_tokens = filtered if filtered else tokens
    return " ".join(final_tokens[:2])


def search_real_law_data_multi(
    keywords: List[str],
    category: str = "전체",
    tax_type: str = "전체",
    oc_key: Optional[str] = None,
    limit: int = 15,
    raw_query: Optional[str] = None,
    intent_data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    [입체적 5대 경로 검색 & 6대 근거 분류 엔진]
    국가법령정보센터 DRF API의 특성(1~2어절 색인)에 맞추어
    1) 복합어 원자 분해
    2) 입체 쿼리 인터리빙 (직접근거+원자키워드+리스크+증빙+반대선례 골고루 호출)
    3) 0건 방지 자동 복원(Rescue Pass)
    4) 6대 근거버킷(direct, similar, risk, evidence, statute, weak) 정밀 분류
    """
    oc = (config.get_law_oc() if oc_key is None else oc_key).strip()
    if not oc:
        return {
            "total": 0,
            "items": [],
            "all_items": [],
            "debug": {},
            "api_errors": [{"error_type": ERR_AUTH_ERROR, "category": ERROR_CATEGORY_NAMES[ERR_AUTH_ERROR], "message": "국가법령정보센터 Open API 사용자 인증키(OC)가 설정되지 않았습니다."}],
            "error_type": ERR_AUTH_ERROR,
            "error_category": ERROR_CATEGORY_NAMES[ERR_AUTH_ERROR],
            "error": "[API 인증 오류] 국가법령정보센터 Open API 사용자 인증키(OC)가 설정되지 않았습니다. .env 파일에 LAW_API_KEY를 설정해 주세요."
        }

    api_errors = []

    generic_biz_words = {
        "거래처", "회사", "법인", "사업자", "대표자", "대표이사", "고객", "직원", "임직원", 
        "납세자", "당사", "귀사", "상대방", "타인", "개인", "본인", "제3자", "모회사", "자회사"
    }
    generic_tax_words = {
        "손금인정", "손금산입", "손금불산입", "익금산입", "과세여부", "세무처리", 
        "비용처리", "공제여부", "인정여부", "과세표준", "신고여부", "적법여부", "처분여부"
    }
    stopwords = {
        "목적", "사유", "주체", "행위", "객체", "조건", "금액", "결과", "쟁점", "현상",
        "경우", "사항", "내용", "관련", "대상", "여부", "적용", "인정", "판단", "기준",
        "해당", "문제", "발생", "검토", "상황", "원인", "이유", "방법", "형태", "요청",
        "가능한가", "어떻게", "있는가", "대하여", "경우에", "위하여", "인정이", "처리되나",
        "관련하여", "대하여", "따른", "의한", "위한", "가지", "대한", "통해"
    }
    josa_pattern = r'(은|는|이|가|을|를|에|의|과|와|으로|로|에서|에게|한테|도|만|까지|부터|으로서|으로써)$'

    primary_topics = []
    tax_issues = []
    biz_contexts = []
    excluded_tokens = []

    if raw_query:
        tokens = re.findall(r'[가-힣]{2,}', raw_query)
        for tok in tokens:
            cl = re.sub(josa_pattern, '', tok)
            cl = re.sub(josa_pattern, '', cl)
            if len(cl) < 2 or cl in stopwords:
                if cl and cl not in excluded_tokens:
                    excluded_tokens.append(cl)
                continue
            
            if cl in generic_biz_words:
                if cl not in biz_contexts: biz_contexts.append(cl)
            elif cl in STRONG_TAX_TERMS or any(k in cl for k in ["손금", "익금", "접대비", "가지급금", "부가가치", "대납", "정산", "선납", "경정", "환급", "가산금"]):
                if cl not in tax_issues: tax_issues.append(cl)
            elif cl in generic_tax_words:
                if cl not in tax_issues: tax_issues.append(cl)
            else:
                # 복합어 분해(예: 무증자합병 -> 무증자합병, 무증자, 합병)
                sub_roots = decompose_tax_compound(cl)
                for sr in (sub_roots or [cl]):
                    if sr not in primary_topics and sr not in stopwords:
                        primary_topics.append(sr)

    expanded_kws = []
    for kw in (keywords or []):
        for part in kw.strip().split():
            cl = re.sub(josa_pattern, '', part)
            cl = re.sub(josa_pattern, '', cl)
            if len(cl) >= 2 and cl not in stopwords and cl not in generic_tax_words:
                sub_roots = decompose_tax_compound(cl)
                for sr in (sub_roots or [cl]):
                    if sr not in expanded_kws and sr not in primary_topics:
                        expanded_kws.append(sr)

    intent_must = (intent_data or {}).get("must_keywords", [])
    for m in intent_must:
        m_clean = re.sub(r'[\d%]+', '', m).strip()
        for sr in (decompose_tax_compound(m_clean) or [m_clean]):
            if sr and sr not in primary_topics and sr not in stopwords:
                primary_topics.insert(0, sr)

    intent_issues = (intent_data or {}).get("issue_keywords", [])
    for issue in intent_issues:
        issue = _clean_token(issue)
        if issue and issue not in tax_issues:
            tax_issues.insert(0, issue)

    candidates = []
    for pt in primary_topics:
        if pt and pt not in candidates and pt not in generic_biz_words:
            candidates.append(pt)
    for ti in tax_issues:
        if ti and ti not in candidates:
            candidates.append(ti)
    for ek in expanded_kws:
        if ek and ek not in candidates and ek not in generic_biz_words:
            candidates.append(ek)
    for bc in biz_contexts:
        if bc and bc not in candidates:
            candidates.append(bc)

    # 3. 5대 입체 검색전략(search_strategy) 기반 쿼리 플랜 수립
    strat = (intent_data or {}).get("search_strategy", {}) or {}
    strat_direct = [clean_drf_query(q) for q in strat.get("direct_queries", []) if clean_drf_query(q)]
    strat_risk = [clean_drf_query(q) for q in strat.get("risk_queries", []) if clean_drf_query(q)]
    strat_evidence = [clean_drf_query(q) for q in strat.get("evidence_queries", []) if clean_drf_query(q)]
    strat_opposite = [clean_drf_query(q) for q in strat.get("opposite_queries", []) if clean_drf_query(q)]
    strat_fallback = [clean_drf_query(q) for q in strat.get("fallback_queries", []) if clean_drf_query(q)]
    exclude_terms = [e.strip() for e in (strat.get("exclude_terms", []) or (intent_data or {}).get("exclude_keywords", [])) if e.strip()]

    target_tax_kw = ""
    target_tax = tax_type if tax_type != "전체" else (intent_data or {}).get("tax_category", "")
    if target_tax and target_tax not in ["전체", "조세일반"]:
        target_tax_kw = "소득세" if target_tax == "소득세·원천세" else target_tax

    # 각 루트별 계획된 쿼리 (가중치 및 라우트 부여)
    route_plans = []

    # 전문 도메인 동의어(QUERY_SYNONYMS) 매핑 - 유사어 검색 쿼리로 등록
    domain_synonyms = []
    if raw_query:
        for k, syn_list in QUERY_SYNONYMS.items():
            if k in raw_query or any(k in pt for pt in primary_topics):
                for syn in syn_list:
                    if syn not in domain_synonyms:
                        domain_synonyms.append(syn)
                        route_plans.append({"query": syn, "route": "synonym", "weight": 0.92})

    # Route 1: 직접근거 (Direct)
    for q in strat_direct:
        route_plans.append({"query": q, "route": "direct", "weight": 1.0})
    if not strat_direct or len(strat_direct) < 2:
        for pt in primary_topics[:3]:
            # 광의의 기본어는 수식어가 있을 때 단독 조합 생성 지양
            if pt in BROAD_BASE_WORDS and any(m in (raw_query or "") for m in ["무증자", "포합", "적격", "완전", "간이", "소규모", "삼각", "역", "우회", "물적", "인적"]):
                continue
            for issue in tax_issues[:2]:
                q_comb = clean_drf_query(f"{pt} {issue}")
                if q_comb:
                    route_plans.append({"query": q_comb, "route": "direct", "weight": 1.0})
            if target_tax_kw:
                q_tax = clean_drf_query(f"{pt} {target_tax_kw}")
                if q_tax:
                    route_plans.append({"query": q_tax, "route": "direct", "weight": 0.95})

    # Route 2: 과세관청 리스크 (Risk)
    for q in strat_risk:
        route_plans.append({"query": q, "route": "risk", "weight": 0.90})
    if not strat_risk:
        for pt in primary_topics[:2]:
            route_plans.append({"query": clean_drf_query(f"{pt} 부당행위"), "route": "risk", "weight": 0.88})
        for ti in tax_issues[:2]:
            route_plans.append({"query": clean_drf_query(f"{ti} 부당행위"), "route": "risk", "weight": 0.88})

    # Route 3: 증빙·입증 (Evidence)
    for q in strat_evidence:
        route_plans.append({"query": q, "route": "evidence", "weight": 0.85})
    if not strat_evidence:
        for pt in primary_topics[:2]:
            route_plans.append({"query": clean_drf_query(f"{pt} 증빙"), "route": "evidence", "weight": 0.82})
        route_plans.append({"query": "적격증빙 입증", "route": "evidence", "weight": 0.80})

    # Route 4: 반대/패소 선례 (Opposite)
    for q in strat_opposite:
        route_plans.append({"query": q, "route": "opposite", "weight": 0.88})
    if not strat_opposite:
        for ti in tax_issues[:2]:
            route_plans.append({"query": clean_drf_query(f"{ti} 기각"), "route": "opposite", "weight": 0.85})

    # Route 5: 대체/기본 (Fallback) - 단일 원자 키워드 및 동의어로 모수 절대 확보
    for q in strat_fallback:
        # 분해 가능한 복합어는 단일 원자로 쪼개어 추가
        for sub in decompose_tax_compound(q):
            route_plans.append({"query": sub, "route": "fallback", "weight": 0.60})
        route_plans.append({"query": q, "route": "fallback", "weight": 0.58})
        
    for pt in primary_topics[:3]:
        if pt in BROAD_BASE_WORDS and any(m in (raw_query or "") for m in ["무증자", "포합", "적격", "완전", "간이", "소규모", "삼각", "역", "우회", "물적", "인적"]):
            continue
        route_plans.append({"query": pt, "route": "fallback", "weight": 0.60})
    for ti in tax_issues[:2]:
        route_plans.append({"query": ti, "route": "fallback", "weight": 0.60})
    for ek in expanded_kws[:2]:
        route_plans.append({"query": ek, "route": "fallback", "weight": 0.55})

    # 동의어 보강
    for cand in candidates[:4]:
        for syn in QUERY_SYNONYMS.get(cand, []):
            route_plans.append({"query": syn, "route": "synonym", "weight": 0.90})

    if not route_plans and raw_query:
        fallback_tokens = [t for t in re.findall(r'[가-힣]{2,}', raw_query) if t not in stopwords]
        for ft in (fallback_tokens[:3] or [raw_query.strip().split()[0][:10]]):
            route_plans.append({"query": ft, "route": "fallback", "weight": 0.50})

    # 중복 쿼리 제거 및 최고 가중치 유지
    search_queries_meta = {}
    for plan in route_plans:
        q_str = plan["query"].strip()
        if not q_str:
            continue
        if q_str not in search_queries_meta:
            search_queries_meta[q_str] = plan
        else:
            if plan["weight"] > search_queries_meta[q_str]["weight"]:
                search_queries_meta[q_str] = plan

    all_unique_plans = list(search_queries_meta.values())

    # 4. [인터리빙 쿼리 스케줄러] 5대 경로별로 고르게 배분
    direct_pool = [p for p in all_unique_plans if p["route"] == "direct"]
    synonym_pool = [p for p in all_unique_plans if p["route"] == "synonym"]
    risk_pool = [p for p in all_unique_plans if p["route"] == "risk"]
    evidence_pool = [p for p in all_unique_plans if p["route"] == "evidence"]
    opposite_pool = [p for p in all_unique_plans if p["route"] == "opposite"]
    fallback_pool = [p for p in all_unique_plans if p["route"] == "fallback"]

    selected_plans = []
    def add_from_pool(pool, count=1):
        added = 0
        while pool and added < count:
            cand = pool.pop(0)
            if cand["query"] not in [sp["query"] for sp in selected_plans]:
                selected_plans.append(cand)
                added += 1

    # 빠른 1차 검색: 직접근거 2개 + 유사근거 1개 + 리스크 1개
    add_from_pool(direct_pool, 2)     # 직접 검색 2개
    add_from_pool(synonym_pool, 1)    # 유사어 검색 1개
    add_from_pool(risk_pool, 1)       # 리스크 검색 1개

    # 위 경로가 부족할 때만 증빙·반대·기본 검색으로 4개를 채움
    for p in all_unique_plans:
        if len(selected_plans) >= MAX_PRIMARY_QUERIES:
            break
        if p["query"] not in [sp["query"] for sp in selected_plans]:
            selected_plans.append(p)

    search_queries = [p["query"] for p in selected_plans]

    items_dict = {}
    query_logs = []
    network_failed = threading.Event()

    # 5. DRF API 실시간 병렬 호출 (판례 + 조세심판례 + 예규/법령해석 3대 채널 동시 쿼리)
    def _execute_plan(plan):
        q = plan["query"]
        r = plan["route"]
        w = plan["weight"]
        thread_errors = []
        try:
            if network_failed.is_set():
                return (plan, [], {
                    "query": q, "route": r, "route_name": ROUTE_PATH_MAP.get(r, "직접 검색 결과"),
                    "prec_count": 0, "decc_count": 0, "expc_count": 0, "total_count": 0,
                    "status": "skipped: network error",
                }, [])

            # 핵심 판례 채널로 연결 상태를 먼저 확인하고, 네트워크 장애면 나머지 호출을 중단한다.
            prec_errs = []
            prec_fetched = fetch_prec_from_drf(q, oc, display=35, error_list=prec_errs)
            if _has_network_error(prec_errs):
                network_failed.set()
                return (plan, [], {
                    "query": q, "route": r, "route_name": ROUTE_PATH_MAP.get(r, "직접 검색 결과"),
                    "prec_count": 0, "decc_count": 0, "expc_count": 0, "total_count": 0,
                    "status": "network error",
                }, prec_errs)

            decc_errs = []
            decc_fetched = fetch_decc_from_drf(q, oc, display=40, error_list=decc_errs)
            if _has_network_error(decc_errs):
                network_failed.set()
                return (plan, prec_fetched, {
                    "query": q, "route": r, "route_name": ROUTE_PATH_MAP.get(r, "직접 검색 결과"),
                    "prec_count": len(prec_fetched), "decc_count": 0, "expc_count": 0,
                    "total_count": len(prec_fetched), "status": "partial: network error",
                }, decc_errs)

            expc_errs = []
            expc_fetched = fetch_expc_from_drf(q, oc, display=40, error_list=expc_errs)

            fetched = expc_fetched + decc_fetched + prec_fetched

            # 판례와 심판례 핵심 채널이 모두 네트워크 에러인 경우에만 치명적 에러 목록에 반영
            if not fetched:
                if decc_errs and prec_errs:
                    thread_errors.extend(decc_errs)
                    thread_errors.extend(prec_errs)
                elif prec_errs:
                    thread_errors.extend(prec_errs)
                elif decc_errs:
                    thread_errors.extend(decc_errs)

            log_item = {
                "query": q,
                "route": r,
                "route_name": ROUTE_PATH_MAP.get(r, "직접 검색 결과"),
                "prec_count": len(prec_fetched),
                "decc_count": len(decc_fetched),
                "expc_count": len(expc_fetched),
                "total_count": len(fetched),
                "status": "ok" if fetched else "empty"
            }
            return (plan, fetched, log_item, thread_errors)
        except Exception as e:
            thread_errors.append({
                "error_type": ERR_NETWORK_ERROR,
                "category": ERROR_CATEGORY_NAMES[ERR_NETWORK_ERROR],
                "message": f"API 호출 중 예외 발생: {str(e)[:80]}",
                "query": q,
                "target": "drf_multi"
            })
            log_item = {
                "query": q,
                "route": r,
                "route_name": ROUTE_PATH_MAP.get(r, "직접 검색 결과"),
                "prec_count": 0,
                "decc_count": 0,
                "expc_count": 0,
                "total_count": 0,
                "status": f"error: {str(e)[:80]}"
            }
            return (plan, [], log_item, thread_errors)

    # 국가법령정보센터(law.go.kr) 동시 접속 제한(WAF/Connection Reset) 방지를 위해 max_workers는 3으로 안전하게 제한
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(selected_plans), 3)) as executor:
        plan_results = list(executor.map(_execute_plan, selected_plans))

    for plan, fetched, log_item, t_errors in plan_results:
        api_errors.extend(t_errors)
        query_logs.append(log_item)
        q = plan["query"]
        r = plan["route"]
        w = plan["weight"]
        for it in fetched:
            key = it.get("prec_id") or f"{it.get('category')}:{it.get('case_number')}:{it.get('title')}"
            if not key:
                continue
            if key not in items_dict:
                it["matched_routes"] = [r]
                it["matched_queries"] = [q]
                it["route_weight"] = w
                items_dict[key] = it
            else:
                existing = items_dict[key]
                if r not in existing.get("matched_routes", []):
                    existing.setdefault("matched_routes", []).append(r)
                if q not in existing.get("matched_queries", []):
                    existing.setdefault("matched_queries", []).append(q)
                existing["route_weight"] = max(existing.get("route_weight", 0.0), w)

    # 6. [0건 방지 자동 복원 패스 (Dynamic Rescue Pass)]
    # 검색된 건수가 3건 미만일 경우, 핵심 원자 명사 및 세목 조합으로 즉시 비상 검색
    if len(items_dict) < 3 and not network_failed.is_set():
        rescue_tokens = []
        for pt in primary_topics:
            for sub in decompose_tax_compound(pt):
                if sub not in rescue_tokens and len(sub) >= 2 and sub not in generic_biz_words:
                    rescue_tokens.append(sub)
        for ti in tax_issues:
            if ti not in rescue_tokens and len(ti) >= 2:
                rescue_tokens.append(ti)
        
        rescue_queries = []
        if target_tax_kw and rescue_tokens:
            rescue_queries.append(clean_drf_query(f"{rescue_tokens[0]} {target_tax_kw}"))
        for tok in rescue_tokens[:3]:
            if tok not in rescue_queries:
                rescue_queries.append(tok)
                
        for rq in rescue_queries[:MAX_RESCUE_QUERIES]:
            try:
                prec_f = fetch_prec_from_drf(rq, oc, display=30, error_list=api_errors)
                decc_f = fetch_decc_from_drf(rq, oc, display=20, error_list=api_errors)
                expc_f = fetch_expc_from_drf(rq, oc, display=20, error_list=api_errors)
                fetched_r = prec_f + decc_f + expc_f
                query_logs.append({
                    "query": f"[자동복원] {rq}",
                    "route": "rescue",
                    "route_name": "자동 복원 검색 결과",
                    "prec_count": len(prec_f),
                    "decc_count": len(decc_f),
                    "expc_count": len(expc_f),
                    "total_count": len(fetched_r),
                    "status": "rescued"
                })
                for it in fetched_r:
                    key = it.get("prec_id") or f"{it.get('category')}:{it.get('case_number')}:{it.get('title')}"
                    if key and key not in items_dict:
                        it["matched_routes"] = ["rescue"]
                        it["matched_queries"] = [rq]
                        it["route_weight"] = 0.45
                        items_dict[key] = it
            except Exception as e:
                _record_error(api_errors, ERR_NETWORK_ERROR, f"자동복원 API 호출 중 예외 발생: {str(e)[:80]}", rq, "rescue")
                pass

    # 모든 아이템에 대해 대표 검색 경로(search_path) 및 우선순위 코드 확정
    for it in items_dict.values():
        routes = it.get("matched_routes", ["direct"])
        best_route = max(routes, key=lambda x: ROUTE_PRIORITY.get(x, 0))
        it["search_path"] = ROUTE_PATH_MAP.get(best_route, "직접 검색 결과")
        it["search_path_code"] = best_route

    all_items = list(items_dict.values())

    # 7. 기관 구분 필터 (판례 / 조세심판·결정례 / 예규·법령해석)
    filtered_by_cat = []
    for it in all_items:
        court = it.get("court", "")
        it_cat = it.get("category", "")
        if category in ("전체", "🏛️ 전체 자료", "🏛️ 전체 기관"):
            filtered_by_cat.append(it)
        elif "판례" in category and not ("조세심판" in category or "결정례" in category):
            if it_cat == "판례" or ("법원" in court or "대법원" in court):
                filtered_by_cat.append(it)
        elif "조세심판" in category or "결정례" in category or "행정청" in category:
            if it_cat in ("조세심판례", "국세청 심사·결정례") or ("국세청" in court or "조세심판원" in court or "행정안전부" in court):
                filtered_by_cat.append(it)
        elif "예규" in category or "해석" in category:
            if it_cat == "예규/해석례" or "해석" in court:
                filtered_by_cat.append(it)
        else:
            filtered_by_cat.append(it)

    # 8. 제외어(exclude_terms) 필터링
    items_after_exclude = []
    for it in filtered_by_cat:
        t = it.get("title", "")
        summary_txt = it.get("summary", "")
        full_corpus = f"{t} {summary_txt}"
        
        has_exclude = False
        for ex in exclude_terms:
            if ex and len(ex) >= 2 and ex in full_corpus:
                if not any(pt and pt in t for pt in primary_topics):
                    has_exclude = True
                    break
        if not has_exclude:
            items_after_exclude.append(it)

    if len(items_after_exclude) >= 3 or not filtered_by_cat:
        working_items = items_after_exclude
    else:
        working_items = filtered_by_cat

    # 8.5 상위 후보 15건 선정 및 상세 내용(판결요지·판시사항·이유·주문) 병렬 결합 (Detail Enrichment)
    def _prelim_score(it):
        sp = it.get("search_path_code", "")
        t = it.get("title", "")
        cat = it.get("category", "")
        s = 0
        if sp == "direct":
            s += 100
        elif sp in ("similar", "synonym"):
            s += 70
        elif sp in ("risk", "evidence", "opposite"):
            s += 60
        else:
            s += 10
        # 실무적으로 국세청 예규/해석례 및 조세심판원 결정례 우선 가점
        if cat == "예규/해석례":
            s += 40
        elif cat == "조세심판례":
            s += 30
        for pt in primary_topics:
            if pt and pt in t:
                s += 30
        for ti in tax_issues:
            if ti and ti in t:
                s += 20
        return s

    working_items_sorted = sorted(working_items, key=_prelim_score, reverse=True)
    working_items = enrich_cases_with_details(working_items_sorted, oc, max_items=10)

    # 9. 7-Factor 정밀 관련도 랭킹 및 6대 근거버킷(basis_bucket) 분류
    BUCKET_DISPLAY_NAMES = {
        "direct_basis": "🎯 직접근거",
        "similar_basis": "🔄 유사근거",
        "risk_basis": "🔴 과세리스크",
        "evidence_basis": "📑 증빙·입증",
        "statute_or_admin_basis": "📜 예규·해석례",
        "weak_reference": "📎 단순참고"
    }

    def evaluate_and_classify_case(item: Dict[str, Any]) -> Dict[str, Any]:
        raw_score = 15.0
        t = item.get("title", "")
        summary_txt = " ".join([
            item.get("summary", ""),
            item.get("full_text", ""),
            item.get("points", ""),
            item.get("reason", ""),
            item.get("order", ""),
            item.get("ref_articles", ""),
            item.get("case_number", ""),
            item.get("court", "")
        ])
        matched_kws = []
        reasons = []

        if item.get("has_detail"):
            raw_score += 8.0
            reasons.append("판결 전문/이유 확보")

        # 세부 쟁점 수식어(예: 무증자, 포합주식, 완전자회사 등) 탐지
        has_specific_modifier = any(m in (raw_query or "") for m in ["무증자", "포합", "적격", "완전자회사", "모자회사", "간이", "소규모", "삼각", "역합병", "우회", "물적분할", "인적분할"])

        # 사건 내용(제목+요지+전문)에서 구체적 세부 수식어 또는 관련 도메인 동의어 매칭 여부
        matched_distinctive = []
        if has_specific_modifier:
            relevant_distinctives = []
            for k, syn_list in QUERY_SYNONYMS.items():
                if k in (raw_query or ""):
                    relevant_distinctives.append(k)
                    relevant_distinctives.extend(syn_list)
            
            if "무증자" in (raw_query or "") or "무증자합병" in (raw_query or ""):
                relevant_distinctives.extend(["무증자", "합병신주", "신주", "완전자회사", "포합주식", "모자회사", "합병대가", "피합병법인 주식", "100%"])

            for dist in set(relevant_distinctives):
                if dist and (dist in t or dist in summary_txt):
                    matched_distinctive.append(dist)

        # 1) 핵심 거래 대상 목적물 매칭
        matched_primaries = []
        for pt in primary_topics:
            is_broad_base = (pt in BROAD_BASE_WORDS and has_specific_modifier and not matched_distinctive)
            if pt and pt in t:
                if is_broad_base:
                    raw_score += 15.0
                    matched_primaries.append(pt)
                else:
                    raw_score += 45.0
                    matched_primaries.append(pt)
            elif pt and pt in summary_txt:
                if is_broad_base:
                    raw_score += 10.0
                    matched_primaries.append(pt)
                else:
                    raw_score += 25.0
                    matched_primaries.append(pt)
        if matched_primaries:
            matched_kws.extend(matched_primaries)
            reasons.append(f"핵심주제({', '.join(matched_primaries[:2])}) 일치")

        # 세부 핵심 쟁점 매칭 보너스 (+40점 및 키워드 우선 노출)
        if matched_distinctive:
            raw_score += 40.0
            reasons.insert(0, f"세부쟁점({', '.join(matched_distinctive[:2])}) 직접일치")
            for md in matched_distinctive[:2]:
                if md not in matched_kws:
                    matched_kws.insert(0, md)

        # 2) 세무 쟁점 키워드 매칭
        matched_issues = []
        for ti in tax_issues:
            if ti and ti in t:
                raw_score += 25.0
                matched_issues.append(ti)
            elif ti and ti in summary_txt:
                raw_score += 15.0
                matched_issues.append(ti)
        if matched_issues:
            for mi in matched_issues:
                if mi not in matched_kws:
                    matched_kws.append(mi)
            reasons.append(f"세무쟁점({', '.join(matched_issues[:2])}) 일치")

        # 3) 검색 루트 가중치 반영
        rw = item.get("route_weight", 0.7)
        raw_score += (rw - 0.7) * 35.0

        # 4) 승소/패소/리스크 및 증빙 시그널 탐지
        has_losing_signal = any(k in summary_txt for k in ["기각", "패소", "적법", "정당하다", "불산입", "과세처분 정당", "배척"])
        has_winning_signal = any(k in summary_txt for k in ["인용", "취소", "위법", "처분을 취소한다", "인정된다", "손금산입"])
        has_evidence_signal = any(k in summary_txt for k in ["적격증빙", "계약서", "입증책임", "금융거래", "지급명세서", "원천징수", "장부", "증빙불비"])

        m_routes = item.get("matched_routes", [])

        # 5) 6대 근거버킷(basis_bucket) 결정 및 자동복원 점수 감점
        is_auto_rescue = (item.get("search_path") == "자동 복원 검색 결과")
        if is_auto_rescue:
            # 둘째, 자동 복원으로 추가된 결과는 원래 검색어와 직접 일치하는 결과보다 낮은 점수 부여
            direct_match = False
            raw_score = max(20.0, min(50.0, raw_score - 25.0))
            reasons.insert(0, "[자동 복원] 원래 검색어 완화 매칭 참고 판례 (관련도 감점)")
        elif has_specific_modifier and not matched_distinctive:
            # 특화 수식어가 질문에 있으나 사건에 해당 세부 쟁점이 없는 일반 기본어(예: 일반 합병) 사건은 direct_basis 불가
            direct_match = False
            raw_score = min(raw_score, 62.0)
            reasons.append("일반 합병 선례 (무증자/신주 등 세부쟁점 미포함)")
        else:
            direct_match = bool(matched_issues and (matched_primaries or matched_distinctive))
        if direct_match and not is_auto_rescue:
            raw_score += 25.0
            reasons.insert(0, "거래대상+세무쟁점 동시 일치")

        if is_auto_rescue:
            bucket = "weak_reference"
        elif direct_match:
            if ("risk" in m_routes or "opposite" in m_routes) and has_losing_signal:
                bucket = "risk_basis"
                reasons.append("과세리스크 선례")
            elif "evidence" in m_routes or has_evidence_signal:
                bucket = "evidence_basis"
                reasons.append("입증책임 선례")
            else:
                from components.case_logic import verify_direct_basis_eligibility
                is_ok, reject_reason = verify_direct_basis_eligibility(raw_query or " ".join(keywords), item, intent_data)
                if is_ok:
                    bucket = "direct_basis"
                    if item.get("category") == "예규/해석례":
                        raw_score += 15.0
                        reasons.insert(0, "실무 최우선 근거(국세청 예규·해석례)")
                    elif item.get("category") == "조세심판례":
                        raw_score += 10.0
                        reasons.insert(0, "조세심판원 심판결정례")
                else:
                    bucket = "similar_basis"
                    raw_score = min(raw_score, 62.0)
                    reasons.append(f"유사근거({reject_reason})")
        elif item.get("category") == "예규/해석례":
            bucket = "statute_or_admin_basis"
            raw_score += 10.0
            reasons.append("예규·유권해석")
        elif ("risk" in m_routes or "opposite" in m_routes) or (has_losing_signal and any(k in summary_txt for k in ["부당행위", "손금불산입", "과세처분"])):
            bucket = "risk_basis"
            reasons.append("과세리스크 선례")
        elif "evidence" in m_routes or has_evidence_signal:
            bucket = "evidence_basis"
            reasons.append("증빙·입증 선례")
        elif matched_primaries or matched_issues or "similar" in m_routes or "synonym" in m_routes:
            bucket = "similar_basis"
        else:
            bucket = "weak_reference"

        # 6) 세목 일치 여부 가감점
        it_tax = item.get("tax_category", "조세일반")
        target_tax = tax_type if tax_type != "전체" else (intent_data or {}).get("tax_category", "조세일반")
        if target_tax and target_tax not in ["조세일반", "전체"]:
            if it_tax == target_tax:
                raw_score += 15.0
                reasons.append(f"세목({target_tax}) 일치")
            elif it_tax != "조세일반":
                raw_score -= 20.0

        # 단일 키워드 과잉 점수 방지
        if len(set(matched_kws)) <= 1 and not direct_match:
            raw_score = min(raw_score, 58.0)

        if is_auto_rescue:
            final_score = int(round(min(50.0, max(20.0, raw_score))))
            is_high_rel = False
            compat_basis_type = "참고자료 (자동복원)"
        else:
            final_score = int(round(min(100.0, max(0.0, raw_score))))
            is_high_rel = (final_score >= 65)
            compat_basis_type = (
                "직접근거 후보" if bucket == "direct_basis" else (
                    "보조근거 후보" if bucket in ("similar_basis", "evidence_basis") else (
                        "과세리스크 후보" if bucket == "risk_basis" else (
                            "예규/해석례" if bucket == "statute_or_admin_basis" else "참고자료"
                        )
                    )
                )
            )

        reason_summary = " · ".join(reasons[:2]) if reasons else "관련 법률/기관 검색 결과"

        return {
            "score": final_score,
            "matched_keywords": matched_kws,
            "match_reason": reason_summary,
            "is_high_relevance": is_high_rel,
            "basis_bucket": bucket,
            "basis_bucket_name": BUCKET_DISPLAY_NAMES[bucket],
            "basis_type": compat_basis_type,
            "has_losing_signal": has_losing_signal,
            "has_winning_signal": has_winning_signal
        }

    for it in working_items:
        eval_res = evaluate_and_classify_case(it)
        it["relevance_score"] = eval_res["score"]
        it["matched_keywords"] = eval_res["matched_keywords"]
        it["match_reason"] = eval_res["match_reason"]
        it["is_high_relevance"] = eval_res["is_high_relevance"]
        it["basis_bucket"] = eval_res["basis_bucket"]
        it["basis_bucket_name"] = eval_res["basis_bucket_name"]
        it["basis_type"] = eval_res["basis_type"]
        it["has_losing_signal"] = eval_res["has_losing_signal"]
        it["has_winning_signal"] = eval_res["has_winning_signal"]

    # 랭킹: 직접 검색 최상단, 그 다음 유사어/리스크/증빙, 자동복원은 최하단
    # 실무적으로 국세청 예규/기재부 해석례(2) 및 조세심판원 심판결정례(1)를 법원 판결문(0)보다 우선순위 부여
    def _final_rank_key(x):
        is_direct_path = (x.get("search_path") == "직접 검색 결과")
        is_related_path = (x.get("search_path") in ("유사어 검색 결과", "리스크 검색 결과", "증빙 검색 결과"))
        is_direct_b = (x.get("basis_bucket") == "direct_basis")
        cat = x.get("category", "")
        cat_prio = 2 if cat == "예규/해석례" else (1 if cat == "조세심판례" else 0)
        score = x.get("relevance_score", 0)
        return (is_direct_path, is_related_path, is_direct_b, cat_prio, score)

    ranked_items = sorted(working_items, key=_final_rank_key, reverse=True)

    seen = set()
    deduped = []
    for it in ranked_items:
        k = it.get("prec_id") or f"{it.get('category')}:{it.get('case_number')}:{it.get('title')}"
        if k not in seen:
            seen.add(k)
            deduped.append(it)

    bucket_counts = {
        "direct_basis": len([it for it in deduped if it.get("basis_bucket") == "direct_basis"]),
        "similar_basis": len([it for it in deduped if it.get("basis_bucket") == "similar_basis"]),
        "risk_basis": len([it for it in deduped if it.get("basis_bucket") == "risk_basis"]),
        "evidence_basis": len([it for it in deduped if it.get("basis_bucket") == "evidence_basis"]),
        "statute_or_admin_basis": len([it for it in deduped if it.get("basis_bucket") == "statute_or_admin_basis"]),
        "weak_reference": len([it for it in deduped if it.get("basis_bucket") == "weak_reference"]),
    }

    direct_count = bucket_counts["direct_basis"]
    support_count = bucket_counts["similar_basis"] + bucket_counts["evidence_basis"]
    reference_count = bucket_counts["weak_reference"]

    debug_info = {
        "raw_query": raw_query or "",
        "target_tax": target_tax,
        "category_filter": category,
        "tax_type_filter": tax_type,
        "primary_topics": primary_topics[:10],
        "tax_issues": tax_issues[:10],
        "biz_contexts": biz_contexts[:10],
        "expanded_keywords": expanded_kws[:10],
        "excluded_tokens": excluded_tokens[:20],
        "search_strategy": strat,
        "search_queries": search_queries[:MAX_PRIMARY_QUERIES],
        "query_logs": query_logs,
        "candidate_count_before_filter": len(all_items),
        "candidate_count_after_category_filter": len(filtered_by_cat),
        "candidate_count_after_exclude": len(working_items),
        "deduped_count": len(deduped),
        "direct_basis_count": direct_count,
        "support_basis_count": support_count,
        "reference_basis_count": reference_count,
        "bucket_counts": bucket_counts,
        "no_direct_basis_reason": "" if direct_count else "거래대상(primary_topics)과 세무쟁점(tax_issues)이 동시에 매칭된 공식자료가 없습니다.",
        "top_results": [
            {
                "case_number": it.get("case_number", ""),
                "title": it.get("title", ""),
                "search_path": it.get("search_path", "직접 검색 결과"),
                "basis_bucket": it.get("basis_bucket", ""),
                "basis_bucket_name": it.get("basis_bucket_name", ""),
                "basis_type": it.get("basis_type", ""),
                "relevance_score": it.get("relevance_score", 0),
                "match_reason": it.get("match_reason", ""),
                "matched_keywords": it.get("matched_keywords", [])
            }
            for it in deduped[:8]
        ]
    }

    # 🚨 AI 하이브리드 재정렬 적용 (타임아웃 방지를 위해 상위 25개만 전달)
    try:
        from summarizer import rerank_cases_with_ai
        top_candidates = deduped[:25]
        if top_candidates:
            ai_reranked = rerank_cases_with_ai(raw_query or " ".join(keywords), top_candidates, limit=limit)
            if ai_reranked:
                ai_selected_ids = {c.get("prec_id") or c.get("case_number") for c in ai_reranked}
                remainders = [c for c in deduped if (c.get("prec_id") or c.get("case_number")) not in ai_selected_ids]
                final_list = ai_reranked + remainders
                debug_info["ai_rerank_applied"] = True
                debug_info["ai_selected_count"] = len(ai_reranked)
                return {
                    "total": len(final_list),
                    "items": final_list[:limit],
                    "all_items": final_list,
                    "debug": debug_info,
                    "api_errors": api_errors,
                    "error_type": None,
                    "error_category": None,
                    "error": None
                }
    except Exception as e:
        debug_info["ai_rerank_applied"] = False
        debug_info["ai_rerank_error"] = str(e)[:120]

    total_cnt = len(deduped)
    debug_info["ai_rerank_applied"] = debug_info.get("ai_rerank_applied", False)

    err_type = None
    err_cat = None
    err_msg = None
    if total_cnt == 0:
        err_type, err_cat, err_msg = _determine_final_error(api_errors)

    return {
        "total": total_cnt,
        "items": deduped[:limit],
        "all_items": deduped,
        "debug": debug_info,
        "api_errors": api_errors,
        "error_type": err_type,
        "error_category": err_cat,
        "error": err_msg
    }


def fetch_prec_detail(prec_id: str, oc_key: Optional[str] = None) -> Dict[str, Any]:
    """
    국가법령정보센터 DRF 상세 API(lawService.do)를 호출하여 
    판례(prec) 및 조세심판례(ttSpecialDecc)의 전문, 주문, 이유를 가져옵니다.
    (메모리 캐시 _PREC_DETAIL_CACHE 적용)
    """
    if not prec_id:
        return {}
    
    # 0. 메모리 캐시 확인
    p_key = str(prec_id).strip()
    if p_key in _PREC_DETAIL_CACHE:
        return _PREC_DETAIL_CACHE[p_key]
    
    oc = (config.get_law_oc() if oc_key is None else oc_key).strip()
    if not oc:
        return {
            "total": 0,
            "items": [],
            "error_type": "LAW_API_ERROR",
            "error": "[국가법령정보센터 API 설정 오류] 법제처 Open API 사용자 인증키(OC)가 설정되지 않았습니다. .env 파일에 LAW_API_KEY를 입력해 주세요."
        }

    def clean_html(root_node, tag_name: str) -> str:
        val = root_node.findtext(tag_name) or ""
        val = re.sub(r'<br\s*/?>', '\n', val, flags=re.IGNORECASE)
        val = re.sub(r'<[^>]+>', ' ', val)
        val = re.sub(r'[ \t]+', ' ', val)
        val = re.sub(r'\n\s*\n+', '\n\n', val)
        return val.strip()

    # 1. 조세심판례 (decc:일련번호) 상세 조회
    if str(prec_id).startswith("decc:"):
        raw_id = str(prec_id).replace("decc:", "").strip()
        digits_only = re.findall(r'^\d+', raw_id)
        target_id = digits_only[0] if digits_only else raw_id
        if target_id.isdigit():
            url = f"{DRF_SERVICE_URL}?OC={oc}&target=ttSpecialDecc&ID={target_id}&type=XML"
            try:
                resp = _SESSION.get(url, headers=_DEFAULT_HEADERS, timeout=(2.5, 5.0))
                if resp.status_code == 200 and len(resp.content) >= 150:
                    root = ET.fromstring(resp.content)
                    title = root.findtext("사건명") or ""
                    c_no = root.findtext("청구번호") or root.findtext("사건번호") or ""
                    d_str = root.findtext("의결일자") or root.findtext("선고일자") or ""
                    court = root.findtext("재결청") or "조세심판원"
                    order_txt = clean_html(root, "주문")
                    reason_txt = clean_html(root, "이유") or clean_html(root, "판단")
                    summary_txt = clean_html(root, "재결요지") or clean_html(root, "사건개요")
                    if not summary_txt or summary_txt == title:
                        summary_txt = (reason_txt[:400] + "...") if len(reason_txt) > 400 else reason_txt
                    if not summary_txt:
                        summary_txt = title
                    ref_art = clean_html(root, "참조조문") or clean_html(root, "세목")
                    res = {
                        "prec_id": prec_id,
                        "case_name": title,
                        "case_number": c_no,
                        "date": d_str,
                        "court": court,
                        "points": title,
                        "summary": summary_txt,
                        "ref_articles": ref_art,
                        "ref_precs": "",
                        "order": order_txt,
                        "reason": reason_txt,
                        "has_detail": bool(summary_txt or order_txt or reason_txt)
                    }
                    _PREC_DETAIL_CACHE[p_key] = res
                    return res
            except Exception:
                pass
        return {}

    # 2. 일반 판례 (prec) 상세 조회
    raw_prec_id = str(prec_id).replace("prec:", "").strip()
    digits_only = re.findall(r'^\d+', raw_prec_id)
    target_prec_id = digits_only[0] if digits_only else raw_prec_id
    if not target_prec_id.isdigit():
        return {}

    url = f"{DRF_SERVICE_URL}?OC={oc}&target=prec&ID={target_prec_id}&type=XML"
    try:
        resp = _SESSION.get(url, headers=_DEFAULT_HEADERS, timeout=(2.5, 5.0))
        if resp.status_code != 200 or len(resp.content) < 150:
            return {}
        
        root = ET.fromstring(resp.content)

        prec_point = clean_html(root, "판시사항")
        prec_summary = clean_html(root, "판결요지")
        ref_articles = clean_html(root, "참조조문")
        ref_precs = clean_html(root, "참조판례")
        order_text = clean_html(root, "주문")
        reason_text = clean_html(root, "이유")
        full_content = clean_html(root, "판례내용")

        # 판례내용에서 【주문】과 【이유】 정밀 추출 보완
        if not order_text and full_content:
            m_ord = re.search(r'【\s*주\s*문\s*】\s*(.*?)(?=【|$)', full_content, re.DOTALL)
            if m_ord:
                order_text = m_ord.group(1).strip()
        if not reason_text and full_content:
            m_rsn = re.search(r'【\s*이\s*유\s*】\s*(.*?)$', full_content, re.DOTALL)
            if m_rsn:
                reason_text = m_rsn.group(1).strip()

        # 요지가 비어있을 경우 이유 첫 단락 또는 판시사항으로 summary 보강
        title_txt = root.findtext("사건명") or ""
        if not prec_summary or prec_summary == title_txt:
            if reason_text:
                prec_summary = (reason_text[:400] + "...") if len(reason_text) > 400 else reason_text
            elif prec_point:
                prec_summary = prec_point
            elif full_content:
                prec_summary = (full_content[:400] + "...") if len(full_content) > 400 else full_content
            else:
                prec_summary = title_txt

        res = {
            "prec_id": prec_id,
            "case_name": title_txt,
            "case_number": root.findtext("사건번호") or "",
            "date": root.findtext("선고일자") or "",
            "court": root.findtext("법원명") or "",
            "points": prec_point,          # 판시사항
            "summary": prec_summary,       # 판결요지 (실제 판결 이유 결합)
            "ref_articles": ref_articles,  # 참조조문
            "ref_precs": ref_precs,        # 참조판례
            "order": order_text,           # 주문
            "reason": reason_text,         # 이유
            "has_detail": bool(prec_point or prec_summary or order_text or reason_text or full_content)
        }
        _PREC_DETAIL_CACHE[p_key] = res
        return res
    except Exception:
        return {}


def enrich_cases_with_details(cases: List[Dict[str, Any]], oc: Optional[str] = None, max_items: int = 15) -> List[Dict[str, Any]]:
    """
    상위 후보 판례/결정례(최대 max_items건)의 판결요지, 판시사항, 주문, 이유를
    DRF 상세 API(lawService.do)를 통해 고속 병렬(ThreadPoolExecutor)로 조회하여 결합합니다.
    - 검색 결과의 summary, full_text, points, reason, order, ref_articles가 실제 본문으로 갱신됨
    - AI가 제목만 보던 방식에서 실제 법원의 판단(이유/요지)을 읽을 수 있도록 변환
    """
    if not cases:
        return []
    
    actual_oc = (config.get_law_oc() if oc is None else oc).strip()
    target_items = cases[:max_items]
    
    def _enrich_single(case: Dict[str, Any]) -> Dict[str, Any]:
        p_id = case.get("prec_id")
        if not p_id:
            return case
        
        detail = fetch_prec_detail(p_id, actual_oc)
        if detail and detail.get("has_detail"):
            case["points"] = detail.get("points", "")
            case["order"] = detail.get("order", "")
            case["reason"] = detail.get("reason", "")
            case["ref_articles"] = detail.get("ref_articles", "")
            case["ref_precs"] = detail.get("ref_precs", "")
            
            detail_summary = detail.get("summary", "")
            if detail_summary and detail_summary != case.get("title"):
                case["summary"] = detail_summary
            
            # full_text도 상세 본문(판결요지/판시사항/주문/이유)을 포함하도록 확장
            ft_parts = [case.get("full_text", "")]
            if detail.get("points"):
                ft_parts.append(f"【판시사항】 {detail['points']}")
            if detail_summary and detail_summary != case.get("title"):
                ft_parts.append(f"【판결요지】 {detail_summary}")
            if detail.get("order"):
                ft_parts.append(f"【주문】 {detail['order']}")
            if detail.get("reason"):
                ft_parts.append(f"【이유】 {detail['reason'][:1500]}")
            if detail.get("ref_articles"):
                ft_parts.append(f"【참조조문】 {detail['ref_articles']}")
            
            case["full_text"] = "\n".join(ft_parts)
            case["has_detail"] = True
        return case

    if target_items:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(target_items), 8)) as executor:
            enriched_targets = list(executor.map(_enrich_single, target_items))
    else:
        enriched_targets = []
    
    return enriched_targets + cases[max_items:]
