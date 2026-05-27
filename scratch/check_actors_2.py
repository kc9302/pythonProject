from pymongo import MongoClient
import pprint

def main():
    client = MongoClient("mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/")
    db = client["lrs_test"]
    coll = db["statements"]
    
    # Find a document where statement.actor.account.name exists and is not None
    doc = coll.find_one({"statement.actor.account.name": {"$exists": True, "$ne": None}})
    if doc:
        pprint.pprint(doc["statement"]["actor"])
        print("\nFull statement sample:")
        pprint.pprint(doc["statement"])
    else:
        print("No statement found with actor.account.name")

if __name__ == "__main__":
    main()
