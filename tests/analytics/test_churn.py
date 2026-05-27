import pytest
from datetime import datetime, timedelta
from xapi_tools.analytics.navigation import predict_churn

def test_predict_churn_by_idle_time():
    """
    Test predicting churn due to long idle time (> 30s) after navigation.
    """
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    
    # Sequence: Navigated -> 40s gap -> Next action
    statements = [
        {
            "timestamp": (base_time + timedelta(seconds=0)).isoformat() + "Z",
            "verb": {"id": "https://w3id.org/xapi/video/verbs/navigated"},
            "context": {"extensions": {"session-id": "sess-1"}}
        },
        {
            "timestamp": (base_time + timedelta(seconds=40)).isoformat() + "Z",
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"},
            "context": {"extensions": {"session-id": "sess-1"}}
        }
    ]
    
    # Should detect churn risk for sess-1
    result = predict_churn(statements)
    assert "sess-1" in result
    assert result["sess-1"]["churn_probability"] > 0.5
    assert "Idle state detected" in result["sess-1"]["reasons"]

def test_predict_churn_by_meaningless_navigation():
    """
    Test predicting churn due to rapid meaningless navigation (>= 3 navs in 10s).
    """
    base_time = datetime(2024, 1, 1, 11, 0, 0)
    
    # Sequence: 3 navigations in 6 seconds
    statements = [
        {
            "timestamp": (base_time + timedelta(seconds=0)).isoformat() + "Z",
            "verb": {"id": "navigated"},
            "context": {"extensions": {"session-id": "sess-2"}}
        },
        {
            "timestamp": (base_time + timedelta(seconds=3)).isoformat() + "Z",
            "verb": {"id": "navigated"},
            "context": {"extensions": {"session-id": "sess-2"}}
        },
        {
            "timestamp": (base_time + timedelta(seconds=6)).isoformat() + "Z",
            "verb": {"id": "navigated"},
            "context": {"extensions": {"session-id": "sess-2"}}
        }
    ]
    
    # Should detect churn risk for sess-2
    result = predict_churn(statements)
    assert "sess-2" in result
    assert "Meaningless navigation" in result["sess-2"]["reasons"]

def test_no_churn_for_normal_flow():
    """
    Test that normal flow doesn't trigger churn.
    """
    base_time = datetime(2024, 1, 1, 12, 0, 0)
    
    # Sequence: Nav -> 10s -> Action
    statements = [
        {
            "timestamp": (base_time + timedelta(seconds=0)).isoformat() + "Z",
            "verb": {"id": "navigated"},
            "context": {"extensions": {"session-id": "sess-3"}}
        },
        {
            "timestamp": (base_time + timedelta(seconds=10)).isoformat() + "Z",
            "verb": {"id": "played"},
            "context": {"extensions": {"session-id": "sess-3"}}
        }
    ]
    
    result = predict_churn(statements)
    assert "sess-3" not in result
