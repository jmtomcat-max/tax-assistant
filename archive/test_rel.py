# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
from tax_relations import TaxRelationEngine

engine = TaxRelationEngine()

shares = [
    {"company": "법인A", "shareholder": "갑", "ratio": 40.0},
    {"company": "법인A", "shareholder": "을", "ratio": 30.0},
    {"company": "법인A", "shareholder": "병", "ratio": 30.0},
    {"company": "법인B", "shareholder": "법인A", "ratio": 100.0},
    {"company": "법인B", "shareholder": "정", "ratio": 0.0},
]
kinships = [
    {"person1": "갑", "person2": "을", "relation": "배우자"}
]
execs = [
    {"person": "갑", "company": "법인A", "role": "대표이사"},
    {"person": "정", "company": "법인B", "role": "대표이사"}
]

engine.load_structure(shares, kinships, execs)

print("=== [기준: 갑] 특관자 분석 ===")
res_gap = engine.analyze_relations("갑")
for item in res_gap["items"]:
    print(f"{item['target']} ({item['target_type']}) -> {item['status']} | {item['rel_type']} | {item['legal_basis']}")

print("\n=== [기준: 법인B] 특관자 분석 ===")
res_b = engine.analyze_relations("법인B")
for item in res_b["items"]:
    print(f"{item['target']} ({item['target_type']}) -> {item['status']} | {item['rel_type']} | {item['legal_basis']}")