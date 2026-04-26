"""
prompts.py — Centralized, versioned prompt registry.

Every LLM-facing instruction string lives here and nowhere else.
Each prompt carries explicit version metadata so that changes are
auditable, rollbackable, and visible in eval logs.

Versioning convention: <major>.<minor>
  major — semantic change that materially alters model behaviour
  minor — wording / formatting tweak with no behavioural intent change

Adding a new prompt
-------------------
1. Define the raw template string (plain text, no f-strings).
2. Create a PromptSpec entry in PROMPT_REGISTRY with a unique key.
3. Call build_prompt(key) wherever a LangChain PromptTemplate is needed.
4. The version is automatically carried into logs via prompt_version(key).

Never hard-code prompt text in pipeline or handler modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from langchain_core.prompts import PromptTemplate


# ---------------------------------------------------------------------------
# Registry metadata
# ---------------------------------------------------------------------------

REGISTRY_VERSION = "1.1.0"
"""
Bump this when any prompt in the registry changes.
Recorded in evaluation metadata so every RAGAS run is traceable to a
specific set of prompt instructions.

Changelog
---------
1.0.0 — initial registry; rag_answer v1.0, scope_classifier v1.0
1.1.0 — rag_answer v2.0: citation-enforcement rules added; model must
         decline explicitly when context does not support the answer.
"""


# ---------------------------------------------------------------------------
# PromptSpec — immutable prompt descriptor
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PromptSpec:
    """
    Immutable descriptor for a single prompt template.

    Attributes
    ----------
    name            Human-readable identifier (matches registry key).
    version         Semantic version string, e.g. "2.0".
    description     What this prompt does and when it is used.
    input_variables Variables the template expects (validated by LangChain).
    template        Raw prompt string using {variable} placeholders.
    """
    name: str
    version: str
    description: str
    input_variables: list[str]
    template: str

    def build(self) -> PromptTemplate:
        """Instantiate a LangChain PromptTemplate from this spec."""
        return PromptTemplate(
            template=self.template,
            input_variables=self.input_variables,
        )


# ---------------------------------------------------------------------------
# Template strings (keep these readable — one concern per block)
# ---------------------------------------------------------------------------

# -- RAG Answer prompt  (v2.0 — citation enforcement) -----------------------
#
# Design rationale
# ----------------
# v1.0 said "if the question cannot be answered from documents, inform the
# user" — too soft. Models would still hallucinate plausible-sounding answers.
#
# v2.0 introduces explicit, numbered citation rules and a mandated verbatim
# refusal phrase. The refusal phrase is known to the pipeline so it can be
# detected, logged as [CITATION_DECLINE], and surfaced correctly in the UI
# rather than presented as a genuine answer.
#
# The phrase "CITATION_DECLINE_SIGNAL" below is intentional: rag_pipeline.py
# checks answer_text against CITATION_DECLINE_PREFIX to detect declines.
# If you change the refusal wording here, update that constant too.

_RAG_ANSWER_TEMPLATE = """\
You are a {category_name} customer service specialist at a bank.
Your ONLY source of information is the Document Context section below.

CITATION RULES — follow these without exception:
1. Answer ONLY using facts explicitly stated in the Document Context.
2. Do NOT use outside knowledge, training data, or general financial knowledge.
3. When stating fees, rates, percentages, or dates, quote them verbatim from \
the context — do not round, paraphrase, or approximate.
4. If the context partially addresses the question, answer only the supported \
parts and clearly state: "I do not have document support for the remaining \
part of your question."
5. If the context does not contain sufficient information to answer the \
question at all, respond with EXACTLY this phrase and nothing else:
   "I'm sorry, I cannot find information about that in the {category_name} \
documents provided to me. Please contact our support team for further \
assistance."
6. Do NOT speculate, extrapolate, or assume anything not present in the context.

--- {category_name} Document Context ---
{context}
--- End of Context ---

Customer Question: {question}

Answer (cite only from the context above):"""


# -- Scope classifier prompt  (v1.0) ----------------------------------------
#
# Design rationale
# ----------------
# Single-token output (RELEVANT / IRRELEVANT) keeps latency and cost minimal.
# The prompt is intentionally terse — LLMs perform well on binary classifiers
# when the categories are unambiguous and the examples are crisp.

_SCOPE_CLASSIFIER_TEMPLATE = """\
You are a strict topic classifier for a banking assistant.
The assistant can ONLY answer questions about: {categories}.

Question: {question}

Reply with exactly one word: RELEVANT or IRRELEVANT.
- RELEVANT: the question is clearly about banking, loans, credit cards, \
account management, or financial products.
- IRRELEVANT: the question has nothing to do with banking or finance.

Classification:"""


# ---------------------------------------------------------------------------
# Prompt registry
# ---------------------------------------------------------------------------

PROMPT_REGISTRY: dict[str, PromptSpec] = {

    # ------------------------------------------------------------------ #
    #  rag_answer                                                          #
    #  Main question-answering prompt used by RAGPipeline.query()         #
    # ------------------------------------------------------------------ #
    "rag_answer": PromptSpec(
        name="rag_answer",
        version="2.0",
        description=(
            "Category-scoped RAG answer prompt with citation enforcement. "
            "Instructs the model to answer exclusively from retrieved document "
            "context and to emit a fixed refusal phrase when the context does "
            "not support the question, preventing hallucination."
        ),
        input_variables=["category_name", "context", "question"],
        template=_RAG_ANSWER_TEMPLATE,
    ),

    # ------------------------------------------------------------------ #
    #  scope_classifier                                                    #
    #  Guardrail: classifies whether a question is in-scope for banking   #
    # ------------------------------------------------------------------ #
    "scope_classifier": PromptSpec(
        name="scope_classifier",
        version="1.0",
        description=(
            "Binary topic classifier. Returns RELEVANT when the question is "
            "about banking/finance, IRRELEVANT otherwise. Used by Guardrails "
            "to block off-topic requests before they reach the RAG pipeline."
        ),
        input_variables=["categories", "question"],
        template=_SCOPE_CLASSIFIER_TEMPLATE,
    ),
}


# ---------------------------------------------------------------------------
# The refusal prefix the RAG answer prompt emits on citation decline.
# rag_pipeline.py checks answer_text against this to detect and log declines.
# Keep this in sync with rule 5 in _RAG_ANSWER_TEMPLATE.
# ---------------------------------------------------------------------------
CITATION_DECLINE_PREFIX = "I'm sorry, I cannot find information about that"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def build_prompt(key: str) -> PromptTemplate:
    """
    Return a LangChain PromptTemplate for the given registry key.

    Raises KeyError for unknown keys so callers fail fast at startup rather
    than silently using an empty or wrong prompt.
    """
    if key not in PROMPT_REGISTRY:
        raise KeyError(
            f"Unknown prompt key '{key}'. "
            f"Available keys: {sorted(PROMPT_REGISTRY)}"
        )
    return PROMPT_REGISTRY[key].build()


def prompt_version(key: str) -> str:
    """Return the version string for a registry key (for logging/metadata)."""
    if key not in PROMPT_REGISTRY:
        raise KeyError(f"Unknown prompt key '{key}'.")
    return PROMPT_REGISTRY[key].version


def prompt_metadata(key: str) -> dict:
    """
    Return a JSON-serialisable metadata dict for a prompt.
    Useful for attaching to eval logs so every RAGAS run records exactly
    which prompt version produced the answer being scored.
    """
    spec = PROMPT_REGISTRY[key]
    return {
        "key": key,
        "version": spec.version,
        "registry_version": REGISTRY_VERSION,
    }
