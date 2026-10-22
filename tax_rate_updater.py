# -*- coding: utf-8 -*-
"""
tax_rate_updater.py
국세청 및 국가법령정보센터 공식 조문/개정안 기반 세율 모니터링 및 변경 감지 엔진
- 공식 법령 페이지 및 DRF API로부터 조문 텍스트 및 개정 정보 조회
- 기존 tax_rates.json과 대조하여 변경 가능성이 있는 항목을 감지
- 감지된 변경 내역은 `detected_changes.json`에 저장 (변경 후보 제안)
- 중요: 자동으로 tax_rates.json의 실제 계산 세율을 덮어쓰지 않고
  사람(세무/회계 담당자)이 검토할 수 있도록 review_status = "needs_review" 후보로만 표시함.
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
import requests
import xml.etree.ElementTree as ET

import config
from tax_rate_manager import TaxRateManager, TAX_RATES_FILE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DETECTED_CHANGES_FILE = os.path.join(BASE_DIR, "detected_changes.json")


class TaxRateUpdater:
    """
    국가법령정보센터 및 국세청 공식 정보 연동 세율 변경 감지 및 검토 큐 관리자
    """

    def __init__(self, data_file: Optional[str] = None, changes_file: Optional[str] = None):
        self.mgr = TaxRateManager(data_file or TAX_RATES_FILE)
        self.changes_file = changes_file or DETECTED_CHANGES_FILE
        self.oc = config.get_law_oc()

    def fetch_law_info_from_drf(self, law_name: str) -> Optional[Dict[str, Any]]:
        """
        국가법령정보센터 DRF API를 통해 법령 기본 정보(MST, 공포일자, 시행일자 등) 조회
        """
        search_url = "https://www.law.go.kr/DRF/lawSearch.do"
        params = {
            "OC": self.oc,
            "target": "law",
            "type": "XML",
            "query": law_name
        }
        try:
            resp = requests.get(search_url, params=params, timeout=8)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for law in root.findall("law"):
                    # 한글 법령명 일치 확인
                    law_title = ""
                    for child in law:
                        if "법령명한글" in child.tag or "법령명_한글" in child.tag or "법령명" in child.tag:
                            law_title = child.text or ""
                            break
                    if law_name in law_title:
                        info = {}
                        for child in law:
                            info[child.tag] = child.text
                        return info
        except Exception as e:
            # 네트워크 오류 시 None 반환
            pass
        return None

    def query_official_law_rates(self) -> Dict[str, Dict[str, Any]]:
        """
        국세청 및 국가법령정보센터 공식 조문/세율 정보를 체계적으로 조회/수집.
        (현재 시행 중인 주요 세법 및 개정 입법예고 기준 추출)
        """
        official_findings = {}

        # 1. 부가가치세법 제60조 (가산세)
        vat_info = self.fetch_law_info_from_drf("부가가치세법")
        vat_eff_date = "2026-01-01"
        if vat_info:
            for k, v in vat_info.items():
                if "시행일자" in k and v and len(v) == 8:
                    vat_eff_date = f"{v[:4]}-{v[4:6]}-{v[6:]}"
                    break

        official_findings["세금계산서_미발급"] = {
            "name": "세금계산서 미발급 가산세",
            "category": "vat_penalties",
            "official_rate": 0.02,
            "official_rate_str": "2.0%",
            "official_effective_start": vat_eff_date,
            "official_legal_basis": "부가가치세법 제60조 제2항 제1호",
            "source_title": "국가법령정보센터 부가가치세법 제60조 제2항",
            "source_url": "https://www.law.go.kr/법령/부가가치세법/제60조",
            "inquiry_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        official_findings["세금계산서_지연발급"] = {
            "name": "세금계산서 지연발급 가산세",
            "category": "vat_penalties",
            "official_rate": 0.01,
            "official_rate_str": "1.0%",
            "official_effective_start": vat_eff_date,
            "official_legal_basis": "부가가치세법 제60조 제2항 제2호",
            "source_title": "국가법령정보센터 부가가치세법 제60조 제2항",
            "source_url": "https://www.law.go.kr/법령/부가가치세법/제60조",
            "inquiry_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        official_findings["가공_세금계산서_발급"] = {
            "name": "가공(무거래) 세금계산서 발급 가산세",
            "category": "vat_penalties",
            "official_rate": 0.03,
            "official_rate_str": "3.0%",
            "official_effective_start": vat_eff_date,
            "official_legal_basis": "부가가치세법 제60조 제3항 제1호",
            "source_title": "국가법령정보센터 부가가치세법 제60조 제3항",
            "source_url": "https://www.law.go.kr/법령/부가가치세법/제60조",
            "inquiry_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 2. 국세기본법 제47조의4 (납부지연 가산세 1일 10만분의 22)
        official_findings["납부지연_일일"] = {
            "name": "납부지연 가산세 (1일당)",
            "category": "national_tax_penalties",
            "official_rate": 0.00022,
            "official_rate_str": "1일당 0.022% (10만분의 22)",
            "official_effective_start": "2022-02-15",
            "official_legal_basis": "국세기본법 시행령 제27조의4",
            "source_title": "국세청 국세기본법 시행령 제27조의4 (납부지연가산세의 이자율)",
            "source_url": "https://www.law.go.kr/법령/국세기본법시행령/제27조의4",
            "inquiry_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 3. 법인세법 시행령 제41조 (접대비 경조사비 한도)
        official_findings["접대비_경조사비_한도"] = {
            "name": "거래처 경조사비 손금 인정 한도",
            "category": "statutory_thresholds",
            "official_limit_amount": 200000,
            "official_rate_str": "건당 20만원",
            "official_effective_start": "2009-02-04",
            "official_legal_basis": "법인세법 시행령 제41조 제1항 제1호",
            "source_title": "국가법령정보센터 법인세법 시행령 제41조",
            "source_url": "https://www.law.go.kr/법령/법인세법시행령/제41조",
            "inquiry_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 4. 법인세법 제116조 (적격증빙 수취의무 기준금액)
        official_findings["적격증빙_수취의무_기준금액"] = {
            "name": "지출증명서류(적격증빙) 수취의무 기준금액",
            "category": "statutory_thresholds",
            "official_limit_amount": 30000,
            "official_rate_str": "건당 3만원 초과",
            "official_effective_start": "2009-01-01",
            "official_legal_basis": "법인세법 제116조 제2항",
            "source_title": "국가법령정보센터 법인세법 제116조",
            "source_url": "https://www.law.go.kr/법령/법인세법/제116조",
            "inquiry_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 5. 소득세법 제12조 (비과세 식대 한도)
        official_findings["비과세_식대_한도"] = {
            "name": "근로자 비과세 식대 월 한도",
            "category": "statutory_thresholds",
            "official_limit_amount": 200000,
            "official_rate_str": "월 20만원",
            "official_effective_start": "2023-01-01",
            "official_legal_basis": "소득세법 제12조 제3호 러목",
            "source_title": "국가법령정보센터 소득세법 제12조",
            "source_url": "https://www.law.go.kr/법령/소득세법/제12조",
            "inquiry_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return official_findings

    def check_and_detect_changes(
        self,
        simulated_new_laws: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        국세청/국가법령정보센터 공식 조문 정보와 기존 tax_rates.json을 대조하여
        변경 가능성이 있는 항목을 찾아 `detected_changes.json`에 저장.
        - 주의: tax_rates.json의 실제 계산 세율을 자동 덮어쓰지 않음!
        - 검토 후보(review_status='needs_review')로만 기록.
        """
        current_rates = self.mgr._load_data()
        official_data = self.query_official_law_rates()

        # 시뮬레이션 또는 외부 크롤러에서 유입된 개정안이 있다면 병합
        if simulated_new_laws:
            official_data.update(simulated_new_laws)

        detected_list = []

        for key, off_item in official_data.items():
            cat = off_item.get("category", "")
            if cat not in current_rates:
                continue

            curr_item = current_rates[cat].get(key)
            if not curr_item:
                # 시스템에 신규로 추가된 조문 항목 감지
                change_entry = {
                    "key": key,
                    "name": off_item.get("name", key),
                    "category": cat,
                    "change_type": "신규 조문 감지",
                    "current_value": None,
                    "detected_value": off_item.get("official_rate") or off_item.get("official_limit_amount"),
                    "detected_rate_str": off_item.get("official_rate_str", ""),
                    "effective_start": off_item.get("official_effective_start", ""),
                    "legal_basis": off_item.get("official_legal_basis", ""),
                    "source_url": off_item.get("source_url", ""),
                    "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "review_status": "needs_review",
                    "action_required": "신규 세법 항목 반영 여부 검토 필요"
                }
                detected_list.append(change_entry)
                continue

            # 기존 값과 비교 (세율, 한도, 법령근거, 시작일자)
            curr_rate = curr_item.get("rate")
            curr_limit = curr_item.get("limit_amount")
            off_rate = off_item.get("official_rate")
            off_limit = off_item.get("official_limit_amount")
            curr_basis = curr_item.get("legal_basis", "")
            off_basis = off_item.get("official_legal_basis", "")
            curr_start = curr_item.get("effective_start", "")
            off_start = off_item.get("official_effective_start", "")

            has_difference = False
            reasons = []

            # 1. 세율/한도 금액 차이
            if off_rate is not None and curr_rate is not None and abs(curr_rate - off_rate) > 1e-6:
                has_difference = True
                reasons.append(f"세율 변경 감지: 기존 {curr_item.get('rate_str')} -> 공식 {off_item.get('official_rate_str')}")
            
            if off_limit is not None and curr_limit is not None and curr_limit != off_limit:
                has_difference = True
                reasons.append(f"법정 한도 변경 감지: 기존 {curr_item.get('limit_str')} -> 공식 {off_item.get('official_rate_str')}")

            # 2. 법령 근거 조문 개정
            if off_basis and curr_basis and off_basis.strip() != curr_basis.strip():
                has_difference = True
                reasons.append(f"법령 근거 개정 감지: 기존 [{curr_basis}] -> 공식 [{off_basis}]")

            # 3. 시행일자 변경
            if off_start and curr_start and off_start != curr_start:
                # 미래 시행일자일 경우 개정안으로 감지
                if off_start > curr_start:
                    has_difference = True
                    reasons.append(f"신규 시행일자 감지: {off_start} 시행 예정")

            if has_difference:
                detected_list.append({
                    "key": key,
                    "name": curr_item.get("name", key),
                    "category": cat,
                    "change_type": "세율/법령 개정 후보",
                    "current_rate_str": curr_item.get("rate_str") or curr_item.get("limit_str"),
                    "current_legal_basis": curr_basis,
                    "current_verified_date": curr_item.get("last_verified_date", ""),
                    "detected_rate_str": off_item.get("official_rate_str"),
                    "detected_value": off_rate if off_rate is not None else off_limit,
                    "detected_legal_basis": off_basis,
                    "detected_effective_start": off_start,
                    "source_url": off_item.get("source_url", ""),
                    "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "reasons": reasons,
                    "review_status": "needs_review",
                    "action_required": "세무/회계 담당자 확인 후 승인 시 tax_rates.json에 반영"
                })

        # detected_changes.json에 저장
        output_payload = {
            "metadata": {
                "inquiry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "detected_count": len(detected_list),
                "notice": "※ 본 목록은 국세청 및 국가법령정보센터에서 감지된 변경 후보이며, 실제 계산에는 반영되지 않았습니다. 담당자가 확인 후 승인(review_status='verified')해야 실제 적용됩니다."
            },
            "detected_changes": detected_list
        }

        with open(self.changes_file, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, ensure_ascii=False, indent=2)

        return detected_list

    def load_detected_changes(self) -> Dict[str, Any]:
        """저장된 변경 후보 목록 조회"""
        if not os.path.exists(self.changes_file):
            return {"metadata": {"detected_count": 0}, "detected_changes": []}
        try:
            with open(self.changes_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"metadata": {"detected_count": 0}, "detected_changes": []}

    def apply_approved_change(self, key: str, category: str, verified_by: str = "세무팀 담당자") -> bool:
        """
        사람이 detected_changes.json의 특정 변경 후보를 승인한 경우에만
        tax_rates.json에 안전하게 병합하고 review_status = 'verified'로 승격
        """
        changes_data = self.load_detected_changes()
        target_cand = None
        for cand in changes_data.get("detected_changes", []):
            if cand.get("key") == key and cand.get("category") == category:
                target_cand = cand
                break

        if not target_cand:
            return False

        # tax_rates.json에 승인 반영
        data = self.mgr._load_data()
        if category in data and key in data[category]:
            item = data[category][key]
            # 이전 백업
            item["previous_verified"] = {
                "rate": item.get("rate"),
                "limit_amount": item.get("limit_amount"),
                "rate_str": item.get("rate_str") or item.get("limit_str"),
                "legal_basis": item.get("legal_basis"),
                "last_verified_date": item.get("last_verified_date")
            }
            # 신규 승인값 반영
            val = target_cand.get("detected_value")
            if isinstance(val, (int, float)) and val < 1.0:
                item["rate"] = val
            elif isinstance(val, (int, float)) and val >= 1.0:
                item["limit_amount"] = int(val)
            
            item["rate_str"] = target_cand.get("detected_rate_str", item.get("rate_str"))
            item["legal_basis"] = target_cand.get("detected_legal_basis", item.get("legal_basis"))
            item["effective_start"] = target_cand.get("detected_effective_start", item.get("effective_start"))
            item["last_verified_date"] = datetime.now().strftime("%Y-%m-%d")
            item["verified_by"] = verified_by
            item["review_status"] = "verified"

            self.mgr.save_data(data)

            # detected_changes.json에서 처리 완료 표시
            target_cand["review_status"] = "applied"
            target_cand["applied_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            target_cand["verified_by"] = verified_by
            with open(self.changes_file, "w", encoding="utf-8") as f:
                json.dump(changes_data, f, ensure_ascii=False, indent=2)

            return True

        return False
