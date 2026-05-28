# session_verb_flow_check/io/source_iter.py
import json
import time
import logging
from pathlib import Path
from typing import Iterator, Optional, Tuple
from datetime import datetime, timezone

from pymongo import MongoClient

log = logging.getLogger(__name__)

VERB_LOGGED_IN = "http://lecognizer.com/xapi/profiles/session/1.0/verbs/logged-in"
SESSION_PROFILE_ID = "http://lecognizer.com/xapi/profiles/session"

def iter_jsonl(path: str) -> Iterator[dict]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

def _month_bounds(start_yyyymm: str, end_yyyymm: str) -> Tuple[datetime, datetime]:
    """Convert YYYY-MM range to UTC datetime window [start, end)."""
    s_year, s_mon = map(int, start_yyyymm.split("-"))
    e_year, e_mon = map(int, end_yyyymm.split("-"))
    start = datetime(s_year, s_mon, 1, 0, 0, 0, tzinfo=timezone.utc)
    # end: first day of next month
    if e_mon == 12:
        end = datetime(e_year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    else:
        end = datetime(e_year, e_mon + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    return start, end

def iter_mongo_verb(
    host: str,
    port: int,
    username: Optional[str],
    password: Optional[str],
    db_name: str,
    coll_name: str,
    start_yyyymm: str,
    end_yyyymm: str,
    batch_size: int = 2000,
    verb_id: str = VERB_LOGGED_IN,
    profile_id: Optional[str] = SESSION_PROFILE_ID,   # ✅ 추가
) -> Iterator[dict]:
    """
    Stream statements for the given profile (default: session) and verb id within a month window.
    - time window uses top-level 'stored' (BSON Date)
    - profile filter: statement.context.contextActivities.category.id == profile_id (unless 'auto')
    - verb filter: statement.verb.id == verb_id
    """
    start_dt, end_dt = _month_bounds(start_yyyymm, end_yyyymm)

    client = MongoClient(
        host=host,
        port=port,
        username=username,
        password=password,
        tz_aware=True,
    )
    coll = client[db_name][coll_name]

    query = {
        "stored": {"$gte": start_dt, "$lt": end_dt},
    }
    # profile 필터: 'auto'면 필터 생략
    if profile_id and str(profile_id).lower() != "auto":
        query["statement.context.contextActivities.category.id"] = profile_id
    if verb_id:
        query["statement.verb.id"] = verb_id

    projection = {
        "_id": 0,
        "stored": 1,
        "statement.id": 1,
        "statement.timestamp": 1,
        "statement.stored": 1,
        "statement.verb.id": 1,
        "statement.context.extensions": 1,
        "statement.result.extensions": 1,
    }

    cursor = (
        coll.find(query, projection=projection, batch_size=batch_size)
        .sort([("stored", 1)])
    )
    try:
        for doc in cursor:
            yield doc
    finally:
        cursor.close()
        # client.close() removed for connection pooling

def yyyymm(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"

def iter_mongo_verb_by_month(
    **kwargs,
) -> Iterator[tuple[str, dict]]:
    """
    Yield (YYYY-MM, doc) tuples, bucketed by the document's top-level 'stored' month.
    kwargs는 iter_mongo_verb의 인자들(verb_id, profile_id 포함)이 그대로 전달됨.
    """
    for doc in iter_mongo_verb(**kwargs):
        stored = doc.get("statement", {}).get("stored") or doc.get("stored")
        if not isinstance(stored, datetime):
            # if stored is string, try to parse quickly
            stored = datetime.fromisoformat(str(stored).replace("Z", "+00:00"))
        yield yyyymm(stored), doc

def iter_mongo_verb_monthwise(
    host: str,
    port: int,
    username: Optional[str],
    password: Optional[str],
    db_name: str,
    coll_name: str,
    start_yyyymm: str,
    end_yyyymm: str,
    batch_size: int = 2000,
    verb_id: str = VERB_LOGGED_IN,
    profile_id: Optional[str] = SESSION_PROFILE_ID,   # ✅ 추가
) -> Iterator[tuple[str, dict]]:
    """
    월별로 쿼리를 쪼개서 가져옴. (YYYY-MM, doc) 튜플 반환
    실제로 '달마다 가져오는지'를 확인하고, 월별 성능/건수 로그를 남긴다.
    """
    client = MongoClient(
        host=host,
        port=port,
        username=username,
        password=password,
        tz_aware=True,
    )
    coll = client[db_name][coll_name]

    def _seq(a: str, b: str):
        y, m = map(int, a.split("-"))
        ye, me = map(int, b.split("-"))
        while (y, m) <= (ye, me):
            yield f"{y:04d}-{m:02d}"
            if m == 12:
                y += 1; m = 1
            else:
                m += 1

    try:
        for mm in _seq(start_yyyymm, end_yyyymm):
            start_dt, end_dt = _month_bounds(mm, mm)

            query = {
                "stored": {"$gte": start_dt, "$lt": end_dt},
            }
            if profile_id and str(profile_id).lower() != "auto":
                query["statement.context.contextActivities.category.id"] = profile_id
            if verb_id:
                query["statement.verb.id"] = verb_id

            projection = {
                "_id": 0,
                "stored": 1,
                "statement.id": 1,
                "statement.timestamp": 1,
                "statement.stored": 1,
                "statement.verb.id": 1,
                "statement.context.extensions": 1,
                "statement.result.extensions": 1,
            }

            t0 = time.perf_counter()
            count = 0
            log.debug(f"[FETCH:{mm}] 월별 쿼리 시작 ...")
            cursor = (
                coll.find(query, projection=projection, batch_size=batch_size)
                .sort([("stored", 1)])
            )
            try:
                for doc in cursor:
                    count += 1
                    yield mm, doc
            finally:
                cursor.close()
            dt = (time.perf_counter() - t0) * 1000
            log.debug(f"[FETCH:{mm}] 완료 - {count}건, {dt:.1f}ms")
    finally:
        # client.close() removed for connection pooling
