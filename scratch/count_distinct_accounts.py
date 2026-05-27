from pymongo import MongoClient

def main():
    client = MongoClient("mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/")
    db = client["lrs_test"]
    coll = db["statements"]
    
    # We can aggregate with a group on statement.actor.account.name and count the groups
    pipeline = [
        {"$group": {"_id": "$statement.actor.account.name"}},
        {"$group": {"_id": None, "count": {"$sum": 1}}}
    ]
    
    res = list(coll.aggregate(pipeline))
    print("Distinct accounts count:", res[0]["count"] if res else 0)

if __name__ == "__main__":
    main()
