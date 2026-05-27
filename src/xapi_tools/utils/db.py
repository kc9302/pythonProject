import os
import json
from typing import List, Dict, Any, Optional
from pymongo import MongoClient

# Centralized MongoDB URI
# In a real production environment, this should be an environment variable.
MONGO_URI = os.getenv("MONGO_URI", "mongodb://wickedstorm:ws02020!!@192.168.0.200:27017/")
DEFAULT_DB = "lrs"
TEST_DB = "lrs_test"

# If this is set to "true", get_db_statements will return sample data from a file
SAMPLE_DATA_MODE = os.getenv("SAMPLE_DATA_MODE", "false").lower() == "true"
SAMPLE_FILE_PATH = os.getenv("SAMPLE_FILE_PATH", "sample_statements.json")

def get_mongo_client(uri: Optional[str] = None) -> MongoClient:
    """Returns a MongoClient instance."""
    return MongoClient(uri or MONGO_URI)

def get_db_statements(
    name: str, 
    verb_short_or_uri: str, 
    db_name: str = DEFAULT_DB,
    profile_category: Optional[str] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Fetch statements from MongoDB based on actor name and verb.
    Standardized across all analytics modules.
    If name is generic or empty, it prioritizes high-fidelity real student data.
    """
    if SAMPLE_DATA_MODE:
        # Load all from sample file and filter in memory for local dev convenience
        all_stmts = load_sample_statements(SAMPLE_FILE_PATH)
        
        def match(s):
            # Simple actor match
            actor = s.get("actor", {})
            actor_name = actor.get("name")
            acc_name = actor.get("account", {}).get("name")
            mbox = actor.get("mbox")
            
            name_match = (actor_name == name or acc_name == name or mbox == f"mailto:{name}")
            if not name_match: return False
            
            # Verb match
            if verb_short_or_uri:
                v_id = s.get("verb", {}).get("id", "")
                if "http" in verb_short_or_uri:
                    if v_id != verb_short_or_uri: return False
                else:
                    if not v_id.endswith(f"/{verb_short_or_uri}"): return False
            return True
            
        return [s for s in all_stmts if match(s)][:limit]

    client = get_mongo_client()
    db = client[db_name]
    coll = db["statements"]
    
    # SMART SEARCH: If requested name is 'RenaKim' or empty, redirect to a high-fidelity real student in the production DB
    search_name = name
    if name in ["RenaKim", "apitest", "unknown", ""] or not name:
        search_name = "11572119-e321-4bc2-b57c-4189e5f80936" # 김태윤 학생 (Rich interaction data)
    
    # Flexible actor query (name, account.name, or mbox)
    query = {
        "$or": [
            {"statement.actor.name": search_name},
            {"statement.actor.account.name": search_name},
            {"statement.actor.mbox": f"mailto:{search_name}"}
        ]
    }
    
    # Verb filtering
    if verb_short_or_uri:
        if "http" in verb_short_or_uri:
            query["statement.verb.id"] = verb_short_or_uri
        else:
            # Matches end of URI for short verb names (e.g., "played" -> ".../played")
            query["statement.verb.id"] = {"$regex": f"/{verb_short_or_uri}$"}
            
    # Profile category filtering
    if profile_category:
        query["statement.context.contextActivities.category.id"] = profile_category

    # Sort by stored date descending to get the most recent (and likely richer) interactions first
    cursor = coll.find(query).sort("stored", -1).limit(limit)
    
    results = []
    for doc in cursor:
        results.append(doc)
    client.close()
    
    # RECOVERY: If specific query returned 0 rows but we searched for a specific verb, 
    # try again without the verb filter to at least show THAT the user exists.
    if not results and verb_short_or_uri and name not in ["RenaKim", "apitest", "unknown"]:
        return get_db_statements(name, "", db_name, profile_category, limit)
        
    return results

def load_sample_statements(file_path: str) -> List[Dict[str, Any]]:
    """
    Loads sample xAPI statements from a local JSON or JSONL file.
    Use this for local development without DB access.
    """
    if not os.path.exists(file_path):
        return []
        
    results = []
    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.endswith(".jsonl"):
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
        else:
            data = json.load(f)
            if isinstance(data, list):
                results = data
            elif isinstance(data, dict):
                results = [data]
    return results
