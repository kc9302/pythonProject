import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Iterable
from xapi_tools.utils.db import get_db_statements, get_mongo_client
from xapi_tools.utils.pandas_helper import dict_to_rows, rows_to_dict
from xapi_tools.analytics.utils import ensure_data

logger = logging.getLogger("xapi_tools.analytics.media")

# ==============================================================================
# UTILITIES
# ==============================================================================

def _get_ts(s):
    # Support both 'timestamp' (string/datetime) and nested raw structure
    raw_stmt = s.get("statement", s)
    ts = raw_stmt.get("timestamp", s.get("timestamp"))
    if not ts: return datetime.min
    if isinstance(ts, datetime): return ts
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except:
        return datetime.min

# ==============================================================================
# MEDIA PROFILE BASIC APIS
# ==============================================================================

def verb_count(name: str, verb: str = "played") -> int:
    statements = get_db_statements(name, verb, db_name="lrs")
    return len(statements)

@ensure_data
def watched_media_list(dataset: Dict[str, Dict[int, Any]]) -> Dict[str, Dict[int, Any]]:
    rows = dict_to_rows(dataset)
    media_content = {}
    media_type = {}
    for idx, row in enumerate(rows):
        stmt = row.get("statement", row)
        obj = stmt.get("object", {})
        names = obj.get("definition", {}).get("name", {})
        name = "Unknown Media"
        if isinstance(names, dict):
            name = names.get("ko-KR", names.get("en-US", next(iter(names.values())) if names else obj.get("id", name)))
        else:
            name = names or obj.get("id", name)
        obj_type_raw = obj.get("definition", {}).get("type", "")
        m_type = "video" if "video" in obj_type_raw.lower() or "media" in obj_type_raw.lower() else "audio"
        media_content[idx] = name
        media_type[idx] = m_type
    return {"media_content": media_content, "media_type": media_type}

def watched_media_count(name: str, verb: str = "played") -> Dict[str, int]:
    statements = get_db_statements(name, verb, db_name="lrs")
    video_count = 0
    audio_count = 0
    for doc in statements:
        stmt = doc.get("statement", doc)
        obj_type = stmt.get("object", {}).get("definition", {}).get("type", "")
        if "audio" in obj_type.lower(): audio_count += 1
        else: video_count += 1
    return {"영상": video_count, "오디오": audio_count}

@ensure_data
def initialized_info(dataset: Dict[str, Dict[int, Any]]) -> Any:
    rows = dict_to_rows(dataset)
    results = []
    for row in rows:
        stmt = row.get("statement", row)
        verb_id = stmt.get("verb", {}).get("id", "")
        if "initialized" in verb_id.lower():
            extensions = stmt.get("context", {}).get("extensions", {})
            clean_ext = {}
            for k, v in extensions.items():
                clean_ext[k.split('/')[-1]] = v
            results.append(clean_ext)
            
    if not results:
        return {"result": "데이터 없음"}
        
    return rows_to_dict(results)

@ensure_data
def now_play_time(dataset: Dict[str, Dict[int, Any]]) -> Any:
    rows = dict_to_rows(dataset)
    play_times = {}
    for row in rows:
        stmt = row.get("statement", row)
        if "played" in stmt.get("verb", {}).get("id", "").lower():
            obj_id = stmt.get("object", {}).get("id", "unknown")
            time_val = stmt.get("context", {}).get("extensions", {}).get("https://w3id.org/xapi/video/extensions/time")
            if time_val is not None: play_times[obj_id] = str(time_val)
            
    if not play_times:
        return {"result": "데이터 없음"}
    return play_times

@ensure_data
def play_pause_time_interval(dataset: Dict[str, Dict[int, Any]]) -> Any:
    rows = dict_to_rows(dataset)
    segments = []
    total_played = 0
    for row in rows:
        stmt = row.get("statement", row)
        verb = stmt.get("verb", {}).get("id", "").lower()
        if "played" in verb or "paused" in verb:
            time_val = resolve_video_time(stmt)
            segments.append({"action": "played" if "played" in verb else "paused", "time": time_val})
            if "played" in verb: total_played += 1
            
    if not segments:
        return {"result": "데이터 없음"}
            
    return {"segments": segments, "total_played_count": total_played}

def resolve_video_time(stmt):
    ext = stmt.get("context", {}).get("extensions", {})
    for k, v in ext.items():
        if "time" in k.lower(): return v
    return 0

@ensure_data
def seeked_time_interval(dataset: Dict[str, Dict[int, Any]]) -> Any:
    rows = dict_to_rows(dataset)
    results = []
    for row in rows:
        stmt = row.get("statement", row)
        if "seeked" in stmt.get("verb", {}).get("id", "").lower():
            ext = stmt.get("context", {}).get("extensions", {})
            results.append({
                "from": ext.get("https://w3id.org/xapi/video/extensions/time-from"),
                "to": ext.get("https://w3id.org/xapi/video/extensions/time-to"),
                "timestamp": stmt.get("timestamp")
            })
            
    if not results:
        return {"result": "데이터 없음"}
    return results

@ensure_data
def completed_time_interval(dataset: Dict[str, Dict[int, Any]]) -> Any:
    rows = dict_to_rows(dataset)
    for row in rows:
        stmt = row.get("statement", row)
        if "completed" in stmt.get("verb", {}).get("id", "").lower():
            return {"completed": True, "timestamp": stmt.get("timestamp")}
            
    return {"result": "데이터 없음"}

@ensure_data
def terminated_time_interval(dataset: Dict[str, Dict[int, Any]]) -> Any:
    rows = dict_to_rows(dataset)
    for row in rows:
        stmt = row.get("statement", row)
        if "terminated" in stmt.get("verb", {}).get("id", "").lower():
            return {"terminated": True, "timestamp": stmt.get("timestamp")}
            
    return {"result": "데이터 없음"}

