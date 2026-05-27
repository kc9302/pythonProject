import logging
import re
from typing import Dict, List, Tuple

log = logging.getLogger(__name__)
_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_NUMERIC_RE = re.compile(r"^[0-9]+$")

def _get(d: dict, path: str, default=None):
    cur = d
    for key in path.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur

def _month_label(ts_iso: str) -> str:
    return ts_iso[:7]

def _as_extensions(doc: dict):
    return _get(doc, "statement.context.extensions")

def validate_one(doc: dict, rules: dict) -> Tuple[str, List[str]]:
    errors: List[str] = []

    ts = _get(doc, "statement.timestamp") or _get(doc, "statement.stored")
    month = _month_label(ts) if isinstance(ts, str) and len(ts) >= 7 else "unknown"

    # 1) category
    cat = _get(doc, "statement.context.contextActivities.category")
    c_cfg = rules["checks"]["category"]
    if isinstance(cat, list) and cat:
        c0 = cat[0]
        if c0.get("id") != c_cfg["expected_id"]:
            errors.append(c_cfg["errors"]["bad_category_id"])
        name = (((c0.get("definition") or {}).get("name") or {}).get("en-US"))
        desc = (((c0.get("definition") or {}).get("description") or {}).get("en-US"))
        if name != c_cfg["expected_name_enUS"] or desc != c_cfg["expected_desc_enUS"]:
            errors.append(c_cfg["errors"]["bad_category_name"])
    else:
        errors.append(c_cfg["errors"]["bad_category_id"])
        errors.append(c_cfg["errors"]["bad_category_name"])

    # 2) extensions
    ex_cfg = rules["checks"]["extensions"]
    ex = _as_extensions(doc)
    if ex_cfg.get("must_exist_object", True):
        if not isinstance(ex, dict):
            errors.append(ex_cfg["errors"]["not_object"])
            logging.getLogger("not_object").error("doc_id=%s extensions is not object",
                                                  _get(doc, "statement.id"))
            return month, errors

    for k in ex_cfg["keys"]:
        key = k["path"]
        required = k.get("required", False)
        typ = k.get("type")
        fmt = k.get("format")
        val = None if not isinstance(ex, dict) else ex.get(key, None)

        if val is None:
            if required:
                errors.append(k["error_missing"])
            continue

        # type
        if typ == "string" and not isinstance(val, str):
            errors.append(k["error_type"]); continue
        if typ == "integer" and not isinstance(val, int):
            errors.append(k["error_type"]); continue

        # format
        if fmt == "nonempty":
            if isinstance(val, str) and not val.strip():
                errors.append(k["error_format"])
        elif fmt == "ipv4":
            if not (isinstance(val, str) and _IPV4_RE.match(val)):
                errors.append(k["error_format"])
            else:
                if any(int(o) > 255 for o in val.split(".")):
                    errors.append(k["error_format"])
        elif fmt == "nonempty_numeric":
            if not (isinstance(val, str) and val.strip() and _NUMERIC_RE.match(val.strip())):
                errors.append(k["error_format"])

    return month, errors
