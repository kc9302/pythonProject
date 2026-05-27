def extract_actor_name(actor: dict) -> str:
    """
    Extracts a display name for an xAPI Actor.
    Prioritizes 'name', then falls back to 'mbox' (stripping mailto:), 
    then 'account.name', then 'openid', then 'mbox_sha1sum'.
    """
    if "name" in actor:
        return actor["name"]
    
    if "mbox" in actor:
        mbox = actor["mbox"]
        if mbox.startswith("mailto:"):
            return mbox.replace("mailto:", "")
        return mbox
    
    if "account" in actor:
        return actor["account"].get("name", "Unknown Account")
        
    if "openid" in actor:
        return actor["openid"]
        
    return actor.get("mbox_sha1sum", "Unknown Actor")
