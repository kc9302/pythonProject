import os
from pymongo import MongoClient

MONGO_URI = "mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/"

def main():
    print("Connecting to MongoDB at 192.168.0.200:27017...")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command('ping')
        print("Connected successfully!")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # List all databases
    db_names = client.list_database_names()
    print(f"\nFound {len(db_names)} databases:")
    print("=" * 60)

    for db_name in db_names:
        db = client[db_name]
        print(f"\nDatabase: {db_name}")
        print("-" * 30)
        try:
            colls = db.list_collection_names()
            if not colls:
                print("  (Empty - No collections)")
                continue
            for col_name in colls:
                count = db[col_name].estimated_document_count()
                print(f"  * {col_name}: {count:,} documents")
                
                # Check sample values or structure for main lrs data
                if db_name in ["lrs_test", "lrs", "kt_lrs"] and col_name in ["statements", "statement"]:
                    # Fetch one sample to see actor type
                    sample = db[col_name].find_one()
                    if sample:
                        print("    - Has data. Sample _id:", sample.get("_id"))
        except Exception as e:
            print(f"  Error reading database: {e}")

    client.close()

if __name__ == "__main__":
    main()
