import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Iterable
from xapi_tools.utils.db import get_db_statements, get_mongo_client
from xapi_tools.utils.pandas_helper import dict_to_rows, rows_to_dict

# ==============================================================================
# ORIGINAL BACKWARD COMPATIBLE FUNCTIONS (Zero Regressions)
# ==============================================================================

VERB_PLAYED = "https://w3id.org/xapi/video/verbs/played"
VERB_PAUSED = "https://w3id.org/xapi/video/verbs/paused"
VERB_SEEKED = "https://w3id.org/xapi/video/verbs/seeked"
VERB_COMPLETED = "http://adlnet.gov/expapi/verbs/completed"
VERB_TERMINATED = "http://adlnet.gov/expapi/verbs/terminated" 

def count_media_plays(statements: Iterable[Dict[str, Any]]) -> int:
    count = 0
    for stmt in statements:
        verb_id = stmt.get("verb", {}).get("id")
        if verb_id == VERB_PLAYED or verb_id == "http://aidtbook.kr/xapi/profiles/media/verbs/played":
            count += 1
    return count

def calc_avg_watch_time(statements: Iterable[Dict[str, Any]]) -> float:
    stmts_list = list(statements)
    
    def get_ts(s):
        ts_str = s.get("timestamp", "")
        if not ts_str: return datetime.min
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except:
            return datetime.min
            
    stmts_list.sort(key=get_ts)
    
    reg_durations = {}
    active_segments = {} 
    
    for stmt in stmts_list:
        reg = stmt.get("context", {}).get("registration")
        if not reg:
            continue
            
        verb_id = stmt.get("verb", {}).get("id")
        ts = get_ts(stmt)
        
        if verb_id == VERB_PLAYED:
            active_segments[reg] = ts
        elif verb_id in [VERB_PAUSED, VERB_COMPLETED, VERB_TERMINATED]:
            start_time = active_segments.get(reg)
            if start_time:
                duration = (ts - start_time).total_seconds()
                if duration >= 0:
                    reg_durations[reg] = reg_durations.get(reg, 0.0) + duration
                del active_segments[reg]

    if not reg_durations:
        return 0.0
        
    return sum(reg_durations.values()) / len(reg_durations)

def identify_drop_off_points(statements: Iterable[Dict[str, Any]]) -> Dict[float, int]:
    drop_offs = {}
    EXT_TIME = "https://w3id.org/xapi/video/extensions/time"
    
    for stmt in statements:
        verb_id = stmt.get("verb", {}).get("id")
        if verb_id not in [VERB_PAUSED, VERB_TERMINATED]:
            continue
            
        result = stmt.get("result", {})
        extensions = result.get("extensions", {})
        time_point = extensions.get(EXT_TIME) or extensions.get("time")
        
        if time_point is not None:
            try:
                t = float(time_point)
                drop_offs[t] = drop_offs.get(t, 0) + 1
            except (ValueError, TypeError):
                continue
                
    return drop_offs

def calc_completion_rate(statements: Iterable[Dict[str, Any]]) -> float:
    started_regs = set()
    completed_regs = set()
    
    for stmt in statements:
        reg = stmt.get("context", {}).get("registration")
        if not reg:
            continue
            
        verb_id = stmt.get("verb", {}).get("id")
        
        if verb_id == VERB_PLAYED or verb_id == "http://aidtbook.kr/xapi/profiles/media/verbs/played":
            started_regs.add(reg)
        elif verb_id == VERB_COMPLETED or verb_id == "http://adlnet.gov/expapi/verbs/completed":
            completed_regs.add(reg)
            
    if not started_regs:
        return 0.0
        
    completed_and_started = completed_regs.intersection(started_regs)
    return len(completed_and_started) / len(started_regs)

