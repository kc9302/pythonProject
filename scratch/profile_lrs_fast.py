from pymongo import MongoClient
import re
import time

MONGO_URI = "mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/"

def is_korean_human_name(name):
    if not name:
        return False
    # Typical Korean names are 2-4 characters long, consisting of Korean Hangul syllables
    if re.search(r"학생|테스트|test|student|teacher|교사|관리자|KERIS|바꿔|user|admin|system", name, re.IGNORECASE):
        return False
    # Check if Hangul only and 2-4 chars
    hangul_pattern = re.compile(r"^[가-힣]{2,4}$")
    return bool(hangul_pattern.match(name))

def main():
    client = MongoClient(MONGO_URI)
    db = client["lrs"]
    coll = db["statements"]
    
    print("Profiling a fast subset of 200,000 records from lrs.statements...")
    t0 = time.time()
    
    pipeline = [
        {"$limit": 200000},
        {"$group": {
            "_id": "$statement.actor.account.name",
            "name": {"$first": "$statement.actor.name"},
            "count": {"$sum": 1},
            "verbs": {"$addToSet": "$statement.verb.id"}
        }}
    ]
    
    actors = list(coll.aggregate(pipeline))
    print(f"Grouped unique actors in {time.time() - t0:.2f}s: {len(actors)}")
    
    real_students = []
    rich_testers = []
    
    for a in actors:
        name = a["name"] or ""
        if is_korean_human_name(name):
            real_students.append(a)
        else:
            rich_testers.append(a)
            
    print(f"\nClassification Results for the 200k subset:")
    print("-" * 50)
    print(f"1. Real Students (Korean Human Names): {len(real_students)} accounts")
    print(f"2. Testing/Tester Accounts (e.g. 학생001, 난학생이다): {len(rich_testers)} accounts")
    
    print("\nSample Real Students found:")
    for rs in sorted(real_students, key=lambda x: x["count"], reverse=True)[:10]:
        print(f"  * Name: {rs['name']} | Account: {rs['_id']} | Logs: {rs['count']} | Verbs: {len(rs['verbs'])}")
        
    print("\nSample Testers found:")
    for rt in sorted(rich_testers, key=lambda x: x["count"], reverse=True)[:10]:
        print(f"  * Name: {rt['name']} | Account: {rt['_id']} | Logs: {rt['count']} | Verbs: {len(rt['verbs'])}")

    client.close()

if __name__ == "__main__":
    main()
