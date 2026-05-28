# session_validator/io/source_iter.py
import json
from pathlib import Path
from typing import Iterator, Optional
from datetime import datetime, timezone

from pymongo import MongoClient


def iter_jsonl(path: str) -> Iterator[dict]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def _month_bounds(start_yyyymm: str, end_yyyymm: str) -> tuple[datetime, datetime]:
    """YYYY-MM 범위를 UTC datetime [start, end) 으로 변환"""
    s_year, s_mon = map(int, start_yyyymm.split("-"))
    e_year, e_mon = map(int, end_yyyymm.split("-"))
    start = datetime(s_year, s_mon, 1, 0, 0, 0, tzinfo=timezone.utc)
    # end: 다음달 1일
    if e_mon == 12:
        end = datetime(e_year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    else:
        end = datetime(e_year, e_mon + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    return start, end


def iter_mongo(
    host: str,
    port: int,
    username: Optional[str],
    password: Optional[str],
    db_name: str,
    coll_name: str,
    start_yyyymm: str,
    end_yyyymm: str,
    batch_size: int = 2000,
) -> Iterator[dict]:
    """
    MongoDB에서 기간/프로파일(Session) 필터로 문서를 스트리밍
    - 기간: top-level 'stored' (BSON Date) 기준
    - 프로파일: statement.context.contextActivities.category.id == session 프로파일
    """
    start_dt, end_dt = _month_bounds(start_yyyymm, end_yyyymm)

    client = MongoClient(
        host=host,
        port=port,
        username=username,
        password=password,
        # 서버 설정에 맞춰 필요한 옵션 더 추가 가능 (tls 등)
        tz_aware=True,
    )
    coll = client[db_name][coll_name]

    session_profile_id = "http://lecognizer.com/xapi/profiles/session"

    query = {
        "stored": {"$gte": start_dt, "$lt": end_dt},
        "statement.context.contextActivities.category.id": session_profile_id,
    }

    # 최소 필드만 가져와 네트워크/메모리 절약 (검증에 필요한 경로만)
    projection = {
        "_id": 0,
        "statement.timestamp": 1,
        "statement.stored": 1,
        "statement.id": 1,
        "statement.context.contextActivities.category": 1,
        "statement.context.extensions": 1,
    }

    cursor = (
        coll.find(query, projection=projection, batch_size=batch_size)
        .sort([("stored", 1)])  # <-- stored 오름차순 정렬 추가!
    )
    try:
        for doc in cursor:
            yield doc
    finally:
        cursor.close()
        # client.close() removed for connection pooling
