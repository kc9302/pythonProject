from pymongo import MongoClient
import re

MONGO_URI = "mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/"

def is_korean_human_name(name):
    if not name:
        return False
    # Typical Korean names are 2-4 characters long, consisting of Korean Hangul syllables
    # Exclude obvious test keywords
    if re.search(r"학생|테스트|test|student|teacher|교사|관리자|KERIS|바꿔", name, re.IGNORECASE):
        return False
    # Check if Hangul only and 2-5 chars
    hangul_pattern = re.compile(r"^[가-힣]{2,5}$")
    return bool(hangul_pattern.match(name))

def main():
    client = MongoClient(MONGO_URI)
    db = client["lrs"]
    coll = db["statements"]
    
    print("Profiling actors in lrs.statements...")
    
    # Run an aggregate to group by actor name
    pipeline = [
        {"$group": {
            "_id": "$statement.actor.account.name",
            "name": {"$first": "$statement.actor.name"},
            "count": {"$sum": 1},
            "verbs": {"$addToSet": "$statement.verb.id"}
        }}
    ]
    
    actors = list(coll.aggregate(pipeline))
    print(f"Total Unique Actor Accounts: {len(actors):,}")
    
    real_students = []
    rich_testers = []
    uuid_bots = []
    
    for a in actors:
        acc_name = a["_id"] or ""
        name = a["name"] or ""
        count = a["count"]
        verbs = a["verbs"]
        
        # 1. 1-log UUID bots
        if len(acc_name) == 36 and count == 1:
            uuid_bots.append(a)
        elif is_korean_human_name(name):
            real_students.append(a)
        else:
            rich_testers.append(a)
            
    print("\nClassification Results:")
    print("-" * 50)
    print(f"1. Real Students (Korean Human Names): {len(real_students)} accounts")
    print(f"2. Richer Testing/Tester Accounts (e.g. 학생001, 난학생이다): {len(rich_testers)} accounts")
    print(f"3. UUID 1-Log Load Bots: {len(uuid_bots)} accounts")
    
    print("\nSample Real Students:")
    for rs in sorted(real_students, key=lambda x: x["count"], reverse=True)[:10]:
        print(f"  * Name: {rs['name']} | Account: {rs['_id']} | Logs: {rs['count']} | Verbs: {len(rs['verbs'])}")
        
    print("\nSample Richer Testers:")
    for rt in sorted(rich_testers, key=lambda x: x["count"], reverse=True)[:10]:
        print(f"  * Name: {rt['name']} | Account: {rt['_id']} | Logs: {rt['count']} | Verbs: {len(rt['verbs'])}")

    client.close()

if __name__ == "__main__":
    main()
