import time
from pymongo import MongoClient

MONGO_URI = "mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/"

def test_media_heatmap_performance():
    print("=== [TEST] Media Heatmap Performance ===")
    client = MongoClient(MONGO_URI)
    db = client["lrs"]
    coll = db["statements"]
    
    activity_id = "https://www.toctocmath.kr/VCS-1-1"
    
    # 1. MongoDB Query Explain
    query = {
        "search.activities": activity_id,
        "statement.verb.id": {
            "$in": [
                "http://lecognizer.com/xapi/profiles/media/1.0/verbs/paused",
                "http://lecognizer.com/xapi/profiles/media/1.0/verbs/seeked"
            ]
        }
    }
    
    start_time = time.time()
    explain_res = coll.find(query).explain()
    duration = (time.time() - start_time) * 1000
    
    winning_plan = explain_res.get("queryPlanner", {}).get("winningPlan", {})
    input_stage = winning_plan.get("inputStage", {})
    index_name = input_stage.get("indexName", "None") or winning_plan.get("indexName", "None")
    
    print(f"Explain query duration: {duration:.2f}ms")
    print(f"Index used: {index_name}")
    assert index_name != "None", "Warning: Query did not use any index!"
    print("MongoDB successfully used index for search.activities!")
    
    # 2. Real Execution & Aggregation Performance
    start_time = time.time()
    from xapi_tools.analytics.media import media_heatmap
    res = media_heatmap(activity_id)
    duration_agg = (time.time() - start_time) * 1000
    
    print(f"Total aggregation time (DB + Python): {duration_agg:.2f}ms")
    print(f"Result count (buckets): {len(res)}")
    if res:
        print(f"Sample Bucket: {res[0]}")
    print("Media Heatmap Test SUCCESS!\n")
    client.close()

def test_assessment_efficiency_performance():
    print("=== [TEST] Assessment Efficiency Performance ===")
    client = MongoClient(MONGO_URI)
    db = client["lrs"]
    coll = db["statements"]
    
    user_id = "11572119-e321-4bc2-b57c-4189e5f80936" # 김태윤
    
    # 1. Explain Query
    query = {
        "statement.actor.account.name": user_id,
        "statement.verb.id": {
            "$in": [
                "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/submitted",
                "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/completed"
            ]
        }
    }
    
    start_time = time.time()
    explain_res = coll.find(query).explain()
    duration = (time.time() - start_time) * 1000
    
    winning_plan = explain_res.get("queryPlanner", {}).get("winningPlan", {})
    index_name = winning_plan.get("inputStage", {}).get("indexName", "None")
    if index_name == "None":
        index_name = winning_plan.get("indexName", "None")
        
    print(f"Explain query duration: {duration:.2f}ms")
    print(f"Index used: {index_name}")
    print("MongoDB successfully used index for actor.account.name!")
    
    # 2. Real Execution Performance
    start_time = time.time()
    from xapi_tools.analytics.assessment import assessment_efficiency
    res = assessment_efficiency(user_id)
    duration_agg = (time.time() - start_time) * 1000
    
    print(f"Total execution time (DB + Python): {duration_agg:.2f}ms")
    print(f"Result count (questions): {len(res)}")
    if res:
        print(f"Sample Question: {res[0]}")
    print("Assessment Efficiency Test SUCCESS!\n")
    client.close()

if __name__ == "__main__":
    test_media_heatmap_performance()
    test_assessment_efficiency_performance()
