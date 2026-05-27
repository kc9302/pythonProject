import pytest
from datetime import datetime, timedelta
from xapi_tools.analytics.media import detect_frustration

def test_detect_frustration_by_frequency():
    """
    Test detecting frustration due to frequent seek/pause actions (>= 4 actions in 60s).
    """
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    
    # Frustrating sequence: 4 actions in 30 seconds
    statements = [
        {
            "timestamp": (base_time + timedelta(seconds=0)).isoformat() + "Z",
            "verb": {"id": "https://w3id.org/xapi/video/verbs/seeked"},
            "context": {"registration": "reg-1"}
        },
        {
            "timestamp": (base_time + timedelta(seconds=10)).isoformat() + "Z",
            "verb": {"id": "https://w3id.org/xapi/video/verbs/paused"},
            "context": {"registration": "reg-1"}
        },
        {
            "timestamp": (base_time + timedelta(seconds=20)).isoformat() + "Z",
            "verb": {"id": "https://w3id.org/xapi/video/verbs/seeked"},
            "context": {"registration": "reg-1"}
        },
        {
            "timestamp": (base_time + timedelta(seconds=30)).isoformat() + "Z",
            "verb": {"id": "https://w3id.org/xapi/video/verbs/paused"},
            "context": {"registration": "reg-1"}
        }
    ]
    
    # Should detect frustration for reg-1
    result = detect_frustration(statements)
    assert "reg-1" in result
    assert result["reg-1"]["frustration_score"] > 0
    assert "High frequency of actions" in result["reg-1"]["reasons"]

def test_detect_frustration_by_speed():
    """
    Test detecting frustration due to extreme play-speed (e.g., 2.0x).
    """
    statements = [
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"},
            "context": {
                "registration": "reg-2",
                "extensions": {
                    "https://w3id.org/xapi/video/extensions/speed": 2.0
                }
            }
        }
    ]
    
    # Should detect frustration for reg-2
    result = detect_frustration(statements)
    assert "reg-2" in result
    assert "Extreme play speed" in result["reg-2"]["reasons"]

def test_no_frustration_for_normal_usage():
    """
    Test that normal usage doesn't trigger frustration.
    """
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    
    # Normal sequence: 2 actions in 10 minutes
    statements = [
        {
            "timestamp": (base_time + timedelta(seconds=0)).isoformat() + "Z",
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"},
            "context": {"registration": "reg-3"}
        },
        {
            "timestamp": (base_time + timedelta(minutes=10)).isoformat() + "Z",
            "verb": {"id": "https://w3id.org/xapi/video/verbs/paused"},
            "context": {"registration": "reg-3"}
        }
    ]
    
    result = detect_frustration(statements)
    assert "reg-3" not in result
