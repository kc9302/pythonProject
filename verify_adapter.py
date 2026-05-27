import json
from pymongo import MongoClient
from xapi_tools.adapter import MappingEngine

def main():
    mongo_uri = "mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/"
    client = MongoClient(mongo_uri)
    db = client["lrs_test"]
    coll = db["statements"]

    def serialize(obj):
        from bson import ObjectId
        from datetime import datetime
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)

    print("======================================================================")
    print("1. AIDT Book (media.played) normalization:")
    raw_aidt = coll.find_one({"statement.verb.id": "http://aidtbook.kr/xapi/profiles/media/verbs/played"})
    if raw_aidt:
        print("\n[Raw AIDT Statement]:")
        # Just print keys first to keep clean
        print(json.dumps(raw_aidt["statement"], indent=2, default=serialize)[:1000] + "\n...")
        
        aidt_config = {
            "client_id": "aidtbook_service",
            "mappings": {
                "actor_id_path": "statement.actor.account.name",
                "actor_name_path": "statement.actor.name",
                "verb_mapping": {
                    "http://aidtbook.kr/xapi/profiles/media/verbs/played": "played"
                }
            }
        }
        aidt_engine = MappingEngine(aidt_config)
        canonical_aidt = aidt_engine.normalize(raw_aidt)
        print("\n[Normalized Canonical Model]:")
        print(canonical_aidt.model_dump_json(indent=2))

    print("\n" + "="*70)
    print("2. HY.com (assessment.submitted) normalization:")
    raw_hy = coll.find_one({"statement.verb.id": "http://hy.com/xapi/profiles/assessment/1.0/verbs/submitted"})
    if raw_hy:
        print("\n[Raw HY Statement]:")
        print(json.dumps(raw_hy["statement"], indent=2, default=serialize)[:1000] + "\n...")
        
        hy_config = {
            "client_id": "hy_learning_service",
            "mappings": {
                "actor_id_path": "statement.actor.account.name",
                "actor_name_path": "statement.actor.name",
                "verb_mapping": {
                    "http://hy.com/xapi/profiles/assessment/1.0/verbs/submitted": "completed"
                },
                "score_path": "statement.result.score.raw",
                "score_min": 0,
                "score_max": 100
            }
        }
        hy_engine = MappingEngine(hy_config)
        canonical_hy = hy_engine.normalize(raw_hy)
        print("\n[Normalized Canonical Model]:")
        print(canonical_hy.model_dump_json(indent=2))

    client.close()

if __name__ == "__main__":
    main()
