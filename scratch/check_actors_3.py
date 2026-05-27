from pymongo import MongoClient
import pprint

def main():
    client = MongoClient("mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/")
    db = client["lrs_test"]
    coll = db["statements"]
    
    # Let's find a document where statement.actor.name does not exist
    doc = coll.find_one({"statement.actor.name": {"$exists": False}})
    if not doc:
        doc = coll.find_one({"statement.actor.name": None})
        
    if doc:
        print("Keys in document:", doc.keys())
        if "statement" in doc:
            print("Keys in statement:", doc["statement"].keys())
            pprint.pprint(doc["statement"].get("actor"))
        else:
            pprint.pprint(doc)
    else:
        print("No document found without statement.actor.name")

if __name__ == "__main__":
    main()
