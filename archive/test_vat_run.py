# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
from vat_penalty import VatPenaltyEngine

engine = VatPenaltyEngine()

# 테스트 케이스:
# 공급가액 10억원, 매출,
# 실무자가 실수로 [세금계산서 미발급], [전자전송 미전송], [합계표 미제출]을 모두 체크했다고 가정
res = engine.calculate(
    supply_value=1000000000, # 10억원
    trans_type="매출",
    selected_violations=["세금계산서_미발급", "전자세금계산서_미전송", "매출처별합계표_미제출"],
    include_reporting_penalty=True,
    unpaid_tax_amount=100000000, # 부가세 1억원
    delay_days=180,
    is_fraud=False,
    amendment_period="3개월이내" # 50% 감면
)

print(f"공급가액: {res['supply_value']:,}원")
print(f"적용된 세금계산서 가산세 총액: {res['vat_penalty_total']:,}원")
for it in res['active_vat_items']:
    print(f" - [적용] {it['name']} ({it['rate_str']}): {it['final_amount']:,}원 | {it['legal_basis']}")

print(f"\n중복 배제로 면제된 가산세 (절감액): {res['saved_amount']:,}원")
for ex in res['excluded_records']:
    print(f" - [중복배제 면제] {ex['item']['name']} ({ex['item']['rate_str']}): {ex['item']['raw_amount']:,}원")
    print(f"   · 사유: {ex['reason']}")

print(f"\n신고/납부지연 가산세 총액: {res['reporting_penalty_total']:,}원")
for rp in res['reporting_items']:
    print(f" - [신고/납부] {rp['name']} ({rp['rate_str']}): {rp['final_amount']:,}원 (감면: {rp['reduction_str']})")

print(f"\n최종 총 가산세: {res['grand_total']:,}원")