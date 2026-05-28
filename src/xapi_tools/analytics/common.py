from typing import Dict, Any, List, Set
from datetime import datetime
from xapi_tools.utils.pandas_helper import dict_to_rows
from xapi_tools.analytics.utils import ensure_data

@ensure_data
def active_days_count(dataset: Dict[str, Dict[int, Any]]) -> Any:
    """
    유저가 실제로 로그를 남긴 날짜의 총합(출석일수)을 구합니다.
    """
    rows = dict_to_rows(dataset)
    active_dates: Set[str] = set()
    for r in rows:
        ts = r.get("timestamp")
        if ts:
            # ISO 8601 문자열에서 날짜 부분(YYYY-MM-DD)만 추출
            if isinstance(ts, str):
                date_str = ts.split('T')[0]
                active_dates.add(date_str)
            elif isinstance(ts, datetime):
                active_dates.add(ts.strftime('%Y-%m-%d'))
                
    return {
        "total_active_days": len(active_dates),
        "dates": sorted(list(active_dates), reverse=True)
    }

@ensure_data
def verb_distribution(dataset: Dict[str, Dict[int, Any]]) -> Any:
    """
    유저가 발생시킨 행동(Verbs)의 종류와 횟수 분포를 구합니다.
    """
    rows = dict_to_rows(dataset)
    distribution = {}
    for r in rows:
        verb = r.get("verb_category") or "unknown"
        distribution[verb] = distribution.get(verb, 0) + 1
        
    return {
        "verb_counts": distribution,
        "total_verbs": len(distribution),
        "total_activities": len(rows)
    }