def analyze_seek_behavior(statements: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    stats = {
        "total_seeks": 0,
        "forward_seeks": 0,
        "backward_seeks": 0
    }
    
    EXT_FROM = "https://w3id.org/xapi/video/extensions/time-from"
    EXT_TO = "https://w3id.org/xapi/video/extensions/time-to"
    
    for stmt in statements:
        verb_id = stmt.get("verb", {}).get("id")
        if verb_id == VERB_SEEKED:
            stats["total_seeks"] += 1
            
            result = stmt.get("result", {})
            extensions = result.get("extensions", {})
            
            t_from = extensions.get(EXT_FROM) or extensions.get("time-from")
            t_to = extensions.get(EXT_TO) or extensions.get("time-to")
            
            if t_from is not None and t_to is not None:
                try:
                    tf = float(t_from)
                    tt = float(t_to)
                    if tt > tf:
                        stats["forward_seeks"] += 1
                    elif tt < tf:
                        stats["backward_seeks"] += 1
                except (ValueError, TypeError):
                    pass
                    
    return stats

# ==============================================================================
# MEDIA PROFILE BASIC APIS (Notion Spec)
# ==============================================================================

def verb_count(name: str, verb: str) -> int:
    if verb == "interacted":
        statements = get_db_statements(name, "", db_name="lrs")
        count = len(statements)
    else:
        statements = get_db_statements(name, verb, db_name="lrs")
        count = len(statements)
    return count

def watched_media_list(dataset: Dict[str, Dict[int, Any]]) -> Dict[str, Dict[int, Any]]:
    rows = dict_to_rows(dataset)
    results = []
    
    for row in rows:
        stmt = row.get("statement", row)
        obj = stmt.get("object", {})
        definition = obj.get("definition", {})
        
        media_name = None
        names = definition.get("name", {})
        if isinstance(names, dict):
            media_name = names.get("ko-KR", names.get("en-US", next(iter(names.values())) if names else None))
        else:
            media_name = names
            
        if not media_name:
            media_name = obj.get("id", "Unknown Media")
            
        obj_type = definition.get("type", "")
        media_type = "영상"
        if "audio" in obj_type.lower():
            media_type = "오디오"
            
        results.append({
            "media_content": media_name,
            "media_type": media_type
        })
        
    return rows_to_dict(results)

def watched_media_count(name: str, verb: str) -> Dict[str, int]:
    statements = get_db_statements(name, verb, db_name="lrs")
    
    counts = {"영상": 0, "오디오": 0}
    for stmt in statements:
        actual_stmt = stmt.get("statement", stmt)
        obj_type = actual_stmt.get("object", {}).get("definition", {}).get("type", "")
        
        if "audio" in obj_type.lower():
            counts["오디오"] += 1
        else:
            counts["영상"] += 1
            
    return counts

def initialized_info(dataset: Dict[str, Dict[int, Any]]) -> Dict[str, Dict[int, Any]]:
    rows = dict_to_rows(dataset)
    results = []
    
    EXT_PREFIX = "http://aidtbook.kr/xapi/profiles/media/objects/extensions/"
    ext_keys = [
        "media-session-id", "length", "frame-rate", "track", "tag", 
        "completion-threshold", "user-agent", "screen-size", 
        "cc-subtitle-enabled", "cc-subtitle-lang", "quality", 
        "speed", "volume", "full-screen", "video-playback-size"
    ]
    
    for row in rows:
        stmt = row.get("statement", row)
        context = stmt.get("context") or {}
        extensions = context.get("extensions") or {}
        
        obj_def = stmt.get("object", {}).get("definition", {})
        obj_extensions = obj_def.get("extensions", {})
        
        info = {}
        for key in ext_keys:
            val = extensions.get(f"{EXT_PREFIX}{key}") or extensions.get(key)
            if val is None:
                val = obj_extensions.get(f"{EXT_PREFIX}{key}") or obj_extensions.get(key)
            info[key] = val
        results.append(info)
        
    return rows_to_dict(results)

def now_play_time(dataset: Dict[str, Dict[int, Any]]) -> Dict[str, Dict[int, Any]]:
    rows = dict_to_rows(dataset)
    results = []
    TIME_EXT = "https://w3id.org/xapi/video/extensions/time"
    
    for row in rows:
        stmt = row.get("statement", row)
        obj = stmt.get("object", {})
        media_name = obj.get("definition", {}).get("name", {}).get("ko-KR", obj.get("id"))
        
        result = stmt.get("result", {})
        extensions = result.get("extensions", {})
        start_time = extensions.get(TIME_EXT) or extensions.get("time") or 0.001
        
        results.append({
            "media_name": media_name,
            "start_time": start_time
        })
        
    return rows_to_dict(results)

def play_pause_time_interval(dataset: Dict[str, Dict[int, Any]]) -> Dict[str, Dict[int, Any]]:
    rows = dict_to_rows(dataset)
    results = []
    
    for row in rows:
        stmt = row.get("statement", row)
        obj = stmt.get("object", {})
        media_name = obj.get("definition", {}).get("name", {}).get("ko-KR", obj.get("id"))
        
        result = stmt.get("result", {})
        extensions = result.get("extensions", {})
        progress = result.get("score", {}).get("scaled") or extensions.get("progress") or 0.0
        
        segments = extensions.get("http://aidtbook.kr/xapi/profiles/media/extensions/played-segments") or \
                   extensions.get("played-segments") or []
                   
        results.append({
            "media_name": media_name,
            "start_time": extensions.get("time") or 0.0,
            "progress": progress,
            "played_segments": segments
        })
        
    return rows_to_dict(results)

def seeked_time_interval(dataset: Dict[str, Dict[int, Any]]) -> Dict[str, Dict[int, Any]]:
    rows = dict_to_rows(dataset)
    results = []
    EXT_FROM = "https://w3id.org/xapi/video/extensions/time-from"
    EXT_TO = "https://w3id.org/xapi/video/extensions/time-to"
    
    for row in rows:
        stmt = row.get("statement", row)
        obj = stmt.get("object", {})
        media_name = obj.get("definition", {}).get("name", {}).get("ko-KR", obj.get("id"))
        
        result = stmt.get("result", {})
        extensions = result.get("extensions", {})
        
        time_from = extensions.get(EXT_FROM) or extensions.get("time-from") or 0.0
        time_to = extensions.get(EXT_TO) or extensions.get("time-to") or 0.0
        
        results.append({
            "media_name": media_name,
            "time_from": time_from,
            "time_to": time_to
        })
        
    return rows_to_dict(results)

def completed_time_interval(dataset: Dict[str, Dict[int, Any]]) -> Dict[str, Dict[int, Any]]:
    rows = dict_to_rows(dataset)
    results = []
    
    for row in rows:
        stmt = row.get("statement", row)
        obj = stmt.get("object", {})
        media_name = obj.get("definition", {}).get("name", {}).get("ko-KR", obj.get("id"))
        
        result = stmt.get("result", {})
        extensions = result.get("extensions", {})
        
        duration_raw = result.get("duration") or "0"
        from xapi_tools.adapter.mapping_engine import parse_iso8601_duration
        seconds = parse_iso8601_duration(str(duration_raw))
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        time_str = f"{hours}:{minutes:02d}:{secs:02d}"
        
        results.append({
            "미디어 이름": media_name,
            "미디어 현재 위치": time_str,
            "완료율": "100%",
            "played_segments": extensions.get("played-segments") or []
        })
        
    return rows_to_dict(results)

def terminated_time_interval(dataset: Dict[str, Dict[int, Any]]) -> Dict[str, Dict[int, Any]]:
    return completed_time_interval(dataset)

def interacted_time_interval(dataset: Dict[str, Dict[int, Any]]) -> Dict[str, Dict[int, Any]]:
    rows = dict_to_rows(dataset)
    results = []
    
    for row in rows:
        stmt = row.get("statement", row)
        obj = stmt.get("object", {})
        media_name = obj.get("definition", {}).get("name", {}).get("ko-KR", obj.get("id"))
        
        result = stmt.get("result", {})
        extensions = result.get("extensions", {})
        
        interact_content = extensions.get("interact-content") or []
        
        results.append({
            "미디어 이름": media_name,
            "미디어 위치": extensions.get("time") or "0:00:00",
            "interact_content": interact_content
        })
        
    return rows_to_dict(results)

def media_heatmap(activity_id: str) -> List[Dict[str, Any]]:
    """
    특정 미디어 콘텐츠(activity_id)에 대한 다수 유저들의 pause 및 seek 구간을 5초 단위 윈도우로 집계합니다.
    7.4억 건 대형 LRS 컬렉션에서 부하를 통제하기 위해 search.activities 인덱스를 활용합니다.
    """
    client = get_mongo_client()
    db = client["lrs"]
    coll = db["statements"]
    
    query = {
        "search.activities": activity_id,
        "statement.verb.id": {
            "$in": [
                "http://lecognizer.com/xapi/profiles/media/1.0/verbs/paused",
                "http://lecognizer.com/xapi/profiles/media/1.0/verbs/seeked"
            ]
        }
    }
    
    # Capped at 5000 records to prevent extreme load
    cursor = coll.find(query).limit(5000)
    
    buckets = {}
    
    for doc in cursor:
        stmt = doc.get("statement", {})
        verb_id = stmt.get("verb", {}).get("id", "")
        result = stmt.get("result", {}) or {}
        extensions = result.get("extensions", {}) or {}
        
        time_val = extensions.get("http://lecognizer.com/xapi/profiles/media/1.0/extensions/result/time")
        if time_val is None:
            time_val = extensions.get("time")
            
        if time_val is not None:
            try:
                t = float(time_val)
                if t < 0:
                    continue
                bucket_start = int(t // 5) * 5
                
                if bucket_start not in buckets:
                    buckets[bucket_start] = {"paused_count": 0, "seeked_count": 0}
                    
                if "paused" in verb_id:
                    buckets[bucket_start]["paused_count"] += 1
                elif "seeked" in verb_id:
                    buckets[bucket_start]["seeked_count"] += 1
            except (ValueError, TypeError):
                continue
                
    client.close()
    
    sorted_buckets = []
    for b_start in sorted(buckets.keys()):
        sorted_buckets.append({
            "bucket_start": b_start,
            "bucket_end": b_start + 5,
            "pause_count": buckets[b_start]["paused_count"],
            "seek_count": buckets[b_start]["seeked_count"]
        })
        
    return sorted_buckets

def detect_frustration(statements: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    미디어 재생 중 사용자 좌절(Frustration) 패턴을 탐지합니다.
    - 1분 이내 4회 이상의 seek/pause 발생
    - 극단적인 배속 (1.8x 이상 혹은 0.7x 이하)
    """
    stmts_list = list(statements)
    
    def get_ts(s):
        ts_str = s.get("timestamp", "")
        if not ts_str: return datetime.min
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except:
            return datetime.min
            
    stmts_list.sort(key=get_ts)
    
    reg_events = {} # reg -> list of timestamps
    frustration_results = {}
    
    EXT_SPEED = "https://w3id.org/xapi/video/extensions/speed"
    
    for stmt in stmts_list:
        reg = stmt.get("context", {}).get("registration")
        if not reg:
            continue
            
        ts = get_ts(stmt)
        verb_id = stmt.get("verb", {}).get("id", "")
        
        # 1. 배속 체크
        extensions = stmt.get("context", {}).get("extensions", {})
        speed = extensions.get(EXT_SPEED) or extensions.get("speed")
        if speed is not None:
            try:
                s_val = float(speed)
                if s_val >= 1.8 or s_val <= 0.7:
                    if reg not in frustration_results:
                        frustration_results[reg] = {"frustration_score": 0, "reasons": []}
                    if "Extreme play speed" not in frustration_results[reg]["reasons"]:
                        frustration_results[reg]["frustration_score"] += 30
                        frustration_results[reg]["reasons"].append("Extreme play speed")
            except (ValueError, TypeError):
                pass

        # 2. 빈도 체크 (seeked, paused)
        if any(v in verb_id for v in ["seeked", "paused"]):
            if reg not in reg_events:
                reg_events[reg] = []
            reg_events[reg].append(ts)
            
            # 최근 60초 이내의 이벤트만 필터링
            recent_events = [t for t in reg_events[reg] if (ts - t).total_seconds() <= 60]
            reg_events[reg] = recent_events
            
            if len(recent_events) >= 4:
                if reg not in frustration_results:
                    frustration_results[reg] = {"frustration_score": 0, "reasons": []}
                if "High frequency of actions" not in frustration_results[reg]["reasons"]:
                    frustration_results[reg]["frustration_score"] += 50
                    frustration_results[reg]["reasons"].append("High frequency of actions")
                    
    return frustration_results
