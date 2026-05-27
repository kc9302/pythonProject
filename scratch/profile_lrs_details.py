from pymongo import MongoClient
import time

MONGO_URI = "mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/"

def main():
    print("Connecting...")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["lrs"]
    coll = db["statements"]

    print("Fetching distinct verbs using index...")
    t0 = time.time()
    try:
        # distinct uses the index, which should be very fast
        verbs = coll.distinct("statement.verb.id")
        print(f"Found {len(verbs)} distinct verbs in {time.time() - t0:.2f}s:")
        for v in verbs:
            print(f"  - {v}")
    except Exception as e:
        print(f"Failed to fetch distinct verbs: {e}")

    print("\nFetching some sample documents to see real data structures...")
    # Let's find some distinct actors by scanning a small range or sample
    t0 = time.time()
    try:
        pipeline = [
            {"$limit": 10000},
            {"$group": {
                "_id": "$statement.actor.account.name",
                "actor_name": {"$first": "$statement.actor.name"},
                "homePage": {"$first": "$statement.actor.account.homePage"},
                "count": {"$sum": 1},
                "verbs": {"$addToSet": "$statement.verb.id"}
            }},
            {"$limit": 15}
        ]
        samples = list(coll.aggregate(pipeline))
        print(f"Grouped samples in {time.time() - t0:.2f}s:")
        for s in samples:
            print(f"  Account Name: {s['_id']} | Name: {s.get('actor_name')} | HomePage: {s.get('homePage')} | Count: {s['count']} | Verbs: {len(s['verbs'])}")
    except Exception as e:
        print(f"Failed to fetch sample actors: {e}")

    client.close()

if __name__ == "__main__":
    main()
