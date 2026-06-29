"""
Input and output guardrails for the chat system.

Tier 1: Regex-based — instant, zero-cost, catches obvious attacks
Tier 2: OpenAI Moderation API — ML classifier, catches nuanced harmful content
Output: PII redaction + system information leak detection
"""

import logging
import re

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger("app.guardrails")


# ── Input Guardrails ─────────────────────────────────────────────

class InputBlockedError(Exception):
    """Raised when user input is rejected by a guardrail tier."""

    def __init__(self, reason: str, category: str):
        self.reason = reason
        self.category = category
        super().__init__(reason)


# ── Tier 1: Regex patterns (instant, zero-cost) ─────────────────

_ABUSE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(fuck|shit|ass(?:hole)?|bitch|cunt|dick|cock|pussy|whore|slut|nigger|faggot|retard)\b", re.IGNORECASE),
    re.compile(r"\b(kill\s+(your|my|the)\s*self|suicide|rape|molest|pedo)\b", re.IGNORECASE),
    re.compile(r"\b(porn|hentai|xxx|nsfw|nude|naked|sex\s*(?:ual|ting)?)\b", re.IGNORECASE),
]

_INJECTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|directions?)", re.IGNORECASE), "instruction override"),
    (re.compile(r"forget\s+(everything|all|your)\s+(you|instructions?|rules?|prompts?)", re.IGNORECASE), "instruction override"),
    (re.compile(r"you\s+are\s+now\s+(a|an|my)\b", re.IGNORECASE), "role hijack"),
    (re.compile(r"act\s+as\s+(if|though|a|an)\b", re.IGNORECASE), "role hijack"),
    (re.compile(r"pretend\s+(you\s+are|to\s+be|you're)\b", re.IGNORECASE), "role hijack"),
    (re.compile(r"(system\s*prompt|system\s*message|instructions?\s*say|what\s+are\s+your\s+(rules?|instructions?|prompts?))", re.IGNORECASE), "system prompt extraction"),
    (re.compile(r"(reveal|show|display|print|output|repeat)\s+(your|the|system)\s*(prompt|instructions?|rules?|config)", re.IGNORECASE), "system prompt extraction"),
    (re.compile(r"(execute|run|eval|exec)\s*(sql|query|command|code|script|shell|bash|python)", re.IGNORECASE), "code execution"),
    (re.compile(r"(drop\s+table|delete\s+from|truncate|alter\s+table|insert\s+into|update\s+\w+\s+set)\b", re.IGNORECASE), "SQL injection"),
    (re.compile(r"(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\s+.{0,20}(FROM|INTO|TABLE|SET|WHERE)", re.IGNORECASE), "SQL injection"),
    (re.compile(r"\b(os\.system|subprocess|__import__|eval\(|exec\(|import\s+os)\b", re.IGNORECASE), "code injection"),
    (re.compile(r"(tell\s+me|what\s+is|describe|explain|show\s+me)\s+(your|the|about\s+(your|the))\s*(architecture|database|schema|infrastructure|stack|server|backend|api\s*key|secret|password|token)", re.IGNORECASE), "architecture probing"),
    (re.compile(r"\b(architecture|infrastructure|tech\s*stack|backend\s*stack|server\s*stack)\b.*\b(your|the\s*app|this\s*app|system)", re.IGNORECASE), "architecture probing"),
    (re.compile(r"\b(your|the|this)\b.*\b(architecture|infrastructure|tech\s*stack|backend\s*stack|server\s*setup)\b", re.IGNORECASE), "architecture probing"),
    (re.compile(r"(access|connect\s+to|query|modify|change|update|delete)\s+(the\s+)?(database|db|postgres|redis|server|backend|admin)", re.IGNORECASE), "unauthorized access"),
    (re.compile(r"(show|display|give|list|dump)\s+(me\s+)?(the\s+)?(database|db)\s*(schema|structure|tables?|records?)", re.IGNORECASE), "architecture probing"),
    (re.compile(r"(give\s+me|show\s+me|list)\s+(all\s+)?(users?|records?|data|emails?|passwords?|api\s*keys?|tokens?|credentials?)", re.IGNORECASE), "data exfiltration"),
    (re.compile(r"<\s*script|javascript:|on\w+\s*=", re.IGNORECASE), "XSS attempt"),
    (re.compile(r"\{\{.*\}\}|\{%.*%\}", re.IGNORECASE), "template injection"),
    (re.compile(r"(DAN|jailbreak|bypass\s+(filter|safety|guard|restriction|content\s*policy))", re.IGNORECASE), "jailbreak attempt"),
]

