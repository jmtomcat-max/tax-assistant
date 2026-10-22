import inspect
import unittest
from pathlib import Path
from unittest.mock import patch

from repositories.tax_knowledge_repo import TaxKnowledgeRepository, _has_sufficient_relevance, _is_index_document, _is_relevant, _search_tokens
from repositories.review_repo import SqliteReviewRepository
from repositories.knowledge_search import KnowledgeSearchService
from summarizer import _format_internal_knowledge_context, _knowledge_sources
from law_api import ERR_NETWORK_ERROR, MAX_PRIMARY_QUERIES, MAX_RESCUE_QUERIES, _has_network_error, _record_error, search_real_law_data_multi
from components.sidebar import _navigation_signature
from components.ui_elements import _notion_block_html, format_notion_content
from services import analysis_pipeline
from views.view_search import _build_analysis_snapshot_key, _build_briefing_cache_key, _format_pipeline_timings, _load_or_run_analysis


class TaxKnowledgeRepositoryTest(unittest.TestCase):
    def test_analysis_pipeline_is_ui_free_and_dispatches_documents(self):
        self.assertNotIn("streamlit", inspect.getsource(analysis_pipeline))
        with patch.object(analysis_pipeline, "analyze_document_situation", return_value={"kind": "document"}) as document:
            result = analysis_pipeline.analyze_question("질문", [{"name": "검토서"}], [])
        self.assertEqual({"kind": "document"}, result)
        document.assert_called_once()

    def test_analysis_snapshot_changes_only_with_user_search_context(self):
        base = _build_analysis_snapshot_key("RCPS 전환", "법인세", "no_files", "종합 검토", "전체", ["RCPS"])
        self.assertEqual(base, _build_analysis_snapshot_key("RCPS 전환", "법인세", "no_files", "종합 검토", "전체", ["RCPS"]))
        self.assertNotEqual(base, _build_analysis_snapshot_key("RCPS 전환", "법인세", "no_files", "과세관청 입장", "전체", ["RCPS"]))
        self.assertNotEqual(base, _build_analysis_snapshot_key("RCPS 전환", "법인세", "no_files", "종합 검토", "전체", ["전환"] ))

    def test_official_search_query_budget_is_bounded(self):
        self.assertEqual(4, MAX_PRIMARY_QUERIES)
        self.assertEqual(1, MAX_RESCUE_QUERIES)

    def test_pipeline_timing_text_marks_cached_stages(self):
        self.assertEqual(
            "내부 지식 0.2초 · 공식자료 검색 캐시",
            _format_pipeline_timings({"내부 지식": 0.24, "공식자료 검색": None}),
        )

    def test_card_rerun_keeps_current_analysis_cache_key(self):
        args = ("RCPS 전환 세무이슈", "법인세", "전체", ["RCPS", "전환"], 3)
        self.assertNotIn("knowledge_version", inspect.signature(_build_briefing_cache_key).parameters)
        self.assertNotIn("hash(knowledge_version)", inspect.getsource(_load_or_run_analysis))
        self.assertEqual(
            _build_briefing_cache_key(*args, files_hash_str="no_files"),
            _build_briefing_cache_key(*args, files_hash_str="no_files"),
        )

    def test_ai_summary_html_cannot_break_result_cards(self):
        self.assertEqual("", format_notion_content("</div>"))
        rendered = format_notion_content("검토 내용 <script>alert(1)</script>")
        self.assertNotIn("<script>", rendered)
        self.assertIn("검토 내용", rendered)

    def test_ai_summary_card_is_compact_balanced_html(self):
        rendered = _notion_block_html("nb-gray", "⚖️", "판단 기준", "검토 내용")
        self.assertNotIn("\n", rendered)
        self.assertEqual(rendered.count("<div"), rendered.count("</div>"))

    def test_navigation_signature_is_stable_across_widget_reruns(self):
        self.assertEqual(
            _navigation_signature("new_review", None),
            _navigation_signature("new_review", None),
        )
        self.assertNotEqual(
            _navigation_signature("new_review", None),
            _navigation_signature("vault", None),
        )

    def test_law_api_error_logging_does_not_mask_original_error(self):
        errors = []
        _record_error(errors, ERR_NETWORK_ERROR, "연결 실패", "테스트", "prec")
        self.assertEqual(ERR_NETWORK_ERROR, errors[0]["error_type"])
        self.assertTrue(_has_network_error(errors))
        self.assertFalse(_has_network_error([]))

    def test_network_failure_stops_secondary_and_rescue_calls(self):
        def fail_prec(query, oc, display=35, error_list=None):
            _record_error(error_list, ERR_NETWORK_ERROR, "연결 실패", query, "prec")
            return []

        with patch("law_api.fetch_prec_from_drf", side_effect=fail_prec) as prec, \
             patch("law_api.fetch_decc_from_drf") as decc, \
             patch("law_api.fetch_expc_from_drf") as expc:
            search_real_law_data_multi(
                ["퇴직임원"], oc_key="test", raw_query="퇴직임원 세무 검토",
                intent_data={"search_strategy": {"direct_queries": ["퇴직임원"]}},
            )
        self.assertLessEqual(prec.call_count, 3)
        decc.assert_not_called()
        expc.assert_not_called()

    def test_korean_particles_are_stripped_for_search(self):
        tokens = _search_tokens("판매장려금을 거래처에 지급한 경우")
        self.assertIn("판매장려금", tokens)
        self.assertIn("거래처", tokens)
        self.assertNotIn("경우", tokens)

    def test_internal_knowledge_requires_two_meaningful_matches(self):
        tokens = _search_tokens("합계세금계산서 미발행 가산세 여부")
        self.assertTrue(_is_relevant(tokens, "합계세금계산서", "미발행 가산세 검토"))
        self.assertFalse(_is_relevant(tokens, "법인세 가산세", "계약서 검토"))
        rcps_tokens = _search_tokens("RCPS 전환 시 세무상 검토 해야할 내용은")
        self.assertFalse(_has_sufficient_relevance(rcps_tokens, {"전환", "세무상", "내용"}))
        self.assertTrue(_has_sufficient_relevance(rcps_tokens, {"rcps", "전환", "세무상"}))

    def test_obsidian_index_pages_are_not_treated_as_tax_evidence(self):
        index = "# M Project\n- [[RCPS 전환에 따른 세무 이슈]]\n- [[잠재부실 보고]]\n- [[회의록]]"
        self.assertTrue(_is_index_document(index))
        self.assertFalse(_is_index_document("RCPS 전환 시 증여의제와 시가 산정 기준을 검토한 본문입니다."))
        self.assertTrue(_is_relevant(_search_tokens("RCPS 전환 세무이슈"), "RCPS 전환에 따른 세무 이슈", "증여의제 검토"))

    def test_missing_database_is_safe(self):
        missing = Path(__file__).with_name("missing_tax_knowledge.db")
        repo = TaxKnowledgeRepository(missing)
        self.assertEqual([], repo.search("부가가치세"))
        self.assertEqual("missing", repo.get_database_version())

    def test_internal_context_is_bounded_and_traceable(self):
        hits = [{
            "document_id": 7,
            "title": "퇴직임원 고문료",
            "source_path": "30_Knowledge/세무/test.md",
            "excerpt": "가" * 2000,
            "content_sha256": "abc",
            "score": 3.2,
        }]
        context = _format_internal_knowledge_context(hits)
        self.assertIn("내부검토 K7", context)
        self.assertLess(len(context), 1400)
        self.assertEqual(7, _knowledge_sources(hits)[0]["document_id"])

    def test_review_history_persists_internal_sources(self):
        db_path = Path(__file__).with_name("_review_history_test.db")
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(db_path) + suffix)
            if candidate.exists():
                candidate.unlink()
        try:
            repo = SqliteReviewRepository(
                db_path=str(db_path),
                legacy_json_path=None,
                legacy_audit_path=None,
            )
            source = {
                "document_id": 7,
                "title": "퇴직임원 고문료",
                "source_path": "30_Knowledge/세무/test.md",
                "content_sha256": "abc",
                "score": 3.2,
            }
            record_id, is_new = repo.save_review(
                query="퇴직임원 고문료는 손금인가?",
                tax_category="법인세",
                core_issue="손금산입",
                active_keywords=["퇴직임원", "고문료"],
                risk_level="중립/유의",
                briefing_conclusion="실제 업무 수행 입증 필요",
                checklist=["계약서"],
                direct_basis_count=0,
                total_results_count=0,
                top_cases=[],
                knowledge_sources=[source],
            )
            saved = repo.get_by_id(record_id)
            self.assertTrue(is_new)
            self.assertEqual(7, saved["knowledge_sources"][0]["document_id"])
            self.assertEqual([7], saved["revisions"][0]["knowledge_document_ids"])
            self.assertEqual("candidate", saved["knowledge_status"])

            self.assertTrue(repo.set_knowledge_status(record_id, "approved", "reviewer@company.com", "근거 확인"))
            approved = repo.get_approved_records("퇴직임원")
            self.assertEqual(record_id, approved[0]["id"])
            self.assertEqual("reviewer@company.com", approved[0]["knowledge_reviewed_by"])

            class FakeTaxRepo:
                def get_database_version(self):
                    return "test"

                def search(self, query, limit=5):
                    return [{
                        "document_id": 99,
                        "title": "Obsidian 참고자료",
                        "source_path": "tax.md",
                        "excerpt": "참고",
                        "content_sha256": "xyz",
                        "score": 1,
                    }][:limit]

            combined = KnowledgeSearchService(tax_repo=FakeTaxRepo(), review_repo=repo).search("퇴직임원", 5)
            self.assertEqual("approved_review", combined[0]["knowledge_type"])
            self.assertEqual("obsidian", combined[1]["knowledge_type"])
            self.assertIn("승인검토 R", _format_internal_knowledge_context(combined))

            self.assertTrue(repo.set_feedback(record_id, "helpful", "user@company.com", "실무에 유용"))
            feedback_record = repo.get_by_id(record_id)
            self.assertEqual("helpful", feedback_record["feedback_rating"])
            self.assertEqual(1, repo.get_kpi_stats()["feedback_counts"]["helpful"])
            with self.assertRaises(ValueError):
                repo.set_feedback(record_id, "needs_correction", "user@company.com", "")
            self.assertTrue(repo.set_feedback(record_id, "needs_correction", "user@company.com", "근거 보완 필요"))
            with self.assertRaises(ValueError):
                repo.resolve_feedback(record_id, "reviewer@company.com", "")
            self.assertTrue(repo.resolve_feedback(record_id, "reviewer@company.com", "근거를 재확인함"))
            resolved = repo.get_by_id(record_id)
            self.assertTrue(resolved["feedback_resolved_at"])
            self.assertEqual("reviewer@company.com", resolved["feedback_resolved_by"])

            with self.assertRaises(ValueError):
                repo.set_knowledge_status(record_id, "rejected", "reviewer@company.com", "")

            repo.save_review(
                query="퇴직임원 고문료는 손금인가?",
                tax_category="법인세",
                core_issue="손금산입",
                active_keywords=["퇴직임원", "고문료"],
                risk_level="중립/유의",
                briefing_conclusion="재검토 결과",
                checklist=["계약서"],
                direct_basis_count=0,
                total_results_count=0,
                top_cases=[],
                knowledge_sources=[source],
            )
            self.assertEqual("candidate", repo.get_by_id(record_id)["knowledge_status"])
            self.assertEqual([], repo.get_approved_records("퇴직임원"))
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = Path(str(db_path) + suffix)
                if candidate.exists():
                    candidate.unlink()


if __name__ == "__main__":
    unittest.main()
