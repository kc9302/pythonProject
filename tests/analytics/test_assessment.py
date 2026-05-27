import pytest
from xapi_tools.analytics.assessment import count_attempts

def test_count_attempts_simple():
    """
    Test counting valid assessment attempts ('started' verbs).
    """
    statements = [
        # Attempt 1
        {
            "verb": {
                "id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/started"
            },
            "object": {
                "id": "http://example.com/assessment-1"
            }
        },
        # Interaction (not started)
        {
             "verb": {
                "id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/answered"
            },
             "object": {
                "id": "http://example.com/assessment-1"
            }
        },
        # Attempt 2 (different assessment)
        {
            "verb": {
                "id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/started"
            },
            "object": {
                "id": "http://example.com/assessment-2"
            }
        },
        # Attempt 3 (same assessment, separate attempt)
        {
            "verb": {
                "id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/started"
            },
            "object": {
                "id": "http://example.com/assessment-1"
            }
        }
    ]
    
    
    # Total 'started' verbs
    assert count_attempts(statements) == 3

def test_calc_completion_rate():
    from xapi_tools.analytics.assessment import calc_completion_rate
    statements = [
        # Attempt 1: Started and Completed
        {"verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/started"}},
        {"verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/completed"}},
        
        # Attempt 2: Started only
        {"verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/started"}},
        
        # Attempt 3: Started and Completed
        {"verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/started"}},
        {"verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/completed"}},
        
        # Attempt 4: Started only
        {"verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/started"}},
    ]
    
    # 4 attempts, 2 completions = 50%
    assert calc_completion_rate(statements) == 0.5

def test_calc_avg_score():
    from xapi_tools.analytics.assessment import calc_avg_score
    statements = [
        # Completed with score 0.8
        {
            "verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/completed"},
            "result": {"score": {"scaled": 0.8}}
        },
         # Completed with score 1.0
        {
            "verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/completed"},
            "result": {"score": {"scaled": 1.0}}
        },
        # Completed but no score (rare but possible, ignore or count as 0? usually ignore logic)
        {
            "verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/completed"},
             "result": {}
        },
        # Started (ignore)
        {
             "verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/started"},
             "result": {"score": {"scaled": 0.5}} # Abnormal but ignore non-completed
        }
    ]
    
    
    # (0.8 + 1.0) / 2 = 0.9
    assert calc_avg_score(statements) == 0.9

def test_calc_pass_rate():
    from xapi_tools.analytics.assessment import calc_pass_rate
    statements = [
        # Attempt 1: Started, Completed, Success=True
        {"verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/started"}},
        {
            "verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/completed"},
            "result": {"success": True}
        },
        
        # Attempt 2: Started, Completed, Success=False
        {"verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/started"}},
        {
            "verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/completed"},
            "result": {"success": False}
        },
        
        # Attempt 3: Started (Drop off, so implicitly fail or not counted as success)
        {"verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/started"}},
        
        # Attempt 4: Started, Passed (some systems use Passed verb instead of Completed+Success)
        # But our simple validtor uses 'started' as denominator.
        # Let's assume we look for result.success=True on ANY statement? Or only completed?
        # Usually success stays on completed.
        {"verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/started"}},
        {
            "verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/passed"}, # Different verb
            "result": {"success": True}
        }
    ]
    
    # Denominator: 4 started.
    # Numerator: 2 success=True (one on completed, one on passed)
    # Rate: 2/4 = 0.5
    assert calc_pass_rate(statements) == 0.5

def test_analyze_item_responses():
    from xapi_tools.analytics.assessment import analyze_item_responses
    statements = [
        # Item 1: Correct
        {
            "verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/completed"},
            "object": {"id": "http://example.com/item-1"},
            "result": {"success": True}
        },
        # Item 1: Incorrect
        {
            "verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/completed"},
            "object": {"id": "http://example.com/item-1"},
            "result": {"success": False}
        },
        # Item 2: Correct
        {
            "verb": {"id": "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/completed"},
            "object": {"id": "http://example.com/item-2"},
            "result": {"success": True}
        }
    ]
    
    analysis = analyze_item_responses(statements)
    
    # Item 1: 50%
    assert analysis["http://example.com/item-1"]["total"] == 2
    assert analysis["http://example.com/item-1"]["success"] == 1
    assert analysis["http://example.com/item-1"]["rate"] == 0.5
    
    # Item 2: 100%
    assert analysis["http://example.com/item-2"]["total"] == 1
    assert analysis["http://example.com/item-2"]["success"] == 1
    assert analysis["http://example.com/item-2"]["rate"] == 1.0




