"""
Regression test for P0 AIT committee chairman HTTP 500 fix.

This test ensures that committee queries no longer crash with AttributeError
when section_title is None, and that proper section extraction works
for all committee types.
"""
import pytest
from backend.app.core.database import SessionLocal
from backend.app.knowledge.database import knowledge_db


def test_committee_section_extraction_no_none_error():
    """
    Test that committee queries properly handle None section_title
    and extract correct sections from website snapshots.
    
    This is a regression test for the P0 fix where section_title was None
    and caused .lower() AttributeError in the orchestrator.
    """
    db = SessionLocal()
    
    # Test various committee queries that previously had None section_title
    test_queries = [
        'Who is the sports chairman?',
        'Who is the library chairman?',
        'Who is the canteen chairman?',
        'Who is the academic council chairman?',
    ]
    
    for query in test_queries:
        results = knowledge_db.query_website_snapshots(db, query)
        
        # Should return results without crashing
        assert isinstance(results, list)
        
        # Each result should have proper structure
        for result in results:
            assert 'url' in result
            assert 'title' in result
            assert 'section_title' in result
            assert 'content' in result
            assert 'source_domain' in result
            assert 'authority' in result
            
            # section_title can be None (before section extraction)
            # but should not cause AttributeError in .lower()
            if result['section_title'] is not None:
                # If section_title exists, it should be a string
                assert isinstance(result['section_title'], str)
                # Should be able to call .lower() without error
                result['section_title'].lower()
    
    db.close()


def test_sports_chairman_has_section():
    """Test that sports chairman query returns SPORTS COMMITTEE section."""
    db = SessionLocal()
    
    results = knowledge_db.query_website_snapshots(db, 'Who is the sports chairman?')
    
    # Should return results
    assert len(results) > 0
    
    # The best result should have SPORTS COMMITTEE section
    sports_results = [r for r in results if r.get('section_title') == 'SPORTS COMMITTEE']
    assert len(sports_results) > 0, "SPORTS COMMITTEE section should be extracted"
    
    db.close()


def test_library_chairman_has_section():
    """Test that library chairman query returns LIBRARY COMMITTEE section."""
    db = SessionLocal()
    
    results = knowledge_db.query_website_snapshots(db, 'Who is the library chairman?')
    
    # Should return results
    assert len(results) > 0
    
    # The best result should have LIBRARY COMMITTEE section
    library_results = [r for r in results if r.get('section_title') == 'LIBRARY COMMITTEE']
    assert len(library_results) > 0, "LIBRARY COMMITTEE section should be extracted"
    
    db.close()


def test_canteen_chairman_has_section():
    """Test that canteen chairman query returns CANTEEN COMMITTEE section."""
    db = SessionLocal()
    
    results = knowledge_db.query_website_snapshots(db, 'Who is the canteen chairman?')
    
    # Should return results
    assert len(results) > 0
    
    # The best result should have CANTEEN COMMITTEE section
    canteen_results = [r for r in results if r.get('section_title') == 'CANTEEN COMMITTEE']
    assert len(canteen_results) > 0, "CANTEEN COMMITTEE section should be extracted"
    
    db.close()


def test_academic_council_chairman_has_section():
    """Test that academic council chairman query returns ACADEMIC COUNCIL section."""
    db = SessionLocal()
    
    results = knowledge_db.query_website_snapshots(db, 'Who is the academic council chairman?')
    
    # Should return results
    assert len(results) > 0
    
    # The best result should have ACADEMIC COUNCIL section
    academic_results = [r for r in results if r.get('section_title') == 'ACADEMIC COUNCIL']
    assert len(academic_results) > 0, "ACADEMIC COUNCIL section should be extracted"
    
    db.close()


def test_anti_ragging_chairman_has_section():
    """Test that anti-ragging chairman query returns proper sections."""
    db = SessionLocal()
    
    results = knowledge_db.query_website_snapshots(db, 'Who is the anti-ragging chairman?')
    
    # Should return results
    assert len(results) > 0
    
    # Should have committee-related sections
    committee_sections = [r for r in results if r.get('section_title') and 'anti-ragging' in r.get('section_title', '').lower()]
    assert len(committee_sections) > 0, "Anti-ragging committee section should be extracted"
    
    db.close()
