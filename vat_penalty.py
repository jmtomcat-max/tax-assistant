# -*- coding: utf-8 -*-
"""
부가가치세 가산세 계산 및 중복적용 배제 엔진
- tax_rates.json 및 tax_rate_manager.py 기반 동적 세율 연동
- 거래일자(transaction_date) 기준 유효 세율 선택
- 부가가치세법 제60조 (가산세)
- 부가가치세법 제60조 제9항 (가산세 중복 적용의 배제)
- 국세기본법 제47조의2~제47조의4 (과소신고, 납부지연 가산세)
- 국세기본법 제48조 (가산세 감면: 수정신고 기한별 감면율)
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
from tax_rate_manager import tax_rate_mgr

BASE_DATE_LABEL = "거래일자 기준 세법 및 국세기본법 적용"
TAX_DISCLAIMER = "※ 본 가산세 계산 결과는 입력된 거래일자, 공급가액 및 지연일수에 기초한 모의 산출 내역이며, 정당한 사유 인정 여부 및 관할 세무서의 최종 결정에 따라 실제 고지세액과 상이할 수 있으므로 구체적 사실관계 확인이 필요합니다."


class VatPenaltyEngine:
    """
    부가가치세 가산세 산출 및 법 제60조 제9항에 따른
    중복 적용 배제 룰을 엄격하게 적용하는 세무 계산 엔진
    (모든 세율 및 법령 기준은 tax_rates.json 기반 검증된 값만 적용)
    """

    def __init__(self):
        self.mgr = tax_rate_mgr

    def calculate(
        self,
        supply_value: float,
        trans_type: str = "매출",  # "매출" or "매입"
        selected_violations: Optional[List[str]] = None,
        include_reporting_penalty: bool = False,
        unpaid_tax_amount: float = 0.0,
        delay_days: int = 0,
        is_fraud: bool = False,
        amendment_period: str = "미신고/경정",
        transaction_date: Optional[Union[str, date, datetime]] = None
    ) -> Dict[str, Any]:
        """
        거래일자(transaction_date) 기준 가산세 산출 및 중복배제 필터링 수행
        """
        selected_violations = selected_violations or []
        supply_value = max(0.0, float(supply_value))
        unpaid_tax_amount = max(0.0, float(unpaid_tax_amount))
        delay_days = max(0, int(delay_days))
        
        # 거래일자 정규화
        trans_date_str = self.mgr._normalize_date(transaction_date)

        # 개별 가산세 항목 후보군
        items = {}

        # ---------------- 1. 매출(공급자) 세금계산서 가산세 ----------------
        if trans_type == "매출":
            sales_violation_keys = [
                "세금계산서_미발급",
                "세금계산서_지연발급",
                "가공_세금계산서_발급",
                "위장_세금계산서_발급",
                "사실과다른_세금계산서_발급",
                "전자세금계산서_미전송",
                "전자세금계산서_지연전송",
                "매출처별합계표_미제출",
                "매출처별합계표_지연제출"
            ]
            for v_key in sales_violation_keys:
                if v_key in selected_violations:
                    rate_info = self.mgr.get_vat_penalty(v_key, trans_date_str)
                    if rate_info:
                        rate_val = rate_info["rate"]
                        items[v_key] = {
                            "name": rate_info["name"],
                            "rate_str": rate_info["rate_str"],
                            "rate": rate_val,
                            "base": supply_value,
                            "raw_amount": supply_value * rate_val,
                            "legal_basis": rate_info["legal_basis"],
                            "source_url": rate_info.get("source_url", ""),
                            "last_verified_date": rate_info.get("last_verified_date", ""),
                            "effective_start": rate_info.get("effective_start", ""),
                            "effective_end": rate_info.get("effective_end", ""),
                            "category": rate_info.get("category", "세금계산서 발급 불성실")
                        }

        # ---------------- 2. 매입(공급받는자) 세금계산서 가산세 ----------------
        else:
            purchase_violation_keys = [
                "세금계산서_지연수취",
                "가공_세금계산서_수취",
                "위장_세금계산서_수취",
                "매입처별합계표_불성실"
            ]
            for v_key in purchase_violation_keys:
                if v_key in selected_violations:
                    rate_info = self.mgr.get_vat_penalty(v_key, trans_date_str)
                    if rate_info:
                        rate_val = rate_info["rate"]
                        items[v_key] = {
                            "name": rate_info["name"],
                            "rate_str": rate_info["rate_str"],
                            "rate": rate_val,
                            "base": supply_value,
                            "raw_amount": supply_value * rate_val,
                            "legal_basis": rate_info["legal_basis"],
                            "source_url": rate_info.get("source_url", ""),
                            "last_verified_date": rate_info.get("last_verified_date", ""),
                            "effective_start": rate_info.get("effective_start", ""),
                            "effective_end": rate_info.get("effective_end", ""),
                            "category": rate_info.get("category", "수취 불성실")
                        }

        # ---------------- 3. 중복 적용 배제 필터링 (부가가치세법 제60조 제9항) ----------------
        excluded_records = []

        # 룰 A: 가공(3%)/위장(2%) 발급이 적용되면 -> 미발급(2%), 지연발급(1%), 사실과다른, 합계표(0.5%) 배제
        has_fake_issue = ("가공_세금계산서_발급" in items) or ("위장_세금계산서_발급" in items)
        if has_fake_issue:
            for target_k in ["세금계산서_미발급", "세금계산서_지연발급", "사실과다른_세금계산서_발급", "매출처별합계표_미제출", "매출처별합계표_지연제출"]:
                if target_k in items:
                    reason = "부가가치세법 제60조 제9항에 의거, 가공·위장 발급 가산세가 적용되므로 중복 배제됨"
                    excluded_records.append({"key": target_k, "item": items.pop(target_k), "reason": reason})

        # 룰 B: 미발급(2%) 가산세가 적용되면 -> 지연발급(1%), 전송(미전송/지연전송), 합계표(미제출/지연제출) 배제
        if "세금계산서_미발급" in items:
            for target_k in ["세금계산서_지연발급", "전자세금계산서_미전송", "전자세금계산서_지연전송", "매출처별합계표_미제출", "매출처별합계표_지연제출"]:
                if target_k in items:
                    reason = "부가가치세법 제60조 제9항 제1호에 의거, 세금계산서 미발급 가산세(2%)가 부과되므로 전자전송 및 합계표 가산세는 중복 배제됨"
                    excluded_records.append({"key": target_k, "item": items.pop(target_k), "reason": reason})

        # 룰 C: 지연발급(1%) 가산세가 적용되면 -> 전송(미전송/지연전송), 합계표(지연/미제출) 배제
        if "세금계산서_지연발급" in items:
            for target_k in ["전자세금계산서_미전송", "전자세금계산서_지연전송", "매출처별합계표_미제출", "매출처별합계표_지연제출"]:
                if target_k in items:
                    reason = "부가가치세법 제60조 제9항 제2호에 의거, 세금계산서 지연발급 가산세(1%)가 부과되므로 전자전송 및 합계표 가산세는 중복 배제됨"
                    excluded_records.append({"key": target_k, "item": items.pop(target_k), "reason": reason})

        # 룰 D: 전송 미전송/지연전송 가산세가 부과되는 경우 -> 합계표 가산세 배제
        has_transfer_pen = ("전자세금계산서_미전송" in items) or ("전자세금계산서_지연전송" in items)
        if has_transfer_pen:
            for target_k in ["매출처별합계표_미제출", "매출처별합계표_지연제출"]:
                if target_k in items:
                    reason = "부가가치세법 제60조 제9항 제3호에 의거, 전자세금계산서 전송불성실 가산세가 부과되므로 합계표 가산세는 중복 배제됨"
                    excluded_records.append({"key": target_k, "item": items.pop(target_k), "reason": reason})

        # 룰 E: 매입 쪽 가공/위장 수취 시 -> 지연수취(0.5%), 합계표불성실 배제
        has_fake_recv = ("가공_세금계산서_수취" in items) or ("위장_세금계산서_수취" in items)
        if has_fake_recv:
            for target_k in ["세금계산서_지연수취", "매입처별합계표_불성실"]:
                if target_k in items:
                    reason = "부가가치세법 제60조 제9항에 의거, 가공·위장 세금계산서 수취 가산세가 적용되므로 지연수취 및 합계표 가산세는 중복 배제됨"
                    excluded_records.append({"key": target_k, "item": items.pop(target_k), "reason": reason})

        # ---------------- 4. 국세기본법 신고불성실 & 납부지연 가산세 계산 ----------------
        reporting_items = []
        if include_reporting_penalty and unpaid_tax_amount > 0:
            # 1) 과소신고 가산세 (국세기본법 제47조의3)
            pen_type = "과소신고_부당" if is_fraud else "과소신고_일반"
            r_info = self.mgr.get_national_tax_penalty(pen_type, trans_date_str)
            r_rate = r_info["rate"] if r_info else (0.40 if is_fraud else 0.10)
            r_rate_str = r_info["rate_str"] if r_info else ("40.0% (부당과소)" if is_fraud else "10.0% (일반과소)")
            r_raw = unpaid_tax_amount * r_rate

            # 수정신고 감면율 적용 (국세기본법 제48조 제2항)
            reduction_rate = 0.0
            reduction_str = "0% (감면 없음)"
            red_info = self.mgr.get_amendment_reduction(amendment_period, trans_date_str)
            if red_info:
                reduction_rate = red_info["reduction_rate"]
                reduction_str = red_info["reduction_str"]

            r_final = r_raw * (1.0 - reduction_rate)

            reporting_items.append({
                "name": "과소신고 가산세",
                "rate_str": r_rate_str,
                "base": unpaid_tax_amount,
                "raw_amount": r_raw,
                "reduction_str": reduction_str,
                "reduction_rate": reduction_rate,
                "final_amount": r_final,
                "legal_basis": r_info.get("legal_basis", "국세기본법 제47조의3 및 제48조 제2항") if r_info else "국세기본법 제47조의3",
                "source_url": r_info.get("source_url", "") if r_info else "",
                "last_verified_date": r_info.get("last_verified_date", "") if r_info else "",
                "category": "신고 불성실"
            })

            # 2) 납부지연 가산세 (국세기본법 제47조의4)
            if delay_days > 0:
                delay_info = self.mgr.get_national_tax_penalty("납부지연_일일", trans_date_str)
                daily_rate = delay_info.get("daily_rate", 22.0 / 100000.0) if delay_info else (22.0 / 100000.0)
                p_delay_rate = delay_days * daily_rate
                p_delay_amt = unpaid_tax_amount * p_delay_rate
                reporting_items.append({
                    "name": f"납부지연 가산세 ({delay_days}일 경과)",
                    "rate_str": f"1일당 {daily_rate*100:.3f}% (총 {p_delay_rate*100:.3f}%)",
                    "base": unpaid_tax_amount,
                    "raw_amount": p_delay_amt,
                    "reduction_str": "감면 없음 (이자 성격)",
                    "reduction_rate": 0.0,
                    "final_amount": p_delay_amt,
                    "legal_basis": delay_info.get("legal_basis", "국세기본법 제47조의4 (1일 10만분의 22)") if delay_info else "국세기본법 제47조의4",
                    "source_url": delay_info.get("source_url", "") if delay_info else "",
                    "last_verified_date": delay_info.get("last_verified_date", "") if delay_info else "",
                    "category": "납부 불성실"
                })

        # 최종 집계
        active_vat_items = list(items.values())
        for it in active_vat_items:
            it["final_amount"] = it["raw_amount"]
            it["reduction_str"] = "감면 대상 아님 (세금계산서 가산세는 수정신고 감면 배제)"

        vat_penalty_total = sum(it["final_amount"] for it in active_vat_items)
        reporting_penalty_total = sum(it["final_amount"] for it in reporting_items)
        grand_total = vat_penalty_total + reporting_penalty_total

        # 중복 배제로 절감된 금액
        saved_amount = sum(ex["item"]["raw_amount"] for ex in excluded_records)

        return {
            "transaction_date": trans_date_str,
            "base_date": trans_date_str,
            "base_date_label": f"{trans_date_str} 기준 유효 법령 및 검증 세율 적용",
            "disclaimer": TAX_DISCLAIMER,
            "supply_value": supply_value,
            "trans_type": trans_type,
            "active_vat_items": active_vat_items,
            "excluded_records": excluded_records,
            "reporting_items": reporting_items,
            "vat_penalty_total": vat_penalty_total,
            "reporting_penalty_total": reporting_penalty_total,
            "grand_total": grand_total,
            "saved_amount": saved_amount
        }
