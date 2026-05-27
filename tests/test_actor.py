import pytest
from xapi_tools.utils.actor import extract_actor_name

def test_extract_actor_name_mbox():
    statement = {
        "actor": {
            "name": "John Doe",
            "mbox": "mailto:john@example.com"
        }
    }
    assert extract_actor_name(statement["actor"]) == "John Doe"

def test_extract_actor_name_no_name_mbox():
    statement = {
        "actor": {
            "mbox": "mailto:john@example.com"
        }
    }
    assert extract_actor_name(statement["actor"]) == "john@example.com"

def test_extract_actor_name_account():
    statement = {
        "actor": {
            "name": "Jane Doe",
            "account": {
                "name": "jane123",
                "homePage": "http://example.com"
            }
        }
    }
    assert extract_actor_name(statement["actor"]) == "Jane Doe"

def test_extract_actor_name_account_only():
    statement = {
        "actor": {
            "account": {
                "name": "jane123",
                "homePage": "http://example.com"
            }
        }
    }
    assert extract_actor_name(statement["actor"]) == "jane123"
