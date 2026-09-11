import pytest
from backend.app.intelligence.language import language_engine
from backend.app.intelligence.intent import intent_classifier
from backend.app.intelligence.entities import entity_extractor
from backend.app.intelligence.query_rewriter import query_rewriter

def test_multilingual_language_detection():
    # English
    assert language_engine.detect_language("What courses does AIT offer?")["language"] == "en"
    
    # Gujlish (Gujarati in Latin script)
    res_gujlish = language_engine.detect_language("BCA ni fees ketli che?")
    assert res_gujlish["language"] == "gujlish"
    assert res_gujlish["canonical_lang"] == "gu"

    # Hinglish (Hindi in Latin script)
    res_hinglish = language_engine.detect_language("BCA ki fees kitni hai?")
    assert res_hinglish["language"] == "hinglish"
    assert res_hinglish["canonical_lang"] == "hi"

    # Native Gujarati script
    res_gu = language_engine.detect_language("કોલેજ માં લાયબ્રેરી છે?")
    assert res_gu["language"] == "gu"

def test_intent_classification():
    # Fee lookup
    assert intent_classifier.classify_intent("What are the BCA fees?")["intent"] == "fee_lookup"
    assert intent_classifier.classify_intent("BCA ni fees ketli che?")["intent"] == "fee_lookup"

    # Image request
    img_intent = intent_classifier.classify_intent("Show me the AIT library")
    assert img_intent["intent"] == "image_request"

    # Faculty lookup
    assert intent_classifier.classify_intent("Who teaches DBMS?")["intent"] == "faculty_lookup"

    # Placement info
    assert intent_classifier.classify_intent("Tell me about AIT placements")["intent"] == "placement_info"

    # General educational
    assert intent_classifier.classify_intent("What is normalization in DBMS?")["intent"] == "general_educational"

def test_entity_extraction():
    res = entity_extractor.extract_entities("BCA sem 2 na subjects?")
    assert "BCA (Bachelor of Computer Applications)" in res["programs"]
    assert res["semester"] == 2

    res2 = entity_extractor.extract_entities("Who teaches DBMS at AIT?")
    assert "Database Management Systems" in res2["subjects"]

    res3 = entity_extractor.extract_entities("Show me computer lab and library")
    assert "Computer Laboratories" in res3["facilities"]
    assert "Central Library" in res3["facilities"]

def test_query_rewriter():
    res = query_rewriter.rewrite_query("BCA ni fees ketli che?", "gujlish")
    assert res["is_rewritten"] == True
    assert "what is" in res["normalized_query"].lower()
