from pymongo import MongoClient

MONGO_URI = "mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/"

def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["lrs"]
    coll = db["statements"]
    
    print("Checking indexes on lrs.statements (743M)...")
    indexes = list(coll.list_indexes())
    print(f"Found {len(indexes)} indexes:")
    for idx in indexes:
        print(f"  - Name: {idx['name']}, Keys: {idx['key']}")
        
    client.close()

if __name__ == "__main__":
    main()
