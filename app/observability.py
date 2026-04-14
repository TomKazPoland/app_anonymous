# === OBSERVABILITY LAYER (SAFE, NON-BLOCKING) ===

def detect_browser(user_agent_raw: str) -> str:
    ua = (user_agent_raw or "").lower()

    if "chrome" in ua:
        return "Chrome"
    if "firefox" in ua:
        return "Firefox"
    if "safari" in ua:
        return "Safari"
    if "edge" in ua:
        return "Edge"

    return "Other"


def extract_request_meta(request):
    try:
        user_agent_raw = request.headers.get("User-Agent", "") or ""
        browser = detect_browser(user_agent_raw)
    except Exception:
        user_agent_raw = ""
        browser = "unknown"

    return {
        "browser": browser,
        "user_agent_raw": user_agent_raw,
        "country": detect_country(request.remote_addr or ""),
    }


def safe_log_event(log_event_func, logger, **kwargs):
    try:
        log_event_func(logger, **kwargs)
    except Exception:
        # NEVER break request flow
        pass


def detect_country(client_ip: str) -> str:
    try:
        if not client_ip:
            return "UNKNOWN"

        # VERY SAFE heuristic (no external deps)
        if client_ip.startswith("146.") or client_ip.startswith("151."):
            return "PL"

        if client_ip.startswith("127.") or client_ip.startswith("10."):
            return "LOCAL"

        return "UNKNOWN"
    except Exception:
        return "UNKNOWN"
