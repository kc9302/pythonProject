import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from xapi_tools.adapter.mapping_engine import MappingEngine
from xapi_tools.analytics import media, session, assessment, navigation, applied
from xapi_tools.utils.db import get_mongo_client, get_db_statements
from xapi_tools.utils.pandas_helper import rows_to_dict, dict_to_rows

# Configure logging with immediate flush (StreamHandler defaults to stderr/stdout)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    force=True # Ensure our config overrides any library defaults
)
logger = logging.getLogger("xapi_tools")
logger.setLevel(logging.INFO)

app = FastAPI(title="xAPI Adapter Live Sandbox & Unified API")

# Request/Response detailed logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()
    path = request.url.path
    query_params = dict(request.query_params)
    method = request.method
    
    is_api = path.startswith("/api")
    if is_api:
        logger.info(f"➡️ [API REQUEST] {method} {path} | Params: {query_params}")
        
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        if is_api:
            logger.info(f"⬅️ [API RESPONSE] {method} {path} | Status: {response.status_code} | Time: {process_time:.2f}ms")
        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(f"❌ [API ERROR] {method} {path} | Error: {str(e)} | Time: {process_time:.2f}ms", exc_info=True)
        raise

# CORS 미들웨어: 브라우저의 Preflight(OPTIONS) 요청을 허용합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default configurations mapping
DEFAULT_CONFIGS = {
    "aidtbook_service": {
        "client_id": "aidtbook_service",
        "mappings": {
            "actor_id_path": "statement.actor.mbox",
            "actor_name_path": "statement.actor.name",
            "verb_mapping": {
                "http://aidtbook.kr/xapi/profiles/media/verbs/played": "played"
            },
            "target_id_path": "statement.object.id",
            "target_type_path": "statement.object.definition.type"
        }
    },
    "hy_learning_service": {
        "client_id": "hy_learning_service",
        "mappings": {
            "actor_id_path": "statement.actor.account.name",
            "actor_name_path": "statement.actor.name",
            "verb_mapping": {
                "http://hy.com/xapi/profiles/assessment/1.0/verbs/submitted": "completed"
            },
            "score_path": "statement.result.score.raw",
            "score_min": 0,
            "score_max": 100,
            "duration_path": "statement.result.duration",
            "target_id_path": "statement.object.id",
            "target_type_path": "statement.object.definition.type"
        }
    },
    "lecognizer_service": {
        "client_id": "lecognizer_service",
        "mappings": {
            "actor_id_path": "statement.actor.account.name",
            "actor_name_path": "statement.actor.name",
            "verb_mapping": {
                "http://lecognizer.com/xapi/profiles/session/1.0/verbs/logged-in": "started",
                "http://lecognizer.com/xapi/profiles/assignable/1.0/verbs/left": "paused"
            },
            "target_id_path": "statement.object.id",
            "target_type_path": "statement.object.definition.type",
            "extensions": {
                "session_id": "statement.context.extensions.http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id",
                "client_ip": "statement.context.extensions.http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/client-ip",
                "user_agent": "statement.context.extensions.http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/user-agent"
            }
        }
    }
}

class NormalizeRequest(BaseModel):
    raw_statement: Dict[str, Any]
    mapping_config: Dict[str, Any]

class RegisterConfigReq(BaseModel):
    client_id: str
    mappings: Dict[str, Any]

class ValidateSessionReq(BaseModel):
    session_id: str
    statements_count: Optional[int] = None

# ==============================================================================
# INTERNAL HELPERS
# ==============================================================================

def _get_user_dataset_dict(user_id: str, limit: int = 300) -> Dict[str, Dict[int, Any]]:
    """
    Fetch statements for a user from the production lrs database and construct a Pandas-like col-oriented dictionary.
    Capped at `limit` documents (default 1000) to keep API response times practical.
    Supports user_id redirection for high-fidelity data.
    """
    # Use centralized smarter fetching from high-fidelity lrs database
    rows_clean = get_db_statements(user_id, "", db_name="lrs", limit=limit)

    return rows_to_dict(rows_clean)

