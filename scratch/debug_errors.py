import traceback
from pymongo import MongoClient
from xapi_tools.utils.pandas_helper import rows_to_dict

MONGO_URI = "mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/"
UID = "11572119-e321-4bc2-b57c-4189e5f80936"

def get_dataset():
    client = MongoClient(MONGO_URI)
    db = client["lrs"]
    coll = db["statements"]
    query = {"statement.actor.account.name": UID}
    rows = list(coll.find(query).limit(1000))
    client.close()
    
    rows_clean = [doc.get("statement", doc) for doc in rows]
    return rows_to_dict(rows_clean)

def main():
    dataset = get_dataset()
    print(f"Loaded dataset with {len(dataset)} columns.")
    
    # Test 1: media.initialized_info
    print("\n--- Testing media.initialized_info ---")
    from xapi_tools.analytics import media
    try:
        res = media.initialized_info(dataset)
        print("Success!")
    except Exception as e:
        print("FAIL!")
        traceback.print_exc()
        
    # Test 2: assessment.extensions
    print("\n--- Testing assessment.extensions ---")
    from xapi_tools.analytics import assessment
    try:
        res = assessment.extensions(dataset)
        print("Success!")
    except Exception as e:
        print("FAIL!")
        traceback.print_exc()
        
    # Test 3: applied.assessment_history
    print("\n--- Testing applied.assessment_history ---")
    from xapi_tools.analytics import applied
    try:
        res = applied.assessment_history(dataset)
        print("Success!")
    except Exception as e:
        print("FAIL!")
        traceback.print_exc()

    # Test 4: applied.assessment_grade_history
    print("\n--- Testing applied.assessment_grade_history ---")
    try:
        res = applied.assessment_grade_history(dataset, "5")
        print("Success!")
    except Exception as e:
        print("FAIL!")
        traceback.print_exc()

    # Test 5: applied.subject_correct_rate
    print("\n--- Testing applied.subject_correct_rate ---")
    try:
        res = applied.subject_correct_rate(dataset, "5", "수학")
        print("Success!")
    except Exception as e:
        print("FAIL!")
        traceback.print_exc()

    # Test 6: applied.wrong_answers
    print("\n--- Testing applied.wrong_answers ---")
    try:
        res = applied.wrong_answers(dataset)
        print("Success!")
    except Exception as e:
        print("FAIL!")
        traceback.print_exc()

    # Test 7: applied.wrong_answers_test
    print("\n--- Testing applied.wrong_answers_test ---")
    try:
        res = applied.wrong_answers_test(dataset, "수학")
        print("Success!")
    except Exception as e:
        print("FAIL!")
        traceback.print_exc()

if __name__ == "__main__":
    main()
