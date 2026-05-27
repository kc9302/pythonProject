import time
import re
from pymongo import MongoClient

MONGO_URI = "mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/"

def main():
    print("Testing diagnostics performance & database load...")
    t0 = time.time()
    
    client = MongoClient(MONGO_URI)
    db_main = client["lrs"]
    db_test = client["lrs_test"]
    db_kt = client["kt_lrs"]
    
    print("\n[Stage 1] Fetching metadata-based counts...")
    t_start = time.time()
    lrs_count = db_main["statements"].estimated_document_count()
    lrs_test_count = db_test["statements"].estimated_document_count()
    kt_lrs_count = db_kt["statements"].estimated_document_count()
    print(f"  * lrs count: {lrs_count:,}")
    print(f"  * lrs_test count: {lrs_test_count:,}")
    print(f"  * kt_lrs count: {kt_lrs_count:,}")
    print(f"  Time taken for Stage 1: {time.time() - t_start:.4f}s")
    
    print("\n[Stage 2] Scanning latest 5,000 statements from main DB using stored_-1 index...")
    t_start = time.time()
    coll = db_main["statements"]
    sample_cursor = coll.find().sort([("stored", -1)]).limit(5000)
    
    real_count = 0
    tester_count = 0
    bot_count = 0
    
    test_pattern = re.compile(r"학생|테스트|test|student|teacher|교사|관리자|KERIS|바꿔|user|admin|system", re.IGNORECASE)
    hangul_pattern = re.compile(r"^[가-힣]{2,4}$")
    
    for doc in sample_cursor:
        stmt = doc.get("statement", {})
        actor = stmt.get("actor", {})
        acc_name = actor.get("account", {}).get("name", "")
        name = actor.get("name", "")
        
        if len(acc_name) == 36:
            if test_pattern.search(name):
                tester_count += 1
            elif hangul_pattern.match(name):
                real_count += 1
            else:
                bot_count += 1
        else:
            if test_pattern.search(name) or test_pattern.search(acc_name):
                tester_count += 1
            else:
                real_count += 1
                
    total = real_count + tester_count + bot_count
    print(f"  * Sample size: {total}")
    print(f"  * Real active: {real_count} ({real_count/total*100:.1f}%)")
    print(f"  * Tester active: {tester_count} ({tester_count/total*100:.1f}%)")
    print(f"  * Bot active: {bot_count} ({bot_count/total*100:.1f}%)")
    print(f"  Time taken for Stage 2: {time.time() - t_start:.4f}s")
    
    print("\n[Stage 3] Querying exact live metrics for preset accounts using a single indexed aggregate...")
    presets = {
        "김태윤": "11572119-e321-4bc2-b57c-4189e5f80936",
        "서의진": "50834687-32e4-477b-bff3-da98a2b8dc1c",
        "김지환": "445d358b-322d-4934-8ba3-248a8d76a3cf",
        "난학생이다": "04d9de63-a28c-413f-8ecd-2966241ae6c4",
        "student-02": "f0cbe3a6-9b48-4b9a-b342-e0d02dd8f1f3",
        "학생001": "1655829b-df0f-40fe-a09f-f5d1452caf52"
    }
    
    t_start = time.time()
    # Invert presets for lookup
    presets_inv = {v: k for k, v in presets.items()}
    
    pipeline = [
        {"$match": {"statement.actor.account.name": {"$in": list(presets.values())}}},
        {"$group": {
            "_id": "$statement.actor.account.name",
            "count": {"$sum": 1},
            "verbs": {"$addToSet": "$statement.verb.id"}
        }}
    ]
    
    results = list(coll.aggregate(pipeline))
    
    for r in results:
        acc_id = r["_id"]
        count = r["count"]
        verbs = r["verbs"]
        name = presets_inv.get(acc_id, acc_id)
        print(f"  * Account '{name}': {count:,} statements | {len(verbs)} unique verbs")
        
    # Handle presets that have 0 statements
    found_accs = {r["_id"] for r in results}
    for label, acc_id in presets.items():
        if acc_id not in found_accs:
            print(f"  * Account '{label}': 0 statements | 0 unique verbs")
            
    print(f"  Time taken for Stage 3: {time.time() - t_start:.4f}s")
    
    client.close()
    print(f"\nTotal processing time: {time.time() - t0:.4f}s")

if __name__ == "__main__":
    main()