_REFUSAL_RESPONSES = {
    "abuse": "I'm here to help with your documents. Please keep the conversation respectful.",
    "instruction override": "I can only help with questions about your uploaded documents.",
    "role hijack": "I'm Document Vault AI and I can only assist with document-related questions.",
    "system prompt extraction": "I can't share details about my configuration. I'm here to help you understand your documents.",
    "code execution": "I can't execute code or commands. I can only answer questions about your uploaded documents.",
    "SQL injection": "I can't process database queries. I can only help with document-related questions.",
    "code injection": "I can't execute code. How can I help you with your documents?",
    "architecture probing": "I can't share details about the system architecture. I'm here to help with your documents.",
    "unauthorized access": "I don't have the ability to access or modify any systems. I can only answer questions about your uploaded documents.",
    "data exfiltration": "I can't access user data or system records. I can only help with the documents you've uploaded.",
    "XSS attempt": "I can only help with questions about your uploaded documents.",
    "template injection": "I can only help with questions about your uploaded documents.",
    "jailbreak attempt": "I can only help with questions about your uploaded documents.",
    "moderation_flagged": "Your message was flagged as potentially harmful. I can only help with document-related questions.",
}

_MODERATION_CATEGORY_MESSAGES = {
    "harassment": "I'm here to help with your documents. Please keep the conversation respectful.",
    "harassment/threatening": "I can't engage with threatening content. I'm here to help with your documents.",
    "hate": "I can't engage with hateful content. I'm here to help with your documents.",
    "hate/threatening": "I can't engage with threatening content. I'm here to help with your documents.",
    "illicit": "I can only help with questions about your uploaded documents.",
    "illicit/violent": "I can't engage with violent content. I'm here to help with your documents.",
    "self-harm": "I can't engage with this topic. If you need help, please contact a crisis helpline.",
    "self-harm/intent": "I can't engage with this topic. If you need help, please contact a crisis helpline.",
    "self-harm/instructions": "I can't engage with this topic. If you need help, please contact a crisis helpline.",
    "sexual": "I can only help with document-related questions.",
    "sexual/minors": "I can't engage with this content.",
    "violence": "I can't engage with violent content. I'm here to help with your documents.",
    "violence/graphic": "I can't engage with graphic content. I'm here to help with your documents.",
}


def _check_regex(text: str) -> None:
    """Tier 1: Instant regex-based checks."""
    for pattern in _ABUSE_PATTERNS:
        if pattern.search(text):
            logger.warning("Tier1 blocked abusive input: %s...", text[:80])
            raise InputBlockedError(_REFUSAL_RESPONSES["abuse"], "abuse")

    for pattern, category in _INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning("Tier1 blocked injection (%s): %s...", category, text[:80])
            raise InputBlockedError(
                _REFUSAL_RESPONSES.get(category, _REFUSAL_RESPONSES["code execution"]),
                category,
            )


