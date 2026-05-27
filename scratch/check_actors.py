from pymongo import MongoClient

def main():
    client = MongoClient("mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/")
    db = client["lrs_test"]
    coll = db["statements"]
    
    # Let's count total statements
    total = coll.estimated_document_count()
    print("Total statements in lrs_test.statements:", total)
    
    # Query for distinct or aggregated actor names
    pipeline = [
        {"$group": {"_id": "$statement.actor.name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]
    print("Top actors in statement.actor.name:")
    for doc in coll.aggregate(pipeline):
        print(f"  {doc['_id']}: {doc['count']}")

    pipeline_account = [
        {"$group": {"_id": "$statement.actor.account.name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]
    print("Top actors in statement.actor.account.name:")
    for doc in coll.aggregate(pipeline_account):
        print(f"  {doc['_id']}: {doc['count']}")

if __name__ == "__main__":
    main()