@ensure_data
def interacted_time_interval(dataset: Dict[str, Dict[int, Any]]) -> Any:
    rows = dict_to_rows(dataset)
    results = []
    for row in rows:
        stmt = row.get("statement", row)
        if "interacted" in stmt.get("verb", {}).get("id", "").lower():
            results.append({"type": "interacted", "timestamp": stmt.get("timestamp")})
            
    if not results:
        return {"result": "데이터 없음"}
    return results

def media_heatmap(activity_id: str) -> List[Dict[str, Any]]:
    """
    미디어 히트맵 분석: 특정 미디어의 구간별 중단/탐색 빈도를 분석합니다.
    [최적화] indexed 필드 'search.activities'를 사용하여 Full Scan 방지.
    """
    client = get_mongo_client()
    db = client["lrs"]
    coll = db["statements"]

    # search.activities는 인덱스가 걸려있는 필드임 (743M records safe)
    query = {
        "search.activities": activity_id,
        "statement.verb.id": {
            "$in": [
                "http://aidtbook.kr/xapi/profiles/media/verbs/paused",
                "http://aidtbook.kr/xapi/profiles/media/verbs/seeked",
                "http://lecognizer.com/xapi/profiles/media/1.0/verbs/paused",
                "http://lecognizer.com/xapi/profiles/media/1.0/verbs/seeked"
            ]
        }
    }

    cursor = coll.find(query).limit(5000)
    buckets = {}
    for doc in cursor:
        stmt = doc.get("statement", {})
        verb_id = stmt.get("verb", {}).get("id", "")
        result = stmt.get("result", {}) or {}
        extensions = result.get("extensions", {}) or {}
        time_val = extensions.get("http://lecognizer.com/xapi/profiles/media/1.0/extensions/result/time")
        if time_val is None: time_val = extensions.get("time")
        if time_val is not None:
            try:
                t = float(time_val)
                if t < 0: continue
                bucket_start = int(t // 5) * 5
                if bucket_start not in buckets: buckets[bucket_start] = {"paused_count": 0, "seeked_count": 0}
                if "paused" in verb_id: buckets[bucket_start]["paused_count"] += 1
                elif "seeked" in verb_id: buckets[bucket_start]["seeked_count"] += 1
            except: continue
    sorted_buckets = []
    for b_start in sorted(buckets.keys()):
        sorted_buckets.append({
            "bucket_start": b_start, "bucket_end": b_start + 5,
            "pause_count": buckets[b_start]["paused_count"], "seek_count": buckets[b_start]["seeked_count"]
        })
    
    if not sorted_buckets:
        return {"result": "데이터 없음"}
        
    return sorted_buckets

# ==============================================================================
# ADVANCED ANALYTICS (Relaxed for Real-world Production Data)
# ==============================================================================

def detect_frustration(statements: Iterable[Dict[str, Any]]) -> Any:
    """
    미디어 재생 중 사용자 좌절(Frustration) 패턴을 탐지합니다.
    [기준 완화]
    - 잦은 일시정지/탐색: 2분 이내 2회 이상 발생 (주의)
    - 미세 배속 변경: 1.2배속 이상 감지 시 기록
    """
    stmts_list = list(statements)
    if not stmts_list: 
        return {"result": "데이터 없음"}
    
    stmts_list.sort(key=_get_ts)
    frustration_results = {} 
    reg_events = {} 
    
    # Analyze and group
    for s in stmts_list:
        raw_stmt = s.get("statement", s)
        context = raw_stmt.get("context", {})
        reg_id = context.get("registration") or s.get("user_id") or raw_stmt.get("actor", {}).get("account", {}).get("name", "unknown")
             
        if reg_id not in frustration_results:
            frustration_results[reg_id] = {"frustration_score": 0, "reasons": [], "status": "Safe🟢"}
            reg_events[reg_id] = []
            
        ts = _get_ts(s)
        verb_category = s.get("verb_category")
        verb_id = raw_stmt.get("verb", {}).get("id", "").lower()
        
        # 1. 배속 체크 (1.2x 이상만 되어도 주의 단계로 기록)
        extensions = context.get("extensions", {})
        speed = 1.0
        for k, v in extensions.items():
            if any(term in k.lower() for term in ["speed", "play-speed"]):
                try: speed = float(v)
                except: pass
                
        if speed > 1.1:
            if "Increased play speed" not in frustration_results[reg_id]["reasons"]:
                frustration_results[reg_id]["frustration_score"] += 20
                frustration_results[reg_id]["reasons"].append(f"Increased play speed ({speed}x)")
        
        # 2. 빈도 체크 (2분 이내 2회 이상)
        is_frustrating_verb = (verb_category in ["paused", "seeked"]) or any(v in verb_id for v in ["paused", "seeked"])
        if is_frustrating_verb:
            reg_events[reg_id].append(ts)
            recent_events = [t for t in reg_events[reg_id] if (ts - t).total_seconds() <= 120]
            if len(recent_events) >= 2:
                if "Frequent seek/pause actions" not in frustration_results[reg_id]["reasons"]:
                    frustration_results[reg_id]["frustration_score"] += 40
                    frustration_results[reg_id]["reasons"].append("Frequent seek/pause actions")
                    
    # Status Mapping
    for rid, res in frustration_results.items():
        score = res["frustration_score"]
        if score >= 80: res["status"] = "Critical🔴"
        elif score >= 50: res["status"] = "Warning🟠"
        elif score >= 20: res["status"] = "Caution🟡"
        else: res["status"] = "Safe🟢"
        
    return frustration_results
