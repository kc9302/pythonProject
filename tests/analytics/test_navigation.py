import pytest
from xapi_tools.analytics.navigation import count_page_views

def test_count_page_views_simple():
    """
    Test counting 'navigated' verbs.
    """
    statements = [
        # View 1
        {
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-1"}
        },
        # View 2 (different page)
        {
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-2"}
        },
        # View 3 (same page)
        {
             "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
             "object": {"id": "http://example.com/page-1"}
        },
        # Other verb (ignored)
        {
             "verb": {"id": "http://adlnet.gov/expapi/verbs/initialized"},
             "object": {"id": "http://example.com/page-1"}
        }
    ]
    
    
    assert count_page_views(statements) == 3

def test_find_popular_paths():
    from xapi_tools.analytics.navigation import find_popular_paths
    statements = [
        # Session 1: A -> B -> C
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-A"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}}
        },
        {
            "timestamp": "2024-01-01T10:05:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-B"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}}
        },
        {
            "timestamp": "2024-01-01T10:10:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-C"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}}
        },
        
        # Session 2: A -> B -> D
        {
            "timestamp": "2024-01-02T10:00:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-A"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s2"}}
        },
        {
            "timestamp": "2024-01-02T10:05:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-B"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s2"}}
        },
        {
            "timestamp": "2024-01-02T10:10:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-D"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s2"}}
        }
    ]
    
    # Paths:
    # s1: A->B, B->C
    # s2: A->B, B->D
    # Result: A->B (2), B->C (1), B->D (1)
    
    paths = find_popular_paths(statements)
    
    # Helper to check presence
    # Assuming list of tuples or string representation "A -> B"
    # Let's assume list of dicts or tuples: [ ("A", "B"), count ]
    # Or dict: { "A -> B": 2 }
    
    assert paths["http://example.com/page-A -> http://example.com/page-B"] == 2
    assert paths["http://example.com/page-B -> http://example.com/page-C"] == 1
    assert paths["http://example.com/page-B -> http://example.com/page-D"] == 1

def test_calc_avg_time_on_page():
    from xapi_tools.analytics.navigation import calc_avg_time_on_page
    statements = [
        # Session 1
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-A"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}}
        },
        {
            "timestamp": "2024-01-01T10:05:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-B"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}}
        },
        {
            "timestamp": "2024-01-01T10:10:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-C"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}}
        },
        # Session 1 Termination (optional, can help define time for page C)
        {
            "timestamp": "2024-01-01T10:15:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/session/1.0/verbs/terminated"}, # Or generic terminated
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}}
        },
        
        # Session 2
        {
            "timestamp": "2024-01-02T10:00:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-A"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s2"}}
        },
        {
            "timestamp": "2024-01-02T10:10:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-B"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s2"}}
        }
    ]
    
    # Times:
    # s1: A (10:00->10:05 = 300s), B (10:05->10:10 = 300s), C (10:10->10:15 = 300s)
    # s2: A (10:00->10:10 = 600s), B (10:10->? unknown/ignored)
    
    # Avg A: (300 + 600) / 2 = 450.0
    # Avg B: (300) / 1 = 300.0  (s2 B ignored)
    # Avg C: (300) / 1 = 300.0
    
    analysis = calc_avg_time_on_page(statements)
    
    assert analysis["http://example.com/page-A"] == 450.0
    assert analysis["http://example.com/page-B"] == 300.0
    assert analysis["http://example.com/page-C"] == 300.0

def test_identify_exit_pages():
    from xapi_tools.analytics.navigation import identify_exit_pages
    statements = [
        # Session 1: A -> B -> C (Exit C)
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-A"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}}
        },
        {
            "timestamp": "2024-01-01T10:05:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-B"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}}
        },
        {
            "timestamp": "2024-01-01T10:10:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-C"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}}
        },
        
        # Session 2: A -> B (Exit B)
        {
            "timestamp": "2024-01-02T10:00:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-A"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s2"}}
        },
        {
            "timestamp": "2024-01-02T10:05:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-B"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s2"}}
        },
        
        # Session 3: A (Exit A)
        {
            "timestamp": "2024-01-03T10:00:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated"},
            "object": {"id": "http://example.com/page-A"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s3"}}
        }
    ]
    
    exits = identify_exit_pages(statements)
    
    assert exits["http://example.com/page-A"] == 1
    assert exits["http://example.com/page-B"] == 1
    assert exits["http://example.com/page-C"] == 1
    assert "http://example.com/page-D" not in exits



