"""Search and analysis operations used by the search screen."""

import config
from law_api import search_real_law_data_multi
from repositories.knowledge_search import get_knowledge_search_service
from summarizer import (
    analyze_document_situation,
    analyze_tax_situation,
    generate_situation_briefing,
)


def load_internal_knowledge(query: str, limit: int = 5):
    """Return internal knowledge without allowing a DB failure to stop analysis."""
    try:
        search = get_knowledge_search_service()
        return search.search(query, limit=limit), "", search.get_version()
    except Exception as exc:
        return [], str(exc)[:200], "missing"


def analyze_question(query: str, files_data_list: list, knowledge_hits: list):
    if files_data_list:
        return analyze_document_situation(files_data_list, query)
    return analyze_tax_situation(query, knowledge_hits=knowledge_hits)


def search_official_sources(query, tax_type, category, keywords, limit, intent_data):
    return search_real_law_data_multi(
        keywords=keywords,
        category=category,
        tax_type=tax_type,
        oc_key=config.get_law_oc(),
        limit=limit,
        raw_query=query,
        intent_data=intent_data,
    )


def create_briefing(query, intent_data, results, knowledge_hits):
    return generate_situation_briefing(
        query, intent_data, results, knowledge_hits=knowledge_hits
    )
