import pytest
from xapi_tools.analytics.session import count_total_sessions

def test_count_total_sessions_simple():
    """
    Test counting unique session IDs from statements.
    """
    statements = [
        {
            "context": {
                "extensions": {
                    "http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "session-1"
                }
            }
        },
        {
            "context": {
                "extensions": {
                    "http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "session-1" # Duplicate ID
                }
            }
        },
        {
            "context": {
                "extensions": {
                    "http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "session-2"
                }
            }
        },
        {
            "context": {
                # No extensions
            }
        },
        {
            "context": {
                "extensions": {
                    "other-extension": "value"
                }
            }
        }
    ]
    
    assert count_total_sessions(statements) == 2

def test_calc_avg_session_duration():
    from xapi_tools.analytics.session import calc_avg_session_duration
    statements = [
        # Session 1: 1 hour (3600 sec)
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/session/1.0/verbs/initialized"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}}
        },
        {
            "timestamp": "2024-01-01T11:00:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/session/1.0/verbs/terminated"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}}
        },
        # Session 2: 30 mins (1800 sec)
        {
            "timestamp": "2024-01-02T10:00:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/session/1.0/verbs/initialized"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s2"}}
        },
        {
            "timestamp": "2024-01-02T10:30:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/session/1.0/verbs/terminated"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s2"}}
        },
        # Incomplete Session (Should be ignored)
        {
            "timestamp": "2024-01-03T10:00:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/session/1.0/verbs/initialized"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s3"}}
        }
    ]
    
    # Avg = (3600 + 1800) / 2 = 2700 seconds
    assert calc_avg_session_duration(statements) == 2700.0

def test_count_active_days():
    from xapi_tools.analytics.session import count_active_days
    statements = [
        # Day 1: 2024-01-01
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}}
        },
        # Day 1 again
        {
            "timestamp": "2024-01-01T23:59:59Z",
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s2"}}
        },
        # Day 2: 2024-01-02
        {
            "timestamp": "2024-01-02T00:00:01Z",
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s3"}}
        },
        # No session ID (ignored)
        {
            "timestamp": "2024-01-03T00:00:00Z",
        }
    ]
    
    assert count_active_days(statements) == 2

def test_analyze_login_times():
    from xapi_tools.analytics.session import analyze_login_times
    statements = [
        # 10:00 UTC
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/session/1.0/verbs/initialized"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}}
        },
        # 10:30 UTC
        {
            "timestamp": "2024-01-02T10:30:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/session/1.0/verbs/initialized"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s2"}}
        },
        # 11:00 UTC
        {
            "timestamp": "2024-01-02T11:00:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/session/1.0/verbs/initialized"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s3"}}
        },
        # Not initialized (ignored)
        {
            "timestamp": "2024-01-02T12:00:00Z",
            "verb": {"id": "http://lecognizer.com/xapi/profiles/session/1.0/verbs/terminated"},
            "context": {"extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s3"}}
        }
    ]
    
    # 10h: 2, 11h: 1
    distribution = analyze_login_times(statements)
    assert distribution[10] == 2
    assert distribution[11] == 1
    assert distribution.get(12, 0) == 0

def test_get_platform_usage():
    from xapi_tools.analytics.session import get_platform_usage
    statements = [
        # Session 1: Windows
        {
            "context": {
                "platform": "Windows",
                "extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}
            }
        },
        # Session 1 again (should not double count)
        {
            "context": {
                "platform": "Windows",
                "extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s1"}
            }
        },
        # Session 2: Android
        {
            "context": {
                "platform": "Android",
                "extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s2"}
            }
        },
        # Session 3: No platform
        {
            "context": {
                "extensions": {"http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s3"}
            }
        }
    ]
    
    usage = get_platform_usage(statements)
    assert usage["Windows"] == 1
    assert usage["Android"] == 1
    assert usage["Unknown"] == 1




