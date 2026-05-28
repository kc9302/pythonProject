from datetime import datetime
from typing import Dict, Any, List, Optional, Iterable
from xapi_tools.utils.db import get_db_statements
from xapi_tools.utils.pandas_helper import dict_to_rows, rows_to_dict

# ==============================================================================
# ORIGINAL BACKWARD COMPATIBLE FUNCTIONS (Zero Regressions)
# ==============================================================================

SESSION_ID_IRI = "http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id"
VERB_INITIALIZED = "http://lecognizer.com/xapi/profiles/session/1.0/verbs/initialized"
VERB_TERMINATED = "http://lecognizer.com/xapi/profiles/session/1.0/verbs/terminated"

def count_total_sessions(statements: Iterable[Dict[str, Any]]) -> int:
    session_ids = set()
    for stmt in statements:
        context = stmt.get("context", {})
        extensions = context.get("extensions", {})
        sid = extensions.get(SESSION_ID_IRI)
        if sid:
            session_ids.add(sid)
    return len(session_ids)

def calc_avg_session_duration(statements: Iterable[Dict[str, Any]]) -> float:
    sessions = {}
    for stmt in statements:
        context = stmt.get("context", {})
        extensions = context.get("extensions", {})
        sid = extensions.get(SESSION_ID_IRI)
        
        if not sid:
            continue
            
        verb_id = stmt.get("verb", {}).get("id")
        timestamp_str = stmt.get("timestamp")
        
        if not timestamp_str or not verb_id:
            continue
            
        try:
            timestamp_str = timestamp_str.replace("Z", "+00:00")
            ts = datetime.fromisoformat(timestamp_str)
        except ValueError:
            continue
            
        if sid not in sessions:
            sessions[sid] = {"start": None, "end": None}
            
        if verb_id == VERB_INITIALIZED:
             if sessions[sid]["start"] is None or ts < sessions[sid]["start"]:
                sessions[sid]["start"] = ts
        elif verb_id == VERB_TERMINATED:
              if sessions[sid]["end"] is None or ts > sessions[sid]["end"]:
                sessions[sid]["end"] = ts
                
    durations = []
    for sid, times in sessions.items():
        if times["start"] and times["end"]:
            duration = (times["end"] - times["start"]).total_seconds()
            if duration >= 0:
                durations.append(duration)
                
    if not durations:
        return 0.0
    return sum(durations) / len(durations)

def count_active_days(statements: Iterable[Dict[str, Any]]) -> int:
    active_days = set()
    for stmt in statements:
        context = stmt.get("context", {})
        extensions = context.get("extensions", {})
        sid = extensions.get(SESSION_ID_IRI)
        if not sid:
            continue
        timestamp_str = stmt.get("timestamp")
        if not timestamp_str:
            continue
        try:
            timestamp_str = timestamp_str.replace("Z", "+00:00")
            ts = datetime.fromisoformat(timestamp_str)
            day = ts.date().isoformat()
            active_days.add(day)
        except ValueError:
            continue
    return len(active_days)

def analyze_login_times(statements: Iterable[Dict[str, Any]]) -> Dict[int, int]:
    hours = {}
    for stmt in statements:
        verb_id = stmt.get("verb", {}).get("id")
        if verb_id != VERB_INITIALIZED:
            continue
        timestamp_str = stmt.get("timestamp")
        if not timestamp_str:
            continue
        try:
             timestamp_str = timestamp_str.replace("Z", "+00:00")
             ts = datetime.fromisoformat(timestamp_str)
             h = ts.hour
             hours[h] = hours.get(h, 0) + 1
        except ValueError:
            continue
    return hours

def get_platform_usage(statements: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    session_platforms = {}
    for stmt in statements:
        context = stmt.get("context", {})
        extensions = context.get("extensions", {})
        sid = extensions.get(SESSION_ID_IRI)
        if not sid:
            continue
        if sid not in session_platforms:
            session_platforms[sid] = "Unknown"
        platform = context.get("platform")
        if platform:
            session_platforms[sid] = platform
            
    usage = {}
    for p in session_platforms.values():
        usage[p] = usage.get(p, 0) + 1
    return usage

# ==============================================================================
# SESSION PROFILE BASIC APIS (Notion Spec)
# ==============================================================================

def verb_count(name: str, verb: str) -> int:
    statements = get_db_statements(name, verb, db_name="lrs")
    return len(statements)

def time_list(dataset: Dict[str, Dict[int, Any]]) -> Dict[str, Dict[int, Any]]:
    rows = dict_to_rows(dataset)
    results = []
    
    for row in rows:
        stmt = row.get("statement", row)
        
        raw_ts = stmt.get("timestamp")
        timestamp = raw_ts
        if raw_ts and not isinstance(raw_ts, datetime):
            try:
                timestamp_str = str(raw_ts).replace("Z", "+00:00")
                timestamp = datetime.fromisoformat(timestamp_str)
            except Exception:
                timestamp = raw_ts
                
        obj = stmt.get("object", {})
        def_name = obj.get("definition", {}).get("name", {})
        name = "Unknown Activity"
        if isinstance(def_name, dict):
            name = def_name.get("ko-KR", def_name.get("en-US", next(iter(def_name.values())) if def_name else obj.get("id", name)))
        else:
            name = def_name or obj.get("id", name)
            
        verb_id = stmt.get("verb", {}).get("id", "")
        verb_name = verb_id.split("/")[-1] if "/" in verb_id else "unknown"
        
        results.append({
            "timestamp": timestamp,
            "name": name,
            "verbs": verb_name
        })
        
    def get_sort_key(r):
        ts = r["timestamp"]
        if isinstance(ts, datetime):
            return ts
        return datetime.min
    results.sort(key=get_sort_key)
    
    return rows_to_dict(results)
