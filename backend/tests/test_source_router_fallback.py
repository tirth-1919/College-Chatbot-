"""Regression test: unmatched, non-greeting queries must NOT fall through to
the "greeting" route — they should route to "general_educational" so they
reach the AI fallback path and are logged as knowledge gaps instead of
getting the generic welcome message.
"""
from backend.app.knowledge.source_router import SourceRouter


def _route(text):
    return SourceRouter.route_query(text, intent_info={}, entities={})


def test_offtopic_query_routes_to_general_educational():
    assert _route("Who is the current Chief Minister of Gujarat?") == "general_educational"


def test_various_unmatched_queries_route_to_general_educational():
    for q in [
        "What is the population of India?",
        "Tell me a joke",
        "Who wrote the Ramayana?",
    ]:
        assert _route(q) == "general_educational", q


def test_real_greetings_still_route_to_greeting():
    for q in ["hi", "hello", "hey", "good morning", "good evening", "Hello!"]:
        assert _route(q) == "greeting", q


def test_classified_greeting_still_routes_to_greeting():
    result = SourceRouter.route_query(
        "hi there", intent_info={"intent": "GREETING"}, entities={}
    )
    assert result == "greeting"
