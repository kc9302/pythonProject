from pymongo import MongoClient

def main():
    client = MongoClient("mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/")
    db = client["lrs_test"]
    coll = db["statements"]
    
    pipeline = [
        {"$group": {"_id": "$statement.actor.account.name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    print("Top accounts by statement count:")
    for doc in coll.aggregate(pipeline):
        print(f"  {doc['_id']}: {doc['count']}")

if __name__ == "__main__":
    main()
