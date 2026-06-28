# ── app/core/llm_errors.py ───────────────────────────────────
# Typed seam errors, in their own module so both the seam (core/llm.py) and the
# limiter (core/llm_limiter.py) can use them without an import cycle.
#
# Re-exported from core/llm.py, so callers may import either
# `from app.core.llm import LLMUnavailable` or `from app.core.llm_errors import ...`.


class LLMError(Exception):
    """Base class for LLM seam errors."""


class LLMUnavailable(LLMError):
    """A transient failure that persisted past the retry ceiling (429/timeout/5xx).

    The exam answer path catches this to persist the answer and degrade gracefully
    (Phase 2 commit 4); other callers surface it as their normal error path.
    """


class LLMBusy(LLMError):
    """No concurrency slot became free within the acquire timeout.

    Like LLMUnavailable, the exam path treats this as a safe, degradable failure
    (the answer is persisted and grading catches up); other callers surface a
    clear "system busy".
    """
