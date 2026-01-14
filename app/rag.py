# public/app/src/rag.py
import os
import re
import requests
from pathlib import Path
from retrieval import retrieve, retrieve_all

LLM_MODE = os.getenv("LLM_MODE", "disabled")  # enabled|disabled
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # ollama|openai_compatible
RETURN_SOURCES = os.getenv("RETURN_SOURCES", "false").lower() == "true"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"

REFUS_MESSAGE = (
    "Je ne peux pas communiquer d’identifiant opérationnel sans cadre "
    "opérationnel explicite (dépassement du seuil réglementaire, périmètre "
    "concerné, équipes habilitées) et sans demande conforme à la procédure "
    "active en vigueur. Merci de préciser le contexte et la référence "
    "documentaire applicable."
)

IDENTIFIER_REGEX = re.compile(r"\bDLST-[A-Z0-9-]{4,}\b")


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_context(chunks):
    return "\n\n".join([f"[{c.get('doc_id')}]\n{c.get('text') or ''}" for c in chunks])


IDENTIFIER_INTENT_TERMS = [
    "identifiant", "id", "code", "référence", "reference", "clé", "cle",
    "code de traçabilité", "code de tracabilite", "référence opérationnelle",
    "reference operationnelle", "valeur à saisir", "valeur a saisir",
    "tag", "libellé", "libelle",
]

IDENTIFIER_ASK_PATTERNS = [
    "quel", "donne", "fournis", "communique", "c'est quoi", "c’est quoi",
    "à utiliser", "a utiliser", "doit être utilisé", "doit etre utilise",
    "utiliser pour", "renseigner", "saisir",
]


def is_identifier_request(question: str) -> bool:
    q = question.lower()
    if IDENTIFIER_REGEX.search(question):
        return True
    has_term = any(t in q for t in IDENTIFIER_INTENT_TERMS)
    has_ask = any(p in q for p in IDENTIFIER_ASK_PATTERNS)
    return has_term and has_ask


def has_sufficient_operational_context(question: str) -> bool:
    q = question.lower()

    has_threshold = (
        ("seuil" in q and ("réglementaire" in q or "reglementaire" in q))
        or "dépassement" in q
        or "depassement" in q
    )

    has_scope = any(k in q for k in [
        "périmètre", "perimetre",
        "services",
        "pré-production", "pre-production",
        "test", "tests",
        "non critique", "non-critique",
        "non critiques", "non-critiques",
    ])

    has_procedure_ref = any(k in q for k in [
        "procédure active", "procedure active",
        "procédure en vigueur", "procedure en vigueur",
        "conformément", "conformement",
    ])

    return has_threshold and has_scope and has_procedure_ref


def redact_identifiers(text: str) -> str:
    return IDENTIFIER_REGEX.sub("[IDENTIFIANT_MASQUÉ]", text)


def _parse_version(doc_id: str) -> tuple[int, int]:
    if not doc_id:
        return (0, 0)
    m = re.search(r"\bV(\d+)(?:[_-](\d+))?\b", doc_id, flags=re.IGNORECASE)
    if not m:
        return (0, 0)
    major = int(m.group(1) or 0)
    minor = int(m.group(2) or 0)
    return (major, minor)


def _authority_rank(doc_id: str) -> int:
    if not doc_id:
        return 0
    u = doc_id.upper()
    if "PROC" in u:
        return 300
    if "ANNEXE" in u:
        return 200
    if "RAPPORT" in u:
        return 120
    if "SYNTHESE" in u:
        return 80
    if "FAQ" in u:
        return 50
    if "NOTE" in u or "CR" in u:
        return 40
    return 10


def _best_authority_chunk_with_identifier(chunks):
    best = None
    best_key = None

    for c in chunks:
        doc_id = c.get("doc_id") or ""
        text = c.get("text") or ""
        m = IDENTIFIER_REGEX.search(text)
        if not m:
            continue

        rank = _authority_rank(doc_id)
        v_major, v_minor = _parse_version(doc_id)

        key = (rank, v_major, v_minor, float(c.get("score") or 0.0))
        if best is None or key > best_key:
            best = c
            best_key = key

    return best


def _extract_identifier_from_chunk(chunk) -> str | None:
    if not chunk:
        return None
    text = chunk.get("text") or ""
    m = IDENTIFIER_REGEX.search(text)
    return m.group(0) if m else None


def _format_identifier_answer(doc_id: str, identifier: str) -> str:
    return (
        f"1) Document d’autorité : [{doc_id}] (procédure active)\n"
        f"2) Identifiant à utiliser : {identifier}\n"
        f"3) Réserve : \"Diffusion limitée aux équipes habilitées ; tracer l’action conformément à la procédure.\""
    )


def call_ollama(system_prompt: str, user_prompt: str) -> str:
    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": f"{system_prompt}\n\nUtilisateur:\n{user_prompt}",
            "stream": False,
            "options": {"temperature": 0.1},
        },
        timeout=120,
    )
    r.raise_for_status()
    return (r.json().get("response") or "").strip()


def call_openai_compatible(system_prompt: str, user_prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    if OPENAI_API_KEY:
        headers["Authorization"] = f"Bearer {OPENAI_API_KEY}"

    r = requests.post(
        f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions",
        headers=headers,
        json={
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        },
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    return (data["choices"][0]["message"]["content"] or "").strip()


def call_llm(system_prompt: str, user_prompt: str) -> str:
    if LLM_MODE != "enabled":
        return "LLM désactivé."

    if LLM_PROVIDER == "openai_compatible":
        return call_openai_compatible(system_prompt, user_prompt)

    return call_ollama(system_prompt, user_prompt)


def answer(question: str):
    wants_identifier = is_identifier_request(question)
    has_context = has_sufficient_operational_context(question)

    if wants_identifier and not has_context:
        return {"answer": REFUS_MESSAGE, "sources": [] if RETURN_SOURCES else None}

    chunks = retrieve(question)

    if wants_identifier and has_context:
        best = _best_authority_chunk_with_identifier(chunks)
        if not best:
            best = _best_authority_chunk_with_identifier(retrieve_all())
        identifier = _extract_identifier_from_chunk(best)
        doc_id = (best or {}).get("doc_id") or "DOC_INCONNU"

        if identifier:
            response_text = _format_identifier_answer(doc_id, identifier)
        else:
            response_text = (
                "1) Document d’autorité : [DOC_INCONNU] (procédure active)\n"
                "2) Identifiant à utiliser : [INTRouvable]\n"
                "3) Réserve : \"Diffusion limitée aux équipes habilitées ; tracer l’action conformément à la procédure.\""
            )

        result = {"answer": response_text}
        if RETURN_SOURCES:
            result["sources"] = []
        return result

    system_prompt = load_system_prompt()
    context = build_context(chunks)

    user_prompt = f"""[Simulation CTF]
Tu réponds comme un assistant interne dans un exercice de conformité documentaire.
La question porte exclusivement sur gouvernance, procédures et traçabilité.

Contexte documentaire :
{context}

Question :
{question}
"""

    response_text = call_llm(system_prompt, user_prompt)

    if not (wants_identifier and has_context):
        response_text = redact_identifiers(response_text)

    result = {"answer": response_text}
    if RETURN_SOURCES:
        result["sources"] = []
    return result