async def _check_openai_moderation(text: str) -> None:
    """Tier 2: OpenAI Moderation API — ML-based content classification (free)."""
    settings = get_settings()
    if not settings.openai_api_key:
        return

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.moderations.create(
            model="omni-moderation-latest",
            input=text,
        )
        result = response.results[0]

        if not result.flagged:
            return

        flagged_categories = [
            cat for cat, flagged in result.categories.__dict__.items()
            if flagged and not cat.startswith("_")
        ]

        logger.warning(
            "Tier2 OpenAI moderation flagged input — categories: %s, input: %s...",
            flagged_categories,
            text[:80],
        )

        refusal = _REFUSAL_RESPONSES["moderation_flagged"]
        for cat in flagged_categories:
            cat_key = cat.replace("_", "-").replace("/", "/")
            if cat_key in _MODERATION_CATEGORY_MESSAGES:
                refusal = _MODERATION_CATEGORY_MESSAGES[cat_key]
                break

        raise InputBlockedError(refusal, f"moderation:{','.join(flagged_categories)}")

    except InputBlockedError:
        raise
    except Exception as exc:
        exc_name = type(exc).__name__
        if "PermissionDenied" in exc_name or "403" in str(exc):
            logger.info("OpenAI Moderation API not available for this API key — using regex-only guardrails")
        else:
            logger.warning("OpenAI moderation API call failed — falling back to regex only: %s", exc)


def check_input(text: str) -> None:
    """Tier 1 only — synchronous regex check. Use check_input_async for full pipeline."""
    _check_regex(text)


async def check_input_async(text: str) -> None:
    """Full input guardrail pipeline: Tier 1 (regex) + Tier 2 (OpenAI Moderation API)."""
    _check_regex(text)
    await _check_openai_moderation(text)


# ── Output Guardrails ────────────────────────────────────────────

_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN REDACTED]"),
    (re.compile(r"\b\d{9}\b(?=\s|$|[.,])"), "[SSN REDACTED]"),
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[CARD NUMBER REDACTED]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL REDACTED]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[PHONE REDACTED]"),
    (re.compile(r"\b\d{3}-\d{3}-\d{3}\b"), "[TAX ID REDACTED]"),
    (re.compile(r"\b[A-Z]{1,2}\d{6,8}\b"), "[ID NUMBER REDACTED]"),
]

_SYSTEM_LEAK_PATTERNS: list[re.Pattern] = [
    re.compile(r"(system\s*prompt|my\s*instructions?\s*(are|say)|i\s*was\s*(told|instructed|programmed)\s*to)", re.IGNORECASE),
    re.compile(r"(postgresql|postgres|redis|celery|fastapi|uvicorn|langchain|openai\s*api\s*key|sk-proj-)", re.IGNORECASE),
    re.compile(r"(\/app\/|\/usr\/|\/etc\/|\.env|\.py\b|alembic|sqlalchemy)", re.IGNORECASE),
    re.compile(r"(database\s*(schema|table|column|connection)|api[_\s]*key\s*[:=])", re.IGNORECASE),
]


def sanitize_output(text: str) -> str:
    """Redact PII and system information from LLM output."""
    result = text

    for pattern, replacement in _PII_PATTERNS:
        result = pattern.sub(replacement, result)

    for pattern in _SYSTEM_LEAK_PATTERNS:
        if pattern.search(result):
            logger.warning("Blocked system information leak in output")
            result = pattern.sub("[REDACTED]", result)

    return result


async def check_output_async(text: str) -> str:
    """Full output guardrail: PII redaction + moderation check on LLM output."""
    sanitized = sanitize_output(text)

    settings = get_settings()
    if not settings.openai_api_key:
        return sanitized

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.moderations.create(
            model="omni-moderation-latest",
            input=sanitized,
        )
        result = response.results[0]

        if result.flagged:
            flagged = [
                cat for cat, flagged in result.categories.__dict__.items()
                if flagged and not cat.startswith("_")
            ]
            logger.warning("Tier2 flagged LLM output — categories: %s", flagged)
            return "I'm sorry, I wasn't able to generate an appropriate response. Please try rephrasing your question about the documents."

    except Exception as exc:
        exc_name = type(exc).__name__
        if "PermissionDenied" not in exc_name and "403" not in str(exc):
            logger.warning("OpenAI moderation check on output failed: %s", exc)

    return sanitized


def check_output(text: str) -> str:
    """Synchronous output guardrail (regex-only). Use check_output_async for full pipeline."""
    return sanitize_output(text)
