import os
from pymongo import MongoClient

MONGO_URI = "mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/"

def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    
    # 1. kt_lrs.statements 분석
    print("\n[kt_lrs.statements] 분석:")
    print("-" * 50)
    db_kt = client["kt_lrs"]
    coll_kt = db_kt["statements"]
    
    total_kt = coll_kt.estimated_document_count()
    print(f"총 도큐먼트 수: {total_kt:,}")
    
    # 샘플 3개 확인
    samples = list(coll_kt.find().limit(3))
    for i, s in enumerate(samples):
        print(f"Sample {i+1} structure:")
        # Print actor and verb definition
        statement = s.get("statement", s)
        actor = statement.get("actor", {})
        verb = statement.get("verb", {})
        obj = statement.get("object", {})
        print(f"  Actor: {actor}")
        print(f"  Verb ID: {verb.get('id')}")
        print(f"  Object ID: {obj.get('id')}")
        print(f"  Timestamp: {statement.get('timestamp')}")
        print("-" * 30)

    # 2. lrs.statements 분석 (7억 4천만 건)
    print("\n[lrs.statements] 분석 (7억 4천만 건 대용량):")
    print("-" * 50)
    db_lrs = client["lrs"]
    coll_lrs = db_lrs["statements"]
    
    # 샘플 3개 확인
    samples_lrs = list(coll_lrs.find().limit(3))
    for i, s in enumerate(samples_lrs):
        print(f"Sample {i+1} structure:")
        statement = s.get("statement", s)
        actor = statement.get("actor", {})
        verb = statement.get("verb", {})
        obj = statement.get("object", {})
        print(f"  Actor: {actor}")
        print(f"  Verb ID: {verb.get('id')}")
        print(f"  Object ID: {obj.get('id')}")
        print(f"  Timestamp: {statement.get('timestamp')}")
        print("-" * 30)

    client.close()

if __name__ == "__main__":
    main()
