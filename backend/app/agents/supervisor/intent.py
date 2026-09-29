import re

OBJECT_ID_RE = re.compile(r"\b[a-f0-9]{24}\b", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)

CREATE_USER_RE = re.compile(
    r"\b(create|register|add|onboard|new)\b.*\b(user|customer)\b"
    r"|\b(user|customer)\b.*\b(create|register|add|onboard)\b",
    re.IGNORECASE,
)
CREATE_QUOTE_VERB_RE = re.compile(
    r"\b(create|add|make|new)\b.*\bquote\b"
    r"|\bquote\b.*\b(create|add|make)\b"
    r"|\bquote\s+for\b"
    r"|\bquote\b.*\b(customer|name)\b"
    r"|\b(customer|name)\b.*\bquote\b",
    re.IGNORECASE,
)
QUOTE_FIELDS_RE = re.compile(
    r"\b(origin|destination|cargo|cut[\s-]?off|mode)\b",
    re.IGNORECASE,
)
QUOTE_LIST_RE = re.compile(
    r"\b(get|fetch|show|find|list|give|want|need|retrieve)\b.*\bquotes?\b"
    r"|\ball\s+quotes?\b"
    r"|\bquotes?\s+(created\s+)?(for|of|by)\b",
    re.IGNORECASE,
)
USER_LOOKUP_RE = re.compile(
    r"\b(get|fetch|show|find|lookup|give|want|need|retrieve)\b.*"
    r"\b(user|customer|details?|id|email)\b"
    r"|\b(user|customer)\s+details?\b"
    r"|\bdetails?\s+(of|for|about)\b",
    re.IGNORECASE,
)
CANCEL_RE = re.compile(
    r"^\s*(cancel|never\s*mind|stop|forget\s*it|abort)\s*[.!?]?\s*$",
    re.IGNORECASE,
)
# Atlas company id from seed data, e.g. CMP001
COMPANY_ID_RE = re.compile(r"\bCMP\d{3,}\b", re.IGNORECASE)
SDR_RE = re.compile(
    r"\b(find|search|match|show|list|get|fetch|discover)\b.*"
    r"\b(compan(?:y|ies)|buyers?|suppliers?|importers?|exporters?|leads?)\b"
    r"|\b(similar\s+buyers?|match\s+a\s+company|company\s+search)\b"
    r"|\b(hs\s*codes?|hs\s*\d{4,}|\bteu\b)\b"
    r"|\b(customers?|contacts?|people)\b.*"
    r"\b(compan(?:y|ies)|this\s+company|locked|cmp\d+)\b"
    r"|\b(compan(?:y|ies))\b.*"
    r"\b(customers?|contacts?|details?|profile)\b"
    r"|\bbuyers?\s+in\b|\bsuppliers?\s+in\b"
    r"|\b(india|singapore|uae|germany|china|vietnam)\b.*"
    r"\b(buyer|supplier|company|importer|exporter)\b",
    re.IGNORECASE,
)
SALES_IMPORT_RE = re.compile(
    r"\bimport\b"
    r"|\b(onboard|save)\b.*\b(this|these|user|customer|contact|atlas|crm|to\s+users)\b"
    r"|\bimport\s+(this|these|them|it|the)\b"
    r"|\b(add|save)\b.*\b(to\s+)?(atlas|users|crm)\b"
    r"|\b(create|register|add|onboard|new)\b.*\b(user|customer)\b",
    re.IGNORECASE,
)
SALES_DELETE_RE = re.compile(
    r"\b(delete|remove)\b.*"
    r"\b(user|users|customer|customers|contact|contacts)\b"
    r"|\b(delete|remove)\b.*"
    r"\b(today|yesterday)\b",
    re.IGNORECASE,
)


def looks_like_import(text: str) -> bool:
    """Ultra-simple fallback so 'Import …' never stays on SDR."""
    t = (text or "").lower()
    return "import" in t or "save to atlas" in t or "add to atlas" in t


