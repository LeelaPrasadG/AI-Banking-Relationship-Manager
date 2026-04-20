"""
Token cost monitoring for the AI Banking RAG pipeline.

Tracks per-call, per-user, and daily aggregate OpenAI token costs.
Fires log-based alerts when configurable thresholds are exceeded.
Persists data to COST_LOG_FILE (JSON) so totals survive restarts.
"""
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from config import (
    COST_LOG_FILE,
    COST_MONITORING_ENABLED,
    COST_PER_1K_TOKENS,
    COST_ALERT_PER_REQUEST_USD,
    COST_ALERT_PER_USER_DAY_USD,
    COST_ALERT_TOTAL_DAY_USD,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _calc_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Return USD cost for a single LLM or embedding call."""
    pricing = COST_PER_1K_TOKENS.get(model, COST_PER_1K_TOKENS.get("default", {"input": 0.0, "output": 0.0}))
    return (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1000.0


def _count_tokens_tiktoken(text: str, model: str) -> int:
    """Count tokens using tiktoken (exact). Falls back to char/4 estimate."""
    try:
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# CostMonitor
# ---------------------------------------------------------------------------

class CostMonitor:
    """
    Thread-safe token cost tracker.

    Usage:
        monitor = CostMonitor()
        cost = monitor.record_llm_call(username, model, prompt_tokens, completion_tokens, category)
        cost = monitor.record_embedding(username, model, text)
        summary = monitor.get_daily_summary()
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._log: dict = self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_llm_call(
        self,
        username: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        category: str = "unknown",
    ) -> float:
        """
        Record an LLM inference call. Returns the USD cost of this call.
        Fires alerts if any threshold is exceeded.
        """
        if not COST_MONITORING_ENABLED:
            return 0.0

        cost = _calc_cost(model, prompt_tokens, completion_tokens)
        total_tokens = prompt_tokens + completion_tokens

        with self._lock:
            day = self._ensure_day()
            self._add_to_day(day, username, cost, prompt_tokens, completion_tokens, 0, category)
            self._persist()

        self._check_alerts(username, cost, model, "LLM")
        logger.info(
            "COST | user=%s model=%s category=%s prompt_tokens=%d "
            "completion_tokens=%d cost=$%.6f",
            username, model, category, prompt_tokens, completion_tokens, cost,
        )
        return cost

    def record_embedding(self, username: str, model: str, text: str) -> float:
        """
        Record an embedding call (token count derived from text via tiktoken).
        Returns the USD cost of this call.
        """
        if not COST_MONITORING_ENABLED:
            return 0.0

        tokens = _count_tokens_tiktoken(text, model)
        cost = _calc_cost(model, tokens, 0)

        with self._lock:
            day = self._ensure_day()
            self._add_to_day(day, username, cost, 0, 0, tokens, "embedding")
            self._persist()

        self._check_alerts(username, cost, model, "embedding")
        logger.info(
            "COST | user=%s model=%s embedding tokens=%d cost=$%.6f",
            username, model, tokens, cost,
        )
        return cost

    def get_daily_summary(self, date: str | None = None) -> dict:
        """Return the aggregate cost summary for a given date (default: today)."""
        date = date or _today()
        with self._lock:
            day = self._log.get(date, {})
        return {
            "date": date,
            "total_cost_usd": round(day.get("total_cost_usd", 0.0), 6),
            "total_prompt_tokens": day.get("total_prompt_tokens", 0),
            "total_completion_tokens": day.get("total_completion_tokens", 0),
            "total_embedding_tokens": day.get("total_embedding_tokens", 0),
            "total_calls": day.get("total_calls", 0),
            "users": {
                u: {
                    "cost_usd": round(v.get("cost_usd", 0.0), 6),
                    "calls": v.get("calls", 0),
                }
                for u, v in day.get("users", {}).items()
            },
        }

    def get_user_daily_cost(self, username: str, date: str | None = None) -> float:
        """Return the total USD cost for a specific user on a given day."""
        date = date or _today()
        with self._lock:
            return self._log.get(date, {}).get("users", {}).get(username, {}).get("cost_usd", 0.0)

    def get_total_daily_cost(self, date: str | None = None) -> float:
        """Return the aggregate USD cost across all users for a given day."""
        date = date or _today()
        with self._lock:
            return self._log.get(date, {}).get("total_cost_usd", 0.0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_day(self) -> dict:
        """Return (and create if needed) today's entry in the log. Must hold lock."""
        today = _today()
        if today not in self._log:
            self._log[today] = {
                "total_cost_usd": 0.0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_embedding_tokens": 0,
                "total_calls": 0,
                "users": {},
            }
        return self._log[today]

    def _add_to_day(
        self,
        day: dict,
        username: str,
        cost: float,
        prompt_tokens: int,
        completion_tokens: int,
        embedding_tokens: int,
        category: str,
    ) -> None:
        """Update day-level and user-level counters. Must hold lock."""
        day["total_cost_usd"]           += cost
        day["total_prompt_tokens"]      += prompt_tokens
        day["total_completion_tokens"]  += completion_tokens
        day["total_embedding_tokens"]   += embedding_tokens
        day["total_calls"]              += 1

        user_entry = day["users"].setdefault(username, {"cost_usd": 0.0, "calls": 0})
        user_entry["cost_usd"] += cost
        user_entry["calls"]    += 1

    def _check_alerts(self, username: str, call_cost: float, model: str, call_type: str) -> None:
        """Fire WARNING-level alerts when any configured threshold is breached."""
        # Per-request threshold
        if call_cost >= COST_ALERT_PER_REQUEST_USD:
            logger.warning(
                "COST ALERT | Single %s call exceeded threshold: "
                "user=%s model=%s cost=$%.4f threshold=$%.4f",
                call_type, username, model, call_cost, COST_ALERT_PER_REQUEST_USD,
            )

        # Per-user daily threshold
        user_day_cost = self.get_user_daily_cost(username)
        if user_day_cost >= COST_ALERT_PER_USER_DAY_USD:
            logger.warning(
                "COST ALERT | User daily spend exceeded threshold: "
                "user=%s daily_cost=$%.4f threshold=$%.4f",
                username, user_day_cost, COST_ALERT_PER_USER_DAY_USD,
            )

        # Total daily threshold
        total_day_cost = self.get_total_daily_cost()
        if total_day_cost >= COST_ALERT_TOTAL_DAY_USD:
            logger.warning(
                "COST ALERT | Total daily spend exceeded threshold: "
                "total_cost=$%.4f threshold=$%.4f",
                total_day_cost, COST_ALERT_TOTAL_DAY_USD,
            )

    def _load(self) -> dict:
        """Load persisted cost log from disk. Returns empty dict on first run."""
        path = Path(COST_LOG_FILE)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("Failed to load cost log from %s: %s", COST_LOG_FILE, exc)
        return {}

    def _persist(self) -> None:
        """Write current log to disk. Must hold lock."""
        try:
            with open(COST_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._log, f, indent=2)
        except OSError as exc:
            logger.error("Failed to persist cost log to %s: %s", COST_LOG_FILE, exc)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
cost_monitor = CostMonitor()
