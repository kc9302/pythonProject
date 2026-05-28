from datetime import datetime
from typing import Dict, Any, List, Optional, Iterable
from xapi_tools.utils.db import get_db_statements
from xapi_tools.utils.pandas_helper import dict_to_rows, rows_to_dict
from xapi_tools.analytics.utils import ensure_data

# ==============================================================================
# NAVIGATION PROFILE BASIC APIS
# ==============================================================================

def verb_count(name: str) -> int:
    """
    유저의 navigation verb의 수를 구합니다.
    Example: verb_count(name="김레나")
    """
    # navigated verb
    statements = get_db_statements(name, "navigated", db_name="lrs")
    return len(statements)

@ensure_data
def navigation_list(dataset: Dict[str, Dict[int, Any]]) -> Any:
    """
    전체기간에서 유저의 navigation 목록을 시간순으로 일자별로 구합니다. (시간차 포함)
    """
    rows = dict_to_rows(dataset)
    
    # 파싱 및 정렬 준비
    parsed = []
    for row in rows:
        stmt = row.get("statement", row)
        
        raw_ts = stmt.get("timestamp")
        ts = None
        if raw_ts:
            if isinstance(raw_ts, datetime):
                ts = raw_ts
            else:
                try:
                    ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                except Exception:
                    pass
                    
        obj = stmt.get("object", {})
        names = obj.get("definition", {}).get("name", {})
        name = "Unknown Page"
        if isinstance(names, dict):
            name = names.get("ko-KR", names.get("en-US", next(iter(names.values())) if names else obj.get("id", name)))
        else:
            name = names or obj.get("id", name)
            
        if ts:
            parsed.append((ts, name))
            
    # 시간 순 정렬
    parsed.sort(key=lambda x: x[0])
    
    results = []
    for idx, (ts, name) in enumerate(parsed):
        # 시간차 계산
        if idx == 0:
            diff_str = "0시 0분 0초"
        else:
            prev_ts = parsed[idx - 1][0]
            diff = (ts - prev_ts).total_seconds()
            
            hours = int(diff // 3600)
            minutes = int((diff % 3600) // 60)
            seconds = int(diff % 60)
            diff_str = f"{hours}시 {minutes}분 {seconds}초"
            
        results.append({
            "date": ts.date(),
            "name": name,
            "시간차": diff_str
        })
        
    return rows_to_dict(results)

@ensure_data
def navigation_ratio(dataset: Dict[str, Dict[int, Any]]) -> Any:
    """
    유저의 navigation마다 머무른 총 시간을 구합니다.
    """
    rows = dict_to_rows(dataset)
    if not rows:
        return "저장소에 데이터가 없습니다"
        
    # 파싱 및 정렬
    parsed = []
    for row in rows:
        stmt = row.get("statement", row)
        raw_ts = stmt.get("timestamp")
        ts = None
        if raw_ts:
            if isinstance(raw_ts, datetime):
                ts = raw_ts
            else:
                try:
                    ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                except Exception:
                    pass
                    
        obj = stmt.get("object", {})
        names = obj.get("definition", {}).get("name", {})
        name = "Unknown Page"
        if isinstance(names, dict):
            name = names.get("ko-KR", names.get("en-US", next(iter(names.values())) if names else obj.get("id", name)))
        else:
            name = names or obj.get("id", name)
            
        if ts:
            parsed.append((ts, name))
            
    parsed.sort(key=lambda x: x[0])
    
    # 각 메뉴별 머무른 시간 합산
    time_spent = {}
    for idx in range(len(parsed) - 1):
        curr_ts, name = parsed[idx]
        next_ts, _ = parsed[idx + 1]
        
        duration = (next_ts - curr_ts).total_seconds()
        if duration >= 0:
            time_spent[name] = time_spent.get(name, 0.0) + duration
            
    # 결과를 시간 형식으로 포맷
    results = []
    for name, seconds in time_spent.items():
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        time_str = f"{hours:02d}시간 {minutes:02d}분 {secs:02d}초"
        
        results.append({
            "name": name,
            "time": time_str
        })
        
    if not results:
        return "저장소에 데이터가 없습니다"

    return rows_to_dict(results)


# ==============================================================================
# ORIGINAL NAVIGATION FUNCTIONS FOR BACKWARD COMPATIBILITY
# ==============================================================================

def _get_session_id(stmt: Dict[str, Any]) -> str:
    context = stmt.get("context", {})
    extensions = context.get("extensions", {})
    if not extensions:
        return "default_session"
    for key, val in extensions.items():
        if "session-id" in key or key == "session-id":
            return str(val)
    return "default_session"

def _parse_timestamp(stmt: Dict[str, Any]) -> Optional[datetime]:
    raw_ts = stmt.get("timestamp")
    if not raw_ts:
        return None
    if isinstance(raw_ts, datetime):
        return raw_ts
    try:
        return datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
    except Exception:
        return None

@ensure_data
def count_page_views(statements: List[Dict[str, Any]]) -> Any:
    """
    Count navigated verb statements.
    """
    count = 0
    for stmt in statements:
        verb = stmt.get("verb", {})
        verb_id = verb.get("id", "")
        if verb_id.endswith("/navigated") or verb_id == "navigated":
            count += 1
    return count

@ensure_data
def find_popular_paths(statements: List[Dict[str, Any]]) -> Any:
    """
    Find and count navigation transitions (A -> B) grouped by session.
    """
    # Group navigated statements by session
    sessions = {}
    for stmt in statements:
        verb = stmt.get("verb", {})
        verb_id = verb.get("id", "")
        if verb_id.endswith("/navigated") or verb_id == "navigated":
            session_id = _get_session_id(stmt)
            ts = _parse_timestamp(stmt)
            obj = stmt.get("object", {})
            page_id = obj.get("id")
            
            if page_id and ts:
                if session_id not in sessions:
                    sessions[session_id] = []
                sessions[session_id].append((ts, page_id))
                
    paths = {}
    for session_id, page_views in sessions.items():
        # Sort by timestamp
        page_views.sort(key=lambda x: x[0])
        
        # Count transitions
        for idx in range(len(page_views) - 1):
            page_a = page_views[idx][1]
            page_b = page_views[idx + 1][1]
            path_key = f"{page_a} -> {page_b}"
            paths[path_key] = paths.get(path_key, 0) + 1
            
    return paths

@ensure_data
def calc_avg_time_on_page(statements: List[Dict[str, Any]]) -> Any:
    """
    Calculate average time spent on each navigated page.
    """
    # Group statements by session
    sessions = {}
    for stmt in statements:
        session_id = _get_session_id(stmt)
        ts = _parse_timestamp(stmt)
        if not ts:
            continue
            
        verb = stmt.get("verb", {})
        verb_id = verb.get("id", "")
        is_nav = verb_id.endswith("/navigated") or verb_id == "navigated"
        
        obj = stmt.get("object", {})
        page_id = obj.get("id") if is_nav else None
        
        if session_id not in sessions:
            sessions[session_id] = []
        sessions[session_id].append((ts, is_nav, page_id))
        
    page_times = {} # page_id -> [durations]
    
    for session_id, events in sessions.items():
        # Sort by timestamp
        events.sort(key=lambda x: x[0])
        
        for idx in range(len(events) - 1):
            ts, is_nav, page_id = events[idx]
            if is_nav and page_id:
                next_ts = events[idx + 1][0]
                duration = (next_ts - ts).total_seconds()
                if duration >= 0:
                    if page_id not in page_times:
                        page_times[page_id] = []
                    page_times[page_id].append(duration)
                    
    results = {}
    for page_id, durations in page_times.items():
        if durations:
            results[page_id] = sum(durations) / len(durations)
            
    return results

@ensure_data
def identify_exit_pages(statements: List[Dict[str, Any]]) -> Any:
    """
    Identify and count exit page occurrences (last navigated page per session).
    """
    sessions = {}
    for stmt in statements:
        verb = stmt.get("verb", {})
        verb_id = verb.get("id", "")
        if verb_id.endswith("/navigated") or verb_id == "navigated":
            session_id = _get_session_id(stmt)
            ts = _parse_timestamp(stmt)
            obj = stmt.get("object", {})
            page_id = obj.get("id")
            
            if page_id and ts:
                if session_id not in sessions:
                    sessions[session_id] = []
                sessions[session_id].append((ts, page_id))
                
    exits = {}
    for session_id, page_views in sessions.items():
        if not page_views:
            continue
        # Sort by timestamp
        page_views.sort(key=lambda x: x[0])
        # Last one is the exit page
        exit_page = page_views[-1][1]
        exits[exit_page] = exits.get(exit_page, 0) + 1
        
    return exits

def predict_churn(statements: Iterable[Dict[str, Any]]) -> Any:
    """
    세션 이탈 징후(Churn Probability)를 분석합니다.
    - Idle 상태 감지: navigated 후 30초 이상 액션 부재
    - 무의미한 탐색: 10초 이내 3회 이상의 navigated 발생
    """
    stmts_list = list(statements)
    if not stmts_list:
        return "저장소에 데이터가 없습니다"
    
    def get_ts(s):
        # Support both 'timestamp' (string/datetime) and nested raw structure
        raw_stmt = s.get("statement", s)
        ts = raw_stmt.get("timestamp", s.get("timestamp"))
        if not ts: return datetime.min
        if isinstance(ts, datetime): return ts
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except:
            return datetime.min
            
    stmts_list.sort(key=get_ts)
    
    session_events = {} # session-id -> list of (ts, verb_id/category)
    churn_results = {}
    
    for s in stmts_list:
        raw_stmt = s.get("statement", s)
        session_id = _get_session_id(raw_stmt)
        ts = get_ts(s)
        
        # Support both raw verb ID and normalized verb_category
        verb_category = s.get("verb_category")
        verb_id = raw_stmt.get("verb", {}).get("id", "").lower()
        
        is_navigated = (verb_category == "navigated") or ("navigated" in verb_id)
        
        if session_id not in session_events:
            session_events[session_id] = []
        
        # 1. Idle 상태 체크 (이전 이벤트와의 간격)
        if session_events[session_id]:
            prev_ts, prev_is_nav = session_events[session_id][-1]
            diff = (ts - prev_ts).total_seconds()
            
            if prev_is_nav and diff > 30:
                if session_id not in churn_results:
                    churn_results[session_id] = {"churn_probability": 0.0, "reasons": []}
                if "Idle state detected" not in churn_results[session_id]["reasons"]:
                    churn_results[session_id]["churn_probability"] += 0.6
                    churn_results[session_id]["reasons"].append("Idle state detected")

        session_events[session_id].append((ts, is_navigated))
        
        # 2. 무의미한 탐색 체크 (최근 10초 이내 navigated 빈도)
        if is_navigated:
            recent_navs = [t for t, is_nav in session_events[session_id] 
                          if is_nav and (ts - t).total_seconds() <= 10]
            
            if len(recent_navs) >= 3:
                if session_id not in churn_results:
                    churn_results[session_id] = {"churn_probability": 0.0, "reasons": []}
                if "Meaningless navigation" not in churn_results[session_id]["reasons"]:
                    churn_results[session_id]["churn_probability"] += 0.4
                    churn_results[session_id]["reasons"].append("Meaningless navigation")
                    
    # 확률 상한선 보정
    for sess in churn_results:
        churn_results[sess]["churn_probability"] = min(churn_results[sess]["churn_probability"], 0.95)
        
    if not churn_results:
        return {"result": "데이터 없음"}

    return churn_results