def is_quote_create_intent(text: str) -> bool:
    text = text or ""
    if CREATE_QUOTE_VERB_RE.search(text):
        return True
    # Partial create follow-ups that mention lane fields without "quote"
    if QUOTE_FIELDS_RE.search(text) and (
        EMAIL_RE.search(text)
        or OBJECT_ID_RE.search(text)
        or "quote" in text.lower()
        or re.search(r"\b(customer|name)\b", text, re.IGNORECASE)
    ):
        # Avoid treating "get quotes for email Origin:..." as create — list wins if list verbs present
        if QUOTE_LIST_RE.search(text) and not CREATE_QUOTE_VERB_RE.search(text):
            return False
        return bool(
            re.search(r"\bquote\b", text, re.IGNORECASE)
            or CREATE_QUOTE_VERB_RE.search(text)
            or (
                QUOTE_FIELDS_RE.search(text)
                and re.search(r"\b(create|add|make)\b", text, re.IGNORECASE)
            )
        )
    return False


def is_quote_list_intent(text: str) -> bool:
    text = text or ""
    if CREATE_QUOTE_VERB_RE.search(text):
        return False
    return bool(QUOTE_LIST_RE.search(text))


def is_create_intent(text: str) -> bool:
    """Legacy create-user phrasing — now handled by sales import."""
    return is_sales_import_intent(text)


def is_sales_import_intent(text: str) -> bool:
    text = text or ""
    if is_quote_create_intent(text) or is_quote_list_intent(text):
        return False
    if is_sales_delete_intent(text):
        return False
    if looks_like_import(text):
        return True
    return bool(SALES_IMPORT_RE.search(text) or CREATE_USER_RE.search(text))


def is_sales_delete_intent(text: str) -> bool:
    text = text or ""
    if is_quote_list_intent(text) or is_quote_create_intent(text):
        return False
    return bool(SALES_DELETE_RE.search(text))


def is_sales_intent(text: str) -> bool:
    return is_sales_import_intent(text) or is_sales_delete_intent(text)


def is_explicit_lookup_intent(text: str) -> bool:
    """Clear user/customer details lookup — not bare email/id alone."""
    text = text or ""
    if is_quote_list_intent(text) or is_quote_create_intent(text):
        return False
    if is_create_intent(text):
        return False
    return bool(USER_LOOKUP_RE.search(text))


def is_lookup_intent(text: str) -> bool:
    """Existing customer lookup when no sticky task is open.

    Bare email/id counts here; while a quote/sales draft is open,
    prefer is_explicit_lookup_intent so follow-up emails stay on that task.
    """
    text = text or ""
    if is_quote_list_intent(text) or is_quote_create_intent(text):
        return False
    if is_create_intent(text):
        return False
    return bool(
        is_explicit_lookup_intent(text)
        or OBJECT_ID_RE.search(text)
        or EMAIL_RE.search(text)
    )


def is_cancel_intent(text: str) -> bool:
    return bool(CANCEL_RE.search(text or ""))


def is_sdr_intent(text: str) -> bool:
    """Company / customer discovery for the Atlas SDR agent."""
    text = text or ""
    if is_quote_list_intent(text) or is_quote_create_intent(text):
        return False
    if is_sales_intent(text):
        return False
    # Bare Atlas company pick (CMP001) while discovering
    if COMPANY_ID_RE.search(text):
        return True
    return bool(SDR_RE.search(text))


def has_open_sdr(state: dict) -> bool:
    """Sticky SDR when a company is locked or results were just listed."""
    if state.get("locked_company_id"):
        return True
    if state.get("listed_companies"):
        return True
    if state.get("listed_customers"):
        return True
    return False


def has_open_quote_create(state: dict) -> bool:
    if state.get("created_quote"):
        return False
    extracted = state.get("extracted_quote") or {}
    if not extracted:
        return False
    return (extracted.get("intent") or "create").lower() != "list"


def has_open_sales(state: dict) -> bool:
    if state.get("created_user"):
        return False
    extracted = state.get("extracted_user") or {}
    if not extracted:
        return False
    return not extracted.get("name") or not extracted.get("email")
