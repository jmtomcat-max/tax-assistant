"""
특수관계인(특수관계자) 판별 및 지배구조 분석 엔진
- 국세기본법 제2조 제20호 및 시행령 제1조의2
- 법인세법 제2조 제12호 및 시행령 제2조 제5항
- 상속세및증여세법 제2조 제10호 및 시행령 제2조의2
"""

from typing import Dict, List, Any, Set, Tuple, Optional

BASE_DATE = "2026-01-01"
BASE_DATE_LABEL = "2026년 1월 1일 시행 상법·법인세법·국세기본법 기준"
TAX_DISCLAIMER = "※ 본 특수관계인 판정 결과는 입력된 지분율 및 임원/친족 관계에 기초한 1차 시뮬레이션이며, 실질적 영향력 행사 여부 및 지배구조 변동 등 세법상 실질과세 원칙에 따라 과세관청의 해석이 달라질 수 있습니다. (구체적 거래 전 사실관계 확인 필요)"


class TaxRelationEngine:
    """
    법인 및 주주 지분 구조, 친족 관계, 임원 관계를 종합하여
    선택한 기준 주체(Focus Subject)와의 특수관계 성립 여부를 판정하는 엔진
    """

    def __init__(self):
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.shareholdings: List[Dict[str, Any]] = []
        self.kinships: List[Dict[str, Any]] = []
        self.executives: List[Dict[str, Any]] = []

    def load_structure(
        self,
        shareholdings: List[Dict[str, Any]],
        kinships: Optional[List[Dict[str, Any]]] = None,
        executives: Optional[List[Dict[str, Any]]] = None
    ):
        """지분 구조, 친족 관계, 임원 현황 데이터 적재"""
        self.shareholdings = shareholdings or []
        self.kinships = kinships or []
        self.executives = executives or []

        self.entities = {}
        for sh in self.shareholdings:
            comp = sh["company"].strip()
            holder = sh["shareholder"].strip()
            if comp and comp not in self.entities:
                self.entities[comp] = {"name": comp, "type": "법인"}
            if holder and holder not in self.entities:
                self.entities[holder] = {
                    "name": holder,
                    "type": "법인" if any(s["company"].strip() == holder for s in self.shareholdings) else "개인"
                }

        for ex in self.executives:
            p = ex["person"].strip()
            c = ex["company"].strip()
            if p not in self.entities:
                self.entities[p] = {"name": p, "type": "개인"}
            if c not in self.entities:
                self.entities[c] = {"name": c, "type": "법인"}

        for kn in self.kinships:
            p1 = kn["person1"].strip()
            p2 = kn["person2"].strip()
            if p1 not in self.entities:
                self.entities[p1] = {"name": p1, "type": "개인"}
            if p2 not in self.entities:
                self.entities[p2] = {"name": p2, "type": "개인"}

    def set_entity_type(self, name: str, ent_type: str):
        """개인/법인 타입 명시적 지정"""
        if name in self.entities:
            self.entities[name]["type"] = ent_type
        else:
            self.entities[name] = {"name": name, "type": ent_type}

    def get_direct_shares(self, shareholder: str, company: str) -> float:
        """직접 지분율 (%) 반환"""
        total = 0.0
        for sh in self.shareholdings:
            if sh["company"].strip() == company.strip() and sh["shareholder"].strip() == shareholder.strip():
                try:
                    total += float(sh.get("ratio", 0.0))
                except (ValueError, TypeError):
                    pass
        return round(total, 2)

    def get_all_companies(self) -> List[str]:
        """등록된 법인 목록 반환"""
        comps = set()
        for sh in self.shareholdings:
            comps.add(sh["company"].strip())
        for ex in self.executives:
            comps.add(ex["company"].strip())
        for name, data in self.entities.items():
            if data.get("type") == "법인":
                comps.add(name)
        return sorted(list(comps))

    def get_kin_group(self, person: str) -> Set[str]:
        """본인 및 친족(배우자, 4촌이내 혈족, 3촌이내 인척) 그룹 반환"""
        kins = {person}
        for kn in self.kinships:
            p1 = kn["person1"].strip()
            p2 = kn["person2"].strip()
            if p1 == person:
                kins.add(p2)
            elif p2 == person:
                kins.add(p1)
        return kins

    def get_aggregated_direct_shares(self, person_or_group: Any, company: str) -> float:
        """본인 및 친족 합산 직접 지분율 계산"""
        if isinstance(person_or_group, str):
            group = self.get_kin_group(person_or_group)
        else:
            group = set(person_or_group)

        tot = 0.0
        for m in group:
            tot += self.get_direct_shares(m, company)
        return round(tot, 2)

    def compute_indirect_shares(self, shareholder: str, target_company: str, visited: Optional[Set[str]] = None) -> float:
        """
        다단계 간접 출자 지분율 계산 (승산방식)
        예: 갑 -> 법인A (40%), 법인A -> 법인B (100%) => 40% * 100% = 40%
        """
        if visited is None:
            visited = set()

        if shareholder == target_company:
            return 0.0

        visited.add(shareholder)
        total_indirect = 0.0

        for sh in self.shareholdings:
            mid_comp = sh["company"].strip()
            holder = sh["shareholder"].strip()

            if holder == shareholder and mid_comp != target_company and mid_comp not in visited:
                try:
                    r1 = float(sh.get("ratio", 0.0)) / 100.0
                except (ValueError, TypeError):
                    r1 = 0.0

                if r1 <= 0:
                    continue

                r2 = self.get_direct_shares(mid_comp, target_company) / 100.0
                total_indirect += (r1 * r2 * 100.0)

                sub_indirect = self.compute_indirect_shares(mid_comp, target_company, visited.copy())
                total_indirect += (r1 * sub_indirect)

        return round(total_indirect, 2)

    def check_pair_related(self, sub: str, tar: str) -> Tuple[bool, str, List[str], Dict[str, Any]]:
        """두 주체 (sub -> tar) 간의 일방적 특수관계 여부 판정"""
        sub_type = self.entities.get(sub, {}).get("type", "개인")
        tar_type = self.entities.get(tar, {}).get("type", "개인")

        is_related = False
        reasons = []
        rel_type = "일반 관계"
        detail_metrics = {}

        # 1. 개인 - 개인
        if sub_type == "개인" and tar_type == "개인":
            for kn in self.kinships:
                p1 = kn["person1"].strip()
                p2 = kn["person2"].strip()
                rel_name = kn.get("relation", "친족")
                if (p1 == sub and p2 == tar) or (p2 == sub and p1 == tar):
                    is_related = True
                    rel_type = f"친족 관계 ({rel_name})"
                    reasons.append(f"국세기본법 제2조 제20호 가목 및 동법 시행령 제1조의2 제1항 (친족: {rel_name})")
                    break

            for ex in self.executives:
                if ex["person"].strip() == tar:
                    comp = ex["company"].strip()
                    sub_shares = self.get_aggregated_direct_shares(sub, comp)
                    if sub_shares >= 30.0:
                        is_related = True
                        rel_type = "지배주주와 소속 임원"
                        reasons.append(f"법인세법 시행령 제2조 제5항 제1호 (본인이 {sub_shares}% 출자한 {comp}의 임원)")

        # 2. 개인 - 법인
        elif sub_type == "개인" and tar_type == "법인":
            for ex in self.executives:
                if ex["person"].strip() == sub and ex["company"].strip() == tar:
                    is_related = True
                    role = ex.get("role", "임원")
                    rel_type = f"소속 임원 ({role})"
                    reasons.append(f"법인세법 시행령 제2조 제5항 제1호 (임원·사용인과 소속 법인)")

            direct_share = self.get_direct_shares(sub, tar)
            agg_share = self.get_aggregated_direct_shares(sub, tar)
            detail_metrics["direct_share"] = direct_share
            detail_metrics["agg_share"] = agg_share

            if agg_share >= 30.0:
                is_related = True
                rel_type = f"경영지배/출자법인 (본인+친족 {agg_share}%)"
                reasons.append(f"법인세법 시행령 제2조 제5항 제2호·제3호 (지배주주 및 친족이 30% 이상 출자한 법인)")
            elif agg_share > 0:
                rel_type = f"단순 주주 (지분 {agg_share}%)"

            indirect_share = self.compute_indirect_shares(sub, tar)
            detail_metrics["indirect_share"] = indirect_share
            if indirect_share >= 30.0:
                is_related = True
                rel_type = f"간접 지배법인 (간접지분 {indirect_share}%)"
                reasons.append(f"상증세법 시행령 제2조의2 / 법인세법 제2조 제12호 (간접 출자 지분 30% 이상 경영지배)")

        # 3. 법인 - 개인
        elif sub_type == "법인" and tar_type == "개인":
            for ex in self.executives:
                if ex["person"].strip() == tar and ex["company"].strip() == sub:
                    is_related = True
                    role = ex.get("role", "임원")
                    rel_type = f"소속 임원 ({role})"
                    reasons.append(f"법인세법 시행령 제2조 제5항 제1호 (법인과 그 임원·사용인)")

            tar_direct = self.get_direct_shares(tar, sub)
            tar_agg = self.get_aggregated_direct_shares(tar, sub)
            detail_metrics["direct_share"] = tar_direct
            detail_metrics["agg_share"] = tar_agg

            if tar_agg >= 30.0:
                is_related = True
                rel_type = f"지배주주 (친족합산 {tar_agg}%)"
                reasons.append(f"법인세법 시행령 제2조 제5항 제2호 (발행주식총수의 30% 이상을 소유한 지배주주 및 친족)")
            elif tar_agg > 0:
                rel_type = f"출자 주주 ({tar_agg}%)"

            for sh in self.shareholdings:
                if sh["company"].strip() == sub:
                    holder = sh["shareholder"].strip()
                    h_shares = self.get_aggregated_direct_shares(holder, sub)
                    if h_shares >= 30.0 and tar in self.get_kin_group(holder):
                        is_related = True
                        rel_type = f"지배주주({holder})의 친족"
                        reasons.append(f"법인세법 시행령 제2조 제5항 제2호 (지배주주 {holder}의 친족)")
                        break

            # 간접 지배주주 여부 (상증세법 / 법인세법)
            ind_share = self.compute_indirect_shares(tar, sub)
            detail_metrics["indirect_share"] = ind_share
            if ind_share >= 30.0:
                is_related = True
                rel_type = f"간접 지배주주 (간접지분 {ind_share}%)"
                reasons.append(f"법인세법 제2조 제12호 / 상증세법 시행령 제2조의2 (간접지분율 30% 이상 지배주주)")

        # 4. 법인 - 법인
        elif sub_type == "법인" and tar_type == "법인":
            direct_b_in_a = self.get_direct_shares(sub, tar)
            direct_a_in_b = self.get_direct_shares(tar, sub)
            detail_metrics["direct_to_target"] = direct_b_in_a
            detail_metrics["direct_from_target"] = direct_a_in_b

            if direct_b_in_a >= 50.0 or direct_a_in_b >= 50.0:
                is_related = True
                rel_type = f"모자회사 관계 (지분 {max(direct_b_in_a, direct_a_in_b)}%)"
                reasons.append(f"법인세법 시행령 제2조 제5항 제3호 가목 (50% 이상 직접 출자 법인)")
            elif direct_b_in_a >= 30.0 or direct_a_in_b >= 30.0:
                is_related = True
                rel_type = f"경영지배 출자관계 (지분 {max(direct_b_in_a, direct_a_in_b)}%)"
                reasons.append(f"법인세법 시행령 제2조 제5항 제3호 나목 (30% 이상 출자 경영지배법인)")

            for common_holder, h_info in self.entities.items():
                if common_holder in [sub, tar]:
                    continue
                sh_sub = self.get_aggregated_direct_shares(common_holder, sub)
                sh_tar = self.get_aggregated_direct_shares(common_holder, tar)

                if (sh_sub >= 30.0 and sh_tar >= 30.0) or (sh_sub >= 50.0 and sh_tar >= 30.0) or (sh_sub >= 30.0 and sh_tar >= 50.0):
                    is_related = True
                    rel_type = f"동일 지배주주({common_holder}) 산하 관계회사"
                    reasons.append(
                        f"법인세법 시행령 제2조 제5항 제3호 다목 (동일 지배주주 {common_holder}가 {sub} {sh_sub}%, {tar} {sh_tar}% 동시 지배)"
                    )
                    break

            ind_1 = self.compute_indirect_shares(sub, tar)
            ind_2 = self.compute_indirect_shares(tar, sub)
            max_ind = max(ind_1, ind_2)
            if max_ind >= 30.0:
                is_related = True
                rel_type = f"다단계 계열/간접출자 관계 (간접 {max_ind}%)"
                reasons.append(f"법인세법 제2조 제12호 / 상증세법 시행령 제2조의2 (간접지분율 30% 이상 지배관계)")

        return is_related, rel_type, reasons, detail_metrics

    def analyze_relations(self, subject: str, law_type: str = "법인세법") -> Dict[str, Any]:
        """
        기준 주체(subject)를 바탕으로 등록된 모든 다른 주체들과의
        특수관계인 성립 여부 및 법적 근거 판정 (쌍방관계 원칙 반영)
        """
        subject = subject.strip()
        sub_type = self.entities.get(subject, {}).get("type", "개인")

        results = []
        all_targets = sorted([name for name in self.entities.keys() if name != subject])

        for target in all_targets:
            tar_type = self.entities.get(target, {}).get("type", "개인")

            # 1. 정방향 분석 (subject -> target)
            is_rel_1, rel_type_1, reasons_1, metrics_1 = self.check_pair_related(subject, target)

            # 2. 역방향 분석 (target -> subject) - 법인세법 제2조 제12호 / 시행령 제2조 제6항 (어느 한쪽이 특수관계인이면 상대방도 특수관계인)
            is_rel_2, rel_type_2, reasons_2, metrics_2 = self.check_pair_related(target, subject)

            is_related = is_rel_1 or is_rel_2
            all_reasons = list(dict.fromkeys(reasons_1 + reasons_2))
            
            if is_rel_1:
                final_rel_type = rel_type_1
            elif is_rel_2:
                final_rel_type = f"{rel_type_2} (쌍방주의)"
                all_reasons.append("법인세법 시행령 제2조 제6항 (쌍방관계 원칙: 상대방의 특수관계인에 해당)")
            else:
                final_rel_type = "일반 관계"

            clean_reasons = list(dict.fromkeys(all_reasons))

            results.append({
                "target": target,
                "target_type": tar_type,
                "is_related": is_related,
                "status": "특수관계 성립 (🔴)" if is_related else "특수관계 미성립 (⚪)",
                "rel_type": final_rel_type,
                "reasons": clean_reasons,
                "legal_basis": " / ".join(clean_reasons) if clean_reasons else "법령상 지분 요건(30%/50%) 및 인적 요건 미충족",
                "metrics": {**metrics_1, **metrics_2}
            })

        results.sort(key=lambda x: (not x["is_related"], x["target"]))
        related_count = sum(1 for r in results if r["is_related"])

        return {
            "subject": subject,
            "subject_type": sub_type,
            "law_type": law_type,
            "total_targets": len(results),
            "related_count": related_count,
            "items": results
        }