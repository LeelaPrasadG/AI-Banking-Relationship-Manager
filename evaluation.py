"""
RAGAS Evaluation Framework – Banking RAG System.

Metric matrix:
  ┌──────────────────────────┬─────────────────┬─────────────────────┬───────────────────────────────────────┐
  │ Metric                   │ Evaluates       │ Needs               │ Key Question                          │
  ├──────────────────────────┼─────────────────┼─────────────────────┼───────────────────────────────────────┤
  │ Faithfulness             │ Generator       │ question, answer,   │ Is the answer grounded in context?    │
  │                          │                 │ contexts            │                                       │
  │ Answer Relevancy         │ Generator       │ question, answer,   │ Does the answer address the question? │
  │                          │                 │ contexts            │                                       │
  │ Context Precision        │ Retriever       │ + ground_truth      │ Are relevant chunks ranked at top?    │
  │ Context Recall           │ Retriever       │ + ground_truth      │ Did we retrieve all necessary info?   │
  │ Context Entity Recall    │ Retriever       │ + ground_truth      │ Did we retrieve all key entities?     │
  │ Noise Sensitivity        │ System          │ + ground_truth      │ Does noise cause wrong answers?       │
  └──────────────────────────┴─────────────────┴─────────────────────┴───────────────────────────────────────┘

Metrics 1-2 run on every evaluation request.
Metrics 3-6 additionally require a `ground_truth` reference answer.

Note: RAGAS makes its own LLM calls to score metrics; these are not tracked by cost_monitor.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

EVAL_LOG_FILE = 'eval_log.json'

# ---------------------------------------------------------------------------
# Graceful import – evaluation is optional; app starts fine without ragas
# ---------------------------------------------------------------------------
try:
    import warnings as _warnings
    from ragas import evaluate
    from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
    # Use the legacy ragas.metrics API (Metric subclasses) which is compatible
    # with ragas.evaluate() and accepts LangchainLLMWrapper / LangchainEmbeddingsWrapper.
    # The ragas.metrics.collections API uses a different base class (BaseMetric)
    # that ragas.evaluate() does NOT accept.
    with _warnings.catch_warnings():
        _warnings.filterwarnings('ignore', category=DeprecationWarning)
        from ragas.metrics import (
            Faithfulness,
            AnswerRelevancy,
            ContextPrecision,
            ContextRecall,
            ContextEntityRecall,
            NoiseSensitivity,
        )
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    RAGAS_AVAILABLE = True
    logger.info("[EVAL] ragas loaded successfully")
except ImportError as _import_exc:
    RAGAS_AVAILABLE = False
    logger.warning("[EVAL] ragas not available – evaluation disabled (%s)", _import_exc)


class RAGASEvaluator:
    """
    Evaluates a single RAG query/answer pair using RAGAS metrics.

    Parameters
    ----------
    llm : BaseChatModel
        LangChain chat model (reuses the pipeline's existing LLM).
    embeddings : Embeddings
        LangChain embedding model (reuses the pipeline's existing embeddings).
    """

    # Columns that appear in ragas result DataFrames but are NOT metric scores
    _NON_METRIC_COLS = {
        'user_input', 'response', 'retrieved_contexts',
        'reference', 'reference_contexts',
    }

    def __init__(self, llm, embeddings):
        if not RAGAS_AVAILABLE:
            raise RuntimeError(
                "ragas is not installed. Run: pip install 'ragas>=0.2.0'"
            )
        # Create a dedicated LLM instance for RAGAS with a high max_tokens.
        # Faithfulness verification outputs JSON for every statement × context chunk
        # and can exceed the pipeline LLM's max_tokens. A separate instance avoids
        # changing the pipeline's token budget.
        from langchain_openai import ChatOpenAI as _ChatOpenAI
        from config import GROQ_API_KEY, XAI_BASE_URL, RAGAS_EVAL_MODEL
        _ragas_chat_llm = _ChatOpenAI(
            api_key=GROQ_API_KEY,
            base_url=XAI_BASE_URL,
            model=RAGAS_EVAL_MODEL,
            temperature=0.0,
            max_tokens=8000,
        )
        self._ragas_llm = LangchainLLMWrapper(_ragas_chat_llm)
        self._ragas_emb = LangchainEmbeddingsWrapper(embeddings)
        logger.info("[EVAL] RAGASEvaluator initialised (eval_model=%s)", RAGAS_EVAL_MODEL)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        question: str,
        answer: str,
        contexts: list[str],
        ground_truth: Optional[str] = None,
        username: str = "__unknown__",
        role: str = "__unknown__",
    ) -> dict:
        """
        Run RAGAS evaluation for one QA sample.

        Parameters
        ----------
        question     : The user's question (post-PII-redaction).
        answer       : The LLM's final answer (post-output-guardrail).
        contexts     : Retrieved (and optionally re-ranked) chunk texts.
        ground_truth : Reference answer supplied by the caller.  When
                       omitted, metrics 3-6 are skipped.
        username     : Logged for audit trail.
        role         : Category being evaluated (e.g. 'credit-card').

        Returns
        -------
        {
            "success"         : bool,
            "scores"          : {"faithfulness": 0.95, ...},
            "metrics_run"     : ["Faithfulness", ...],
            "has_ground_truth": bool,
            "error"           : str   # only present on failure
        }
        """
        has_gt = bool(ground_truth)
        logger.info(
            "[EVAL] start  user='%s' role='%s' contexts=%d ground_truth=%s",
            username, role, len(contexts), "yes" if has_gt else "no",
        )

        sample = SingleTurnSample(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
            reference=ground_truth if has_gt else None,
        )
        dataset = EvaluationDataset(samples=[sample])

        # --- build metric list ----------------------------------------
        # ragas 0.4.x: llm (and embeddings for AnswerRelevancy) must be
        # passed directly to each metric constructor.
        metrics = [
            Faithfulness(llm=self._ragas_llm),
            # strictness=1 → single LLM call (n=1). Groq rejects n > 1.
            AnswerRelevancy(llm=self._ragas_llm, embeddings=self._ragas_emb, strictness=1),
        ]
        if has_gt:
            metrics += [
                ContextPrecision(llm=self._ragas_llm),
                ContextRecall(llm=self._ragas_llm),
                ContextEntityRecall(llm=self._ragas_llm),
                NoiseSensitivity(llm=self._ragas_llm),
            ]
        else:
            logger.info(
                "[EVAL] ContextPrecision / ContextRecall / ContextEntityRecall "
                "/ NoiseSensitivity skipped – no ground_truth provided"
            )

        metric_names = [m.__class__.__name__ for m in metrics]
        logger.info("[EVAL] running %d metric(s): %s", len(metrics), metric_names)

        # --- execute --------------------------------------------------
        try:
            result = evaluate(
                dataset=dataset,
                metrics=metrics,
            )
            scores = self._extract_scores(result)

            logger.info("[EVAL] results for user='%s' role='%s':", username, role)
            for metric, score in scores.items():
                logger.info("[EVAL]   %-32s = %.4f", metric, score)

            self._persist(username, role, question, scores, has_gt)
            return {
                "success": True,
                "scores": {k: round(v, 4) for k, v in scores.items()},
                "metrics_run": metric_names,
                "has_ground_truth": has_gt,
            }

        except Exception as exc:
            logger.error(
                "[EVAL] failed user='%s' role='%s': %s",
                username, role, exc, exc_info=True,
            )
            return {
                "success": False,
                "error": str(exc),
                "scores": {},
                "metrics_run": metric_names,
                "has_ground_truth": has_gt,
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_scores(self, result) -> dict[str, float]:
        """Pull numeric metric scores from a RAGAS EvaluationResult."""
        # RAGAS 0.2+: result.scores is a list of per-sample dicts
        if hasattr(result, 'scores') and result.scores:
            return {
                k: float(v)
                for k, v in result.scores[0].items()
                if isinstance(v, (int, float)) and k not in self._NON_METRIC_COLS
            }
        # Fallback: result is a DataFrame-backed object (RAGAS 0.1 / older 0.2)
        if hasattr(result, 'to_pandas'):
            row = result.to_pandas().iloc[0].to_dict()
            return {
                k: float(v)
                for k, v in row.items()
                if isinstance(v, (int, float)) and k not in self._NON_METRIC_COLS
            }
        return {}

    def _persist(
        self,
        username: str,
        role: str,
        question: str,
        scores: dict[str, float],
        has_ground_truth: bool,
    ) -> None:
        """Append evaluation entry to eval_log.json."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "username": username,
            "role": role,
            "question_preview": question[:120],
            "has_ground_truth": has_ground_truth,
            "scores": {k: round(v, 4) for k, v in scores.items()},
        }
        try:
            log: list = []
            if os.path.exists(EVAL_LOG_FILE):
                with open(EVAL_LOG_FILE, 'r') as f:
                    log = json.load(f)
            log.append(entry)
            with open(EVAL_LOG_FILE, 'w') as f:
                json.dump(log, f, indent=2)
            logger.info(
                "[EVAL] persisted to %s (total entries: %d)", EVAL_LOG_FILE, len(log)
            )
        except Exception as exc:
            logger.warning("[EVAL] could not persist result: %s", exc)
