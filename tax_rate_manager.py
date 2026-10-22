# -*- coding: utf-8 -*-
"""
tax_rate_manager.py
세법상 세율, 한도, 가산세율 마스터 데이터(tax_rates.json) 관리 및 검증 모듈
- 거래일자 기준 유효한 세율 선택 (effective_start <= trans_date <= effective_end)
- 사람이 확인한 review_status == 'verified' 항목만 실제 계산에 반영
- review_status == 'needs_review' 항목은 자동 갱신 대기 상태로 분리하고 계산에서 격리
"""

import json
import os
from datetime import datetime, date
from typing import Dict, Any, Optional, List, Union

import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TAX_RATES_FILE = config.get_data_file_path("tax_rates.json")


class TaxRateManager:
    """
    tax_rates.json 기반 세율/한도 데이터 로더 및 유효일자 판정 엔진
    """
    _instance = None
    _cached_data = None
    _cache_mtime = None

    def __init__(self, data_file: Optional[str] = None):
        self.data_file = data_file or TAX_RATES_FILE

    def _load_data(self) -> Dict[str, Any]:
        """파일 수정시간(mtime)을 감지하여 안전하게 캐싱/재로드"""
        if not os.path.exists(self.data_file):
            return {"metadata": {}, "vat_penalties": {}, "national_tax_penalties": {}, "amendment_reductions": {}, "statutory_thresholds": {}}

        current_mtime = os.path.getmtime(self.data_file)
        if TaxRateManager._cached_data is not None and TaxRateManager._cache_mtime == current_mtime:
            return TaxRateManager._cached_data

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            TaxRateManager._cached_data = data
            TaxRateManager._cache_mtime = current_mtime
            return data
        except Exception as e:
            if TaxRateManager._cached_data is not None:
                return TaxRateManager._cached_data
            raise RuntimeError(f"tax_rates.json 로드 실패: {e}")

    def save_data(self, data: Dict[str, Any]):
        """안전한 파일 쓰기 및 캐시 갱신"""
        tmp_file = f"{self.data_file}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, self.data_file)
        TaxRateManager._cached_data = data
        TaxRateManager._cache_mtime = os.path.getmtime(self.data_file)

    @staticmethod
    def _normalize_date(d: Optional[Union[str, date, datetime]]) -> str:
        """날짜 객체나 문자열을 YYYY-MM-DD 형식 문자열로 정규화"""
        if not d:
            return datetime.now().strftime("%Y-%m-%d")
        if isinstance(d, datetime):
            return d.strftime("%Y-%m-%d")
        if isinstance(d, date):
            return d.strftime("%Y-%m-%d")
        s = str(d).strip()
        if len(s) == 8 and s.isdigit():
            return f"{s[:4]}-{s[4:6]}-{s[6:]}"
        return s[:10]

    def get_rate_item(
        self,
        category: str,
        key: str,
        transaction_date: Optional[Union[str, date, datetime]] = None,
        only_verified: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        특정 카테고리와 키에 대해 거래일자(transaction_date)에 유효한 세율 항목 조회.
        only_verified=True인 경우 review_status == 'verified'인 항목만 반환 (요구사항 6).
        """
        data = self._load_data()
        cat_dict = data.get(category, {})
        raw_item = cat_dict.get(key)
        if not raw_item:
            return None

        # 상태 검증
        status = raw_item.get("review_status", "needs_review")
        if only_verified and status != "verified":
            # 검증되지 않은 항목은 사용 불가
            return None

        # 거래일자 유효 범위 체크 (요구사항 2, 3)
        target_date_str = self._normalize_date(transaction_date)
        eff_start = raw_item.get("effective_start", "1900-01-01")
        eff_end = raw_item.get("effective_end", "9999-12-31")

        if eff_start <= target_date_str <= eff_end:
            item_copy = dict(raw_item)
            item_copy["applied_date"] = target_date_str
            return item_copy

        return None

    def get_vat_penalty(self, key: str, transaction_date: Optional[Union[str, date, datetime]] = None) -> Optional[Dict[str, Any]]:
        """부가가치세 가산세 항목 조회"""
        return self.get_rate_item("vat_penalties", key, transaction_date, only_verified=True)

    def get_national_tax_penalty(self, key: str, transaction_date: Optional[Union[str, date, datetime]] = None) -> Optional[Dict[str, Any]]:
        """국세기본법 가산세 항목 조회"""
        return self.get_rate_item("national_tax_penalties", key, transaction_date, only_verified=True)

    def get_amendment_reduction(self, period_code: str, transaction_date: Optional[Union[str, date, datetime]] = None) -> Optional[Dict[str, Any]]:
        """수정신고 감면율 항목 조회"""
        return self.get_rate_item("amendment_reductions", period_code, transaction_date, only_verified=True)

    def get_statutory_threshold(self, key: str, transaction_date: Optional[Union[str, date, datetime]] = None) -> Optional[Dict[str, Any]]:
        """법정 한도 항목 조회"""
        return self.get_rate_item("statutory_thresholds", key, transaction_date, only_verified=True)

    def list_all_rates(self, category: Optional[str] = None) -> Dict[str, Any]:
        """모든 세율 및 검토 상태 목록 조회 (관리용)"""
        data = self._load_data()
        if category:
            return data.get(category, {})
        return data

    def get_all_rates(self, category: Optional[str] = None) -> Dict[str, Any]:
        """list_all_rates의 별칭 (호환성 제공)"""
        return self.list_all_rates(category)

    def update_review_status(self, category: str, key: str, new_status: str, verified_date: Optional[str] = None) -> bool:
        """사람이 검토 후 상태를 변경 (verified <-> needs_review) (요구사항 6)"""
        data = self._load_data()
        if category in data and key in data[category]:
            data[category][key]["review_status"] = new_status
            if new_status == "verified":
                data[category][key]["last_verified_date"] = verified_date or datetime.now().strftime("%Y-%m-%d")
            self.save_data(data)
            return True
        return False


# 싱글톤 인스턴스 편의 제공
tax_rate_mgr = TaxRateManager()