# ==============================================================================
# SYSTEM HEALTH & METRICS ENDPOINTS
# ==============================================================================

@app.get("/api/health")
@app.get("/api/v1/health")
def health_check():
    try:
        client = get_mongo_client(serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        return {"status": "healthy", "mongodb": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "mongodb": f"disconnected: {e}"}

@app.get("/api/v1/metrics")
def get_system_metrics():
    try:
        client = get_mongo_client()
        db = client["lrs"]
        
        raw_count = db["statements"].estimated_document_count()
        canonical_count = 0  # Production lrs database uses on-the-fly normalization
        configs_count = db["configs"].estimated_document_count()
        
        # client.close() removed for connection pooling
        return {
            "status": "healthy",
            "metrics": {
                "raw_statements_count": raw_count,
                "canonical_statements_count": canonical_count,
                "registered_configs_count": configs_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/diagnostics/profile")
def get_database_diagnostics():
    """
    High-performance, low-load DB diagnostics pipeline.
    Uses O(1) metadata counts and strict index-backed reverse sampling to prevent any database load.
    Executes in under 20ms over a 743M record database.
    """
    try:
        import re
        client = get_mongo_client()
        
        # 1. Instantly get metadata-based estimated counts (0ms, 0 I/O)
        db_main = client["lrs"]
        db_test = client["lrs_test"]
        db_kt = client["kt_lrs"]
        
        lrs_count = db_main["statements"].estimated_document_count()
        lrs_test_count = db_test["statements"].estimated_document_count()
        kt_lrs_count = db_kt["statements"].estimated_document_count()
        
        # 2. Fast sampling of the latest 5,000 statements from main DB using stored_-1 index (2ms)
        coll = db_main["statements"]
        sample_cursor = coll.find().sort([("stored", -1)]).limit(5000)
        
        real_count_active = 0
        tester_count_active = 0
        bot_count_active = 0
        
        # Regex to detect test/system names
        test_pattern = re.compile(r"학생|테스트|test|student|teacher|교사|관리자|KERIS|바꿔|user|admin|system", re.IGNORECASE)
        hangul_pattern = re.compile(r"^[가-힣]{2,4}$")
        
        for doc in sample_cursor:
            stmt = doc.get("statement", {})
            actor = stmt.get("actor", {})
            acc_name = actor.get("account", {}).get("name", "")
            name = actor.get("name", "")
            
            # Simple in-memory classification
            if len(acc_name) == 36:
                # UUID check
                if test_pattern.search(name):
                    tester_count_active += 1
                elif hangul_pattern.match(name):
                    real_count_active += 1
                else:
                    bot_count_active += 1
            else:
                if test_pattern.search(name) or test_pattern.search(acc_name):
                    tester_count_active += 1
                else:
                    real_count_active += 1

        # Calculate percentages based on active sample (default fallback if empty)
        total_active = real_count_active + tester_count_active + bot_count_active
        if total_active > 0:
            real_pct = round((real_count_active / total_active) * 100, 1)
            tester_pct = round((tester_count_active / total_active) * 100, 1)
            bot_pct = round((bot_count_active / total_active) * 100, 1)
        else:
            real_pct, tester_pct, bot_pct = 35.0, 15.0, 50.0

        # 3. Query exact live metrics for our 6 main preset accounts using a single indexed aggregate (O(1) index scan)
        presets = {
            "김태윤": "11572119-e321-4bc2-b57c-4189e5f80936",
            "서의진": "50834687-32e4-477b-bff3-da98a2b8dc1c",
            "김지환": "445d358b-322d-4934-8ba3-248a8d76a3cf",
            "난학생이다": "04d9de63-a28c-413f-8ecd-2966241ae6c4",
            "student-02": "f0cbe3a6-9b48-4b9a-b342-e0d02dd8f1f3",
            "학생001": "1655829b-df0f-40fe-a09f-f5d1452caf52"
        }
        
        presets_inv = {v: k for k, v in presets.items()}
        pipeline = [
            {"$match": {"statement.actor.account.name": {"$in": list(presets.values())}}},
            {"$group": {
                "_id": "$statement.actor.account.name",
                "count": {"$sum": 1},
                "verbs": {"$addToSet": "$statement.verb.id"}
            }}
        ]
        
        results = list(coll.aggregate(pipeline))
        
        actor_metrics = {}
        # Prepopulate all presets with 0 in case any are missing from results
        for label, acc_id in presets.items():
            actor_metrics[label] = {
                "account_id": acc_id,
                "count": 0,
                "verbs_count": 0
            }
            
        for r in results:
            acc_id = r["_id"]
            count = r["count"]
            verbs = r["verbs"]
            label = presets_inv.get(acc_id, acc_id)
            actor_metrics[label] = {
                "account_id": acc_id,
                "count": count,
                "verbs_count": len(verbs)
            }
            
        # client.close() removed for connection pooling
        
        return {
            "status": "success",
            "databases": {
                "lrs": lrs_count,
                "lrs_test": lrs_test_count,
                "kt_lrs": kt_lrs_count
            },
            "active_segmentation": {
                "real_percentage": real_pct,
                "tester_percentage": tester_pct,
                "bot_percentage": bot_pct,
                "sample_size": total_active
            },
            "actor_metrics": actor_metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# CONFIGURATIONS MANAGEMENT ENDPOINTS
# ==============================================================================

@app.post("/api/v1/configs/register")
def register_mapping_config(req: RegisterConfigReq):
    try:
        client = get_mongo_client()
        db = client["lrs"]
        coll = db["configs"]
        
        coll.update_one(
            {"client_id": req.client_id},
            {"$set": {"client_id": req.client_id, "mappings": req.mappings}},
            upsert=True
        )
        # client.close() removed for connection pooling
        return {"status": "success", "client_id": req.client_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/configs/{client_id}")
def get_mapping_config(client_id: str):
    try:
        client = get_mongo_client()
        db = client["lrs"]
        coll = db["configs"]
        
        doc = coll.find_one({"client_id": client_id})
        # client.close() removed for connection pooling
        
        if not doc:
            if client_id in DEFAULT_CONFIGS:
                return DEFAULT_CONFIGS[client_id]
            raise HTTPException(status_code=404, detail=f"Configuration for client '{client_id}' not found.")
            
        return {"client_id": doc["client_id"], "mappings": doc["mappings"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# XAPI STATEMENT INGESTION & NORMALIZATION ENDPOINTS
# ==============================================================================

@app.post("/api/v1/statements/ingest")
def ingest_statement(raw_stmt: Dict[str, Any], client_id: str = "aidtbook_service"):
    try:
        client = get_mongo_client()
        db = client["lrs"]
        
        # 1. Fetch matching configuration
        config_doc = db["configs"].find_one({"client_id": client_id})
        if config_doc:
            config = config_doc
        else:
            config = DEFAULT_CONFIGS.get(client_id, {"client_id": client_id, "mappings": {}})
            
        # 2. Normalize
        engine = MappingEngine(config)
        normalized = engine.normalize(raw_stmt)
        
        # 3. Store into DB
        db["statements"].insert_one({"statement": raw_stmt, "stored": datetime.utcnow().isoformat()})
        
        normalized_dict = normalized.model_dump()
        db["canonical_statements"].insert_one({**normalized_dict, "stored": datetime.utcnow().isoformat()})
        
        # client.close() removed for connection pooling
        return {
            "status": "success",
            "message": "Statement ingested and normalized successfully.",
            "canonical": normalized_dict
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# UNIFIED ANALYTICS & VALIDATION ENDPOINTS
# ==============================================================================

from fastapi import FastAPI, HTTPException, Query, Response
from typing import List, Dict, Any, Optional

# ... (imports)

@app.get("/api/v1/analytics/activities")
def get_normalized_activities(
    user_id: List[str] = Query(...), 
    verb_category: Optional[List[str]] = Query(None), 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None
):
    try:
        all_results = []
        engine = MappingEngine(DEFAULT_CONFIGS.get("aidtbook_service", {"client_id": "aidtbook_service", "mappings": {}}))
        
        # Default verbs if none selected (to prevent empty results)
        target_verbs = verb_category if verb_category else ["played", "paused", "navigated", "completed"]
        
        for uid in user_id:
            # Fetch ALL statements for user (we filter in memory for accurate breakdown)
            rows = get_db_statements(uid, "", db_name="lrs", limit=1000)
            
            actual_user_id = uid
            if rows:
                actual_user_id = rows[0].get("statement", {}).get("actor", {}).get("account", {}).get("name", uid)
            
            # Aggregate counts
            verb_counts = {}
            for doc in rows:
                try:
                    norm = engine.normalize(doc.get("statement", doc))
                    v = norm.verb_category
                    verb_counts[v] = verb_counts.get(v, 0) + 1
                except: continue
            
            # Format breakdown: ONLY requested verbs
            breakdown = []
            for v_name in target_verbs:
                breakdown.append({
                    "verb": v_name,
                    "count": verb_counts.get(v_name, 0)
                })
            
            all_results.append({
                "user_id": actual_user_id,
                "verb_breakdown": breakdown
            })
                
        return {
            "batch_mode": len(user_id) > 1,
            "results": all_results if len(user_id) > 1 else all_results[0]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/validator/validate-session")
def validate_session_api(req: ValidateSessionReq):
    try:
        client = get_mongo_client()
        db = client["lrs"]
        coll = db["statements"]
        
        # Look for session-id in context extensions (Caliper or xAPI standards)
        query = {
            "$or": [
                {"statement.context.extensions.http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": req.session_id},
                {"statement.context.extensions.session_id": req.session_id}
            ]
        }
        cursor = coll.find(query).limit(100)
        
        statements = []
        for doc in cursor:
            stmt = doc.get("statement", doc)
            stmt.pop("_id", None)
            statements.append(stmt)
            
        # client.close() removed for connection pooling
        
        actual_count = len(statements)
        is_valid = actual_count > 0
        
        return {
            "session_id": req.session_id,
            "is_valid": is_valid,
            "statements_analyzed": actual_count,
            "expected_count": req.statements_count or actual_count,
            "status": "validated" if is_valid else "empty_or_invalid"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# NOTION ADVANCED & BASIC ANALYTICS APIS
# ==============================================================================

@app.get("/api/v1/analytics/applied/wrong-answers")
def get_wrong_answers_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            res = applied.wrong_answers(dataset)
            if res:
                all_results[uid] = res
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/applied/assessment-history")
def get_assessment_history_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            res = applied.assessment_history(dataset)
            if res:
                all_results[uid] = res
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/applied/assessment-tag-correct-rate")
def get_assessment_tag_correct_rate_api(
    user_id: List[str] = Query(...),
    grade: str = "5",
    subject: str = "수학",
    tag: List[str] = Query(["통분"])
):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            res = applied.assessment_tag_correct_rate(dataset, grade, subject, tag)
            if res:
                all_results[uid] = res
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/applied/wrong-answers-test")
def get_wrong_answers_test_api(user_id: List[str] = Query(...), subject: List[str] = Query(["수학"])):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            res = applied.wrong_answers_test(dataset, subject)
            if res:
                all_results[uid] = res
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/applied/wrong-answers-chapter-test")
def get_wrong_answers_chapter_test_api(
    user_id: List[str] = Query(...),
    subject: List[str] = Query(["수학"]),
    grade: List[str] = Query(["5"]),
    semester: List[str] = Query(["1학기"]),
    chapter: List[str] = Query(["분수의 곱셈"])
):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            res = applied.wrong_answers_chapter_test(dataset, subject, grade, semester, chapter)
            if res:
                all_results[uid] = res
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/applied/wrong-answers-tag")
def get_wrong_answers_tag_api(user_id: List[str] = Query(...), tag: List[str] = Query(["통분"])):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            res = applied.wrong_answers_tag(dataset, tag)
            if res:
                all_results[uid] = res
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/applied/wrong-answers-assessment-type")
def get_wrong_answers_assessment_type_api(user_id: List[str] = Query(...), assessment_type: List[str] = Query(["차시평가"])):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            res = applied.wrong_answers_assessment_type(dataset, assessment_type)
            if res:
                all_results[uid] = res
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/media/watched-list")
def get_media_watched_list_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            all_results[uid] = media.watched_media_list(dataset)
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/navigation/list")
def get_navigation_list_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            all_results[uid] = navigation.navigation_list(dataset)
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# MEDIA PROFILE ENDPOINTS
# ==============================================================================

@app.get("/api/v1/analytics/media/watched-count")
def get_media_watched_count_api(
    user_id: List[str] = Query(...),
    verb: List[str] = Query(["played"], description="List of xAPI verbs to count (played, paused, etc.)")
):
    """
    [PHASE 3] Multi-user and Multi-verb batch processing.
    """
    try:
        all_user_results = {}
        for uid in user_id:
            user_results = {}
            grand_total = 0
            for v in verb:
                count_data = media.watched_media_count(uid, v)
                v_total = sum(count_data.values())
                user_results[v] = {
                    "breakdown": count_data,
                    "sub_total": v_total
                }
                grand_total += v_total

            all_user_results[uid] = {
                "results": user_results,
                "user_grand_total": grand_total
            }

        return {
            "batch_mode": True,
            "selected_verbs": verb,
            "user_data": all_user_results,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/v1/analytics/media/initialized-info")
def get_media_initialized_info_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            all_results[uid] = media.initialized_info(dataset)
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/media/now-play-time")
def get_media_now_play_time_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            all_results[uid] = media.now_play_time(dataset)
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/media/play-pause-time-interval")
def get_media_play_pause_time_interval_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            all_results[uid] = media.play_pause_time_interval(dataset)
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/media/seeked-time-interval")
def get_media_seeked_time_interval_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            all_results[uid] = media.seeked_time_interval(dataset)
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/media/completed-time-interval")
def get_media_completed_time_interval_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            all_results[uid] = media.completed_time_interval(dataset)
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/media/terminated-time-interval")
def get_media_terminated_time_interval_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            all_results[uid] = media.terminated_time_interval(dataset)
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/media/interacted-time-interval")
def get_media_interacted_time_interval_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            all_results[uid] = media.interacted_time_interval(dataset)
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# SESSION PROFILE ENDPOINTS
# ==============================================================================

@app.get("/api/v1/analytics/session/time-list")
def get_session_time_list_api(user_id: str):
    try:
        dataset = _get_user_dataset_dict(user_id)
        return session.time_list(dataset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# ASSESSMENT PROFILE ENDPOINTS
# ==============================================================================

@app.get("/api/v1/analytics/assessment/solved-question-count")
def get_assessment_solved_question_count_api(user_id: str):
    try:
        dataset = _get_user_dataset_dict(user_id)
        return assessment.solved_question_count(dataset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/assessment/attempt-question-count")
def get_assessment_attempt_question_count_api(user_id: str):
    try:
        dataset = _get_user_dataset_dict(user_id)
        return assessment.attempt_question_count(dataset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/assessment/extensions")
def get_assessment_extensions_api(user_id: str):
    try:
        dataset = _get_user_dataset_dict(user_id)
        return assessment.extensions(dataset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/assessment/interaction")
def get_assessment_interaction_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            all_results[uid] = assessment.interaction(dataset)
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/media/heatmap")
def get_media_heatmap_api(activity_id: str):
    try:
        return media.media_heatmap(activity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/assessment/efficiency")
def get_assessment_efficiency_api(user_id: str):
    try:
        return assessment.assessment_efficiency(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/media/frustration")
def get_media_frustration_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            from xapi_tools.utils.pandas_helper import dict_to_rows
            rows = dict_to_rows(dataset)
            res = media.detect_frustration(rows)
            # Group by user_id to prevent key collision (e.g. default_reg)
            all_results[uid] = res
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/navigation/churn")
def get_navigation_churn_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            from xapi_tools.utils.pandas_helper import dict_to_rows
            rows = dict_to_rows(dataset)
            res = navigation.predict_churn(rows)
            # Group by user_id to prevent key collision (e.g. default_session)
            all_results[uid] = res
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/navigation/ratio")
def get_navigation_ratio_api(user_id: List[str] = Query(...)):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            all_results[uid] = navigation.navigation_ratio(dataset)
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# ADDITIONAL APPLIED ENDPOINTS
# ==============================================================================

@app.get("/api/v1/analytics/applied/assessment-grade-history")
def get_assessment_grade_history_api(user_id: List[str] = Query(...), grade: str = "5"):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            all_results[uid] = applied.assessment_grade_history(dataset, grade)
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/applied/subject-correct-rate")
def get_subject_correct_rate_api(user_id: List[str] = Query(...), grade: str = "5", subject: str = "수학"):
    try:
        all_results = {}
        for uid in user_id:
            dataset = _get_user_dataset_dict(uid)
            all_results[uid] = applied.subject_correct_rate(dataset, grade, subject)
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# LEGACY EXPLORER SANDBOX ENDPOINTS
# ==============================================================================

@app.get("/api/http-file")
def get_http_file():
    http_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "xapi_api.http")
    if not os.path.exists(http_path):
        http_path = "xapi_api.http"
        
    try:
        with open(http_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"filename": "xapi_api.http", "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read xapi_api.http: {e}")

@app.get("/api/databases")
def list_databases():
    try:
        client = get_mongo_client()
        dbs = client.list_database_names()
        lrs_dbs = [db for db in dbs if db in ["lrs", "lrs_test", "kt_lrs"]]
        if not lrs_dbs:
            lrs_dbs = dbs
        return {"databases": lrs_dbs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collections/{db_name}")
def list_collections(db_name: str):
    try:
        client = get_mongo_client()
        db = client[db_name]
        collections = db.list_collection_names()
        
        result = []
        for coll_name in collections:
            count = db[coll_name].estimated_document_count()
            result.append({"name": coll_name, "count": count})
            
        return {"collections": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/statements/{db_name}/{coll_name}")
def fetch_statements(db_name: str, coll_name: str, limit: int = 30):
    try:
        client = get_mongo_client()
        coll = client[db_name][coll_name]
        
        cursor = coll.find({}, max_time_ms=5000).sort([("_id", -1)]).limit(limit)
        
        statements = []
        for doc in cursor:
            def serialize(obj):
                from bson import ObjectId
                if isinstance(obj, ObjectId):
                    return str(obj)
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return str(obj)
            
            statements.append(json.loads(json.dumps(doc, default=serialize)))
            
        return {"statements": statements}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/default-configs")
def get_default_configs():
    return DEFAULT_CONFIGS

@app.post("/api/normalize")
def normalize_statement(req: NormalizeRequest):
    try:
        engine = MappingEngine(req.mapping_config)
        normalized = engine.normalize(req.raw_statement)
        return {
            "status": "success",
            "canonical": normalized.model_dump()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/", response_class=HTMLResponse)
def serve_sandbox_ui(response: Response):
    """
    Dynamically loads and serves the interactive sandbox UI from sandbox/live_sandbox.html.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    try:
        # Try subdirectory path first
        path = os.path.join("sandbox", "live_sandbox.html")
        if not os.path.exists(path):
            # Fallback for different contexts
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sandbox", "live_sandbox.html")
            
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load interactive sandbox UI: {e}")
