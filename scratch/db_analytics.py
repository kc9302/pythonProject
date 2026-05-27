import os
import json
from pymongo import MongoClient
from collections import Counter
from datetime import datetime

MONGO_URI = "mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/"

def analyze_lrs():
    print("Connecting to MongoDB...")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command('ping')
        print("Connected successfully!")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    db = client["lrs_test"]
    coll = db["statements"]

    print("Fetching total document count...")
    total_docs = coll.estimated_document_count()
    print(f"Total xAPI statements: {total_docs:,}")

    # 1. Actor 분석
    print("\n[1] Profiling Unique Actors...")
    pipeline_actors = [
        {"$group": {
            "_id": "$statement.actor.account.name",
            "count": {"$sum": 1},
            "verbs": {"$addToSet": "$statement.verb.id"},
            "min_time": {"$min": "$statement.timestamp"},
            "max_time": {"$max": "$statement.timestamp"}
        }},
        {"$sort": {"count": -1}}
    ]
    actors = list(coll.aggregate(pipeline_actors))
    print(f"Total Unique Actors (by account.name): {len(actors)}")
    
    print("\nTop 15 Actors by Log Count:")
    print(f"{'Actor ID':<45} | {'Count':<8} | {'Unique Verbs':<12} | {'Active Period'}")
    print("-" * 110)
    for actor in actors[:15]:
        actor_id = actor["_id"] or "Unknown"
        count = actor["count"]
        verbs_count = len(actor["verbs"])
        min_t = actor["min_time"] or "N/A"
        max_t = actor["max_time"] or "N/A"
        print(f"{actor_id:<45} | {count:<8} | {verbs_count:<12} | {min_t} ~ {max_t}")

    # 2. Verb 분석
    print("\n[2] Profiling Verbs Distribution...")
    pipeline_verbs = [
        {"$group": {"_id": "$statement.verb.id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    verbs = list(coll.aggregate(pipeline_verbs))
    print("\nVerbs Frequency:")
    for v in verbs:
        print(f" - {v['_id']}: {v['count']:,} times")

    # 3. 데이터 신뢰도 진단 (가짜 데이터 필터링 기준 탐색)
    print("\n[3] Diagnosing Suspicious / Synthetic Data Patterns...")
    # 비현실적으로 빠른 속도로 연속 전송되었거나 중복된 패턴 등 탐색
    # 특정 기간에만 비정상적으로 쏠린 경우 등
    
    # 예: actor_id 중 36자 UUID 형태는 시스템 테스트용 난수일 가능성이 높음.
    uuid_actors = [a for a in actors if a["_id"] and len(a["_id"]) == 36]
    meaningful_actors = [a for a in actors if a["_id"] and len(a["_id"]) != 36]
    
    print(f" - UUID format actors (Test accounts): {len(uuid_actors)}")
    print(f" - Other formatted actors (Potentially Real): {len(meaningful_actors)}")
    for ma in meaningful_actors[:10]:
        print(f"   * Potentially Real User: {ma['_id']} ({ma['count']} logs, {len(ma['verbs'])} unique verbs)")

    client.close()

if __name__ == "__main__":
    analyze_lrs()
