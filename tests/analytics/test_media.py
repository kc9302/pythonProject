import pytest
from xapi_tools.analytics.media import count_media_plays

def test_count_media_plays_simple():
    """
    Test counting 'played' verbs.
    """
    statements = [
        # Play 1
        {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"},
            "object": {"id": "http://example.com/video-1"}
        },
        # Paused (ignored)
        {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/paused"},
            "object": {"id": "http://example.com/video-1"}
        },
        # Play 2 (same video, resume)
        {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"},
            "object": {"id": "http://example.com/video-1"}
        },
        # Play 3 (different video)
        {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"},
            "object": {"id": "http://example.com/video-2"}
        }
    ]
    
    # Total 'played' verbs = 3
    assert count_media_plays(statements) == 3

def test_calc_avg_watch_time():
    from xapi_tools.analytics.media import calc_avg_watch_time
    statements = [
        # Session 1: Played at 10:00, Paused at 10:10 (10 mins = 600s)
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"},
            "object": {"id": "http://example.com/video-1"},
            "context": {"registration": "reg-1"}
        },
        {
            "timestamp": "2024-01-01T10:10:00Z",
            "verb": {"id": "https://w3id.org/xapi/video/verbs/paused"},
            "object": {"id": "http://example.com/video-1"},
            "context": {"registration": "reg-1"}
        },
        
        # Session 2: Played at 11:00, Completed at 11:05 (5 mins = 300s)
        {
            "timestamp": "2024-01-01T11:00:00Z",
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"},
            "object": {"id": "http://example.com/video-2"},
             "context": {"registration": "reg-2"}
        },
        {
            "timestamp": "2024-01-01T11:05:00Z",
            "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
            "object": {"id": "http://example.com/video-2"},
             "context": {"registration": "reg-2"}
        },

        # Session 3: Played but never stopped (Ignore or 0?)
        # Let's assume we ignore open intervals.
        {
            "timestamp": "2024-01-01T12:00:00Z",
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"},
            "object": {"id": "http://example.com/video-3"},
             "context": {"registration": "reg-3"}
        }
    ]
    
    # (600 + 300) / 2 = 450.0
    assert calc_avg_watch_time(statements) == 450.0

def test_identify_drop_off_points():
    from xapi_tools.analytics.media import identify_drop_off_points
    statements = [
        # User 1: Paused at 10.5s
        {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/paused"},
            "result": {
                "extensions": {
                    "https://w3id.org/xapi/video/extensions/time": 10.5
                }
            }
        },
         # User 2: Terminated at 20.0s
        {
            "verb": {"id": "http://adlnet.gov/expapi/verbs/terminated"},
            "result": {
                "extensions": {
                    "https://w3id.org/xapi/video/extensions/time": 20.0
                }
            }
        },
        # User 3: Completed (Not a drop-off, usually)
        # But if we just count all pause/terminate positions, we filter by verb?
        # Usually completed means finished. Drop-off means stopped BEFORE finish.
        {
            "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
             "result": {
                "extensions": {
                    "https://w3id.org/xapi/video/extensions/time": 100.0
                }
            }
        },
        # User 4: Paused at 10.5s (Cluster)
         {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/paused"},
            "result": {
                "extensions": {
                    "https://w3id.org/xapi/video/extensions/time": 10.5
                }
            }
        }
    ]
    
    # Expect counts: 10.5 -> 2, 20.0 -> 1. 100.0 (completed) -> 0 (ignored)
    points = identify_drop_off_points(statements)
    assert points[10.5] == 2
    assert points[20.0] == 1
    assert 100.0 not in points

def test_calc_completion_rate():
    from xapi_tools.analytics.media import calc_completion_rate
    statements = [
        # Session 1: Started and Completed
        {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"},
            "context": {"registration": "reg-1"}
        },
        {
            "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
            "context": {"registration": "reg-1"}
        },
        
        # Session 2: Started only (Drop off)
        {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"},
            "context": {"registration": "reg-2"}
        },
        
        # Session 3: Started multiple times, then completed
        {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"},
            "context": {"registration": "reg-3"}
        },
        {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/paused"},
            "context": {"registration": "reg-3"}
        },
        {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"},
            "context": {"registration": "reg-3"}
        },
        {
            "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
            "context": {"registration": "reg-3"}
        },
        
        # Session 4: Started only
        {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"},
            "context": {"registration": "reg-4"}
        }
    ]
    
    # 4 unique sessions started (reg-1, reg-2, reg-3, reg-4).
    # 2 completed (reg-1, reg-3).
    # Rate: 2/4 = 0.5
    assert calc_completion_rate(statements) == 0.5

def test_analyze_seek_behavior():
    from xapi_tools.analytics.media import analyze_seek_behavior
    statements = [
        # Seek Forward (10 -> 20)
        {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/seeked"},
            "result": {
                "extensions": {
                    "https://w3id.org/xapi/video/extensions/time-from": 10.0,
                    "https://w3id.org/xapi/video/extensions/time-to": 20.0
                }
            }
        },
        # Seek Backward (30 -> 15)
        {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/seeked"},
            "result": {
                "extensions": {
                    "https://w3id.org/xapi/video/extensions/time-from": 30.0,
                    "https://w3id.org/xapi/video/extensions/time-to": 15.0
                }
            }
        },
        # Seek (Missing extensions, should be ignored or counted as unknown?)
        {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/seeked"},
            "result": {}
        },
        # Other verb
         {
            "verb": {"id": "https://w3id.org/xapi/video/verbs/played"}
        }
    ]
    
    analysis = analyze_seek_behavior(statements)
    assert analysis["total_seeks"] == 3
    assert analysis["forward_seeks"] == 1
    assert analysis["backward_seeks"] == 1
    # 3 total, 1 fw, 1 bw -> 1 unknown/neutral




