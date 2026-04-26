from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from prompts import build_prompt, prompt_version, prompt_metadata, CITATION_DECLINE_PREFIX
from pinecone import Pinecone
from config import OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME, OPENAI_MODEL
from config import GROQ_API_KEY, XAI_BASE_URL
from config import GUARDRAIL_LLM_SCOPE_CHECK_ENABLED, GUARDRAIL_LOG_LEVEL, LOG_LEVEL
from config import COHERE_API_KEY, COHERE_RERANK_MODEL
import cohere
from evaluation import RAGASEvaluator, RAGAS_AVAILABLE
from cost_monitor import cost_monitor
from auth import user_has_role
import json
import os
import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
# Guardrail sub-logger respects its own level setting
logging.getLogger('guardrail').setLevel(getattr(logging, GUARDRAIL_LOG_LEVEL, logging.WARNING))

# ---------------------------------------------------------------------------
# PII patterns — compiled once at module load
# ---------------------------------------------------------------------------
_PII_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    # (label, pattern, replacement)
    ("SSN",         re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),                          "[SSN REDACTED]"),
    ("SSN_NODASH",  re.compile(r'\b\d{9}\b'),                                       "[SSN REDACTED]"),
    ("CARD_16",     re.compile(r'\b(?:\d[ -]?){13,16}\b'),                          "[CARD NUMBER REDACTED]"),
    ("ACCOUNT",     re.compile(r'\b(?:account|acct|acc)[\s#:]*\d{6,17}\b', re.I),  "[ACCOUNT NUMBER REDACTED]"),
    ("ROUTING",     re.compile(r'\b(?:routing|aba)[\s#:]*\d{9}\b', re.I),          "[ROUTING NUMBER REDACTED]"),
    ("EMAIL",       re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'), "[EMAIL REDACTED]"),
    ("PHONE",       re.compile(r'\b(?:\+1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b'), "[PHONE REDACTED]"),
    ("DOB",         re.compile(r'\b(?:0?[1-9]|1[0-2])[/\-](?:0?[1-9]|[12]\d|3[01])[/\-](?:19|20)\d{2}\b'), "[DOB REDACTED]"),
    ("ZIP",         re.compile(r'\b\d{5}(?:-\d{4})?\b'),                           "[ZIP REDACTED]"),
    ("IP_ADDR",     re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),                    "[IP REDACTED]"),
]

# ---------------------------------------------------------------------------
# In-scope topic keywords for fast pre-filter
# ---------------------------------------------------------------------------
_BANKING_KEYWORDS = re.compile(
    r'\b(loan|mortgage|credit|debit|card|account|bank|interest|rate|payment|'
    r'balance|transfer|deposit|withdraw|fee|apr|fico|score|finance|borrow|'
    r'lend|collateral|equity|refinanc|statement|transaction|fraud|dispute|'
    r'limit|reward|cashback|overdraft|savings|checking|routing|swift|iban|'
    r'insurance|premium|escrow|amortiz|principal|minimum|due|billing)\b',
    re.I
)

@dataclass
class GuardrailResult:
    """Result returned by each guardrail check."""
    passed: bool
    reason: str = ""
    modified_text: str = ""
    pii_found: list[str] = field(default_factory=list)

class Guardrails:
    """
    Two-layer guardrail system:
      1. PII Redaction  – scrub sensitive data from input and output.
      2. Scope Detection – reject questions outside the banking domain.
    """

    # Topics that are clearly out-of-scope for a banking assistant
    _OUT_OF_SCOPE_TOPICS = re.compile(
        r'\b(recipe|cook|sport|game|movie|music|weather|politics|election|'
        r'celebrity|travel|flight|hotel|relationship|dating|health|medical|'
        r'diagnos|symptom|drug|medicine|homework|essay|poem|code|program|'
        r'hacking|exploit|malware|virus|weapon|hack)\b',
        re.I
    )

    def __init__(self, llm: ChatOpenAI):
        self._llm = llm
        self._scope_prompt = build_prompt("scope_classifier")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_input(self, question: str, user_roles: list[str]) -> GuardrailResult:
        """
        Run all input guardrails.
        Returns GuardrailResult with:
          - passed=False if question should be blocked
          - modified_text with PII redacted (safe version to embed/log)
        """
        # 1. Redact PII from the question before any further processing
        redacted, pii_types = self._redact_pii(question)

        if pii_types:
            logger.warning("PII detected in question from user – types: %s", pii_types)

        # 2. Scope check
        scope = self._check_scope(redacted, user_roles)
        if not scope.passed:
            return GuardrailResult(
                passed=False,
                reason=scope.reason,
                modified_text=redacted,
                pii_found=pii_types,
            )

        return GuardrailResult(
            passed=True,
            modified_text=redacted,
            pii_found=pii_types,
        )

    def check_output(self, answer: str) -> GuardrailResult:
        """
        Redact any PII that may have leaked into the LLM answer.
        Always passes – just sanitises the text.
        """
        redacted, pii_types = self._redact_pii(answer)
        if pii_types:
            logger.warning("PII detected in LLM output – redacted types: %s", pii_types)
        return GuardrailResult(passed=True, modified_text=redacted, pii_found=pii_types)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _redact_pii(self, text: str) -> tuple[str, list[str]]:
        """Apply all PII patterns and return (redacted_text, list_of_matched_labels)."""
        found: list[str] = []
        result = text
        for label, pattern, replacement in _PII_PATTERNS:
            new_result, count = pattern.subn(replacement, result)
            if count:
                found.append(label)
                result = new_result
        return result, found

    def _check_scope(self, question: str, user_roles: list[str]) -> GuardrailResult:
        """
        Two-stage scope check:
          Stage 1 – fast regex: if keywords clearly match, pass immediately.
          Stage 2 – if ambiguous or clearly off-topic keywords found, call LLM classifier.
        """
        has_banking_kw = bool(_BANKING_KEYWORDS.search(question))
        has_oos_kw     = bool(self._OUT_OF_SCOPE_TOPICS.search(question))

        # Fast pass: banking keywords present and no out-of-scope signal
        if has_banking_kw and not has_oos_kw:
            return GuardrailResult(passed=True)

        # Fast fail: explicit out-of-scope topic with no banking context
        if has_oos_kw and not has_banking_kw:
            return GuardrailResult(
                passed=False,
                reason=(
                    "I can only assist with banking and financial product questions. "
                    "Your question appears to be outside that scope."
                ),
            )

        # Ambiguous — delegate to LLM classifier (if enabled)
        if GUARDRAIL_LLM_SCOPE_CHECK_ENABLED:
            return self._llm_scope_check(question, user_roles)

        # LLM check disabled — default allow for ambiguous cases
        return GuardrailResult(passed=True)

    def _llm_scope_check(self, question: str, user_roles: list[str]) -> GuardrailResult:
        """Call the LLM to classify question relevance."""
        categories = ", ".join(
            {"auto-loan": "Auto Loans", "credit-card": "Credit Cards", "banking": "Banking"}.get(r, r)
            for r in user_roles
        )
        try:
            prompt_text = self._scope_prompt.format(question=question, categories=categories)
            response = self._llm.invoke(prompt_text)
            classification = (
                response.content if hasattr(response, "content") else str(response)
            ).strip().upper()

            # Track cost of this classifier call (attributed to __guardrail__ user)
            usage = getattr(response, 'usage_metadata', None)
            if usage:
                pt = usage.get('input_tokens', 0)
                ct = usage.get('output_tokens', 0)
            elif hasattr(response, 'response_metadata'):
                tu = response.response_metadata.get('token_usage', {})
                pt = tu.get('prompt_tokens', 0)
                ct = tu.get('completion_tokens', 0)
            else:
                pt = ct = 0
            cost_monitor.record_llm_call('__guardrail__', OPENAI_MODEL, pt, ct, 'scope-check')

            if classification.startswith("IRRELEVANT"):
                return GuardrailResult(
                    passed=False,
                    reason=(
                        "I can only assist with banking and financial product questions "
                        f"({categories}). Your question appears to be outside that scope."
                    ),
                )
            return GuardrailResult(passed=True)
        except Exception as exc:
            # On classifier failure, default to allow (fail-open) and log
            logger.error("Scope-check LLM call failed: %s – defaulting to allow", exc)
            return GuardrailResult(passed=True)


class RAGPipeline:
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError('GROQ_API_KEY is not set. Please check your .env file')
        if not OPENAI_API_KEY:
            raise ValueError('OPENAI_API_KEY is not set (required for embeddings). Please check your .env file')

        # LLM: xAI Grok via OpenAI-compatible API
        self.llm = ChatOpenAI(
            api_key=GROQ_API_KEY,
            base_url=XAI_BASE_URL,
            model=OPENAI_MODEL,
            temperature=0.3,
            max_tokens=1000
        )
        # Embeddings: OpenAI (xAI has no embedding models)
        self.embedding_query = OpenAIEmbeddings(
            api_key=OPENAI_API_KEY,
            model='text-embedding-3-small'
        )
        self.index_name = PINECONE_INDEX_NAME
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=PINECONE_API_KEY)
        self.index = self.pc.Index(self.index_name)

        # Cohere re-ranker (optional – disabled when COHERE_API_KEY is absent)
        if COHERE_API_KEY:
            self.cohere_client = cohere.ClientV2(api_key=COHERE_API_KEY)
            logger.info("[INIT] Cohere re-ranker enabled (model=%s)", COHERE_RERANK_MODEL)
        else:
            self.cohere_client = None
            logger.warning("[INIT] COHERE_API_KEY not set – re-ranking disabled")

        # Guardrails
        self.guardrails = Guardrails(self.llm)

        # RAGAS evaluator (optional – disabled when ragas is not installed)
        if RAGAS_AVAILABLE:
            try:
                self.evaluator = RAGASEvaluator(self.llm, self.embedding_query)
            except Exception as _eval_err:
                self.evaluator = None
                logger.warning("[INIT] RAGAS evaluator init failed: %s", _eval_err)
        else:
            self.evaluator = None
            logger.warning("[INIT] RAGAS not installed – evaluation disabled")
    
    def _get_category_name(self, category):
        """Convert category code to readable name"""
        names = {
            'auto-loan': 'Auto Loan',
            'credit-card': 'Credit Card',
            'banking': 'Banking'
        }
        return names.get(category, category)
    
    def query(self, question, username, user_roles, ground_truth=None, run_eval=False):
        """
        Query the RAG system with role-based access control and guardrails.
        Guardrails applied:
          - Input:  PII redaction, out-of-scope detection
          - Output: PII redaction on LLM answers
        Optional RAGAS evaluation:
          - run_eval=True  triggers per-category RAGAS scoring.
          - ground_truth   unlocks the full 6-metric suite; without it only
            Faithfulness and Answer Relevancy are scored.
        """
        logger.info(
            "[REQUEST] user='%s' roles=%s question='%.100s%s'",
            username, user_roles, question, '...' if len(question) > 100 else ''
        )

        if not user_roles:
            logger.warning("[REQUEST] user='%s' has no assigned roles – aborting", username)
            return {
                'success': False,
                'answer': 'Error: User has no assigned roles.',
                'sources': [],
                'allowed_categories': []
            }

        # ------------------------------------------------------------------
        # INPUT GUARDRAIL
        # ------------------------------------------------------------------
        logger.info("[GUARDRAIL:INPUT] running PII + scope checks for user='%s'", username)
        input_check = self.guardrails.check_input(question, user_roles)

        if input_check.pii_found:
            # Use the redacted version for all downstream processing
            question = input_check.modified_text
            logger.info(
                "[GUARDRAIL:INPUT] PII redacted for user='%s' types=%s",
                username, input_check.pii_found
            )

        if not input_check.passed:
            logger.info(
                "[GUARDRAIL:INPUT] BLOCKED for user='%s' reason='%s'",
                username, input_check.reason
            )
            return {
                'success': False,
                'guardrail_blocked': True,
                'answer': input_check.reason,
                'sources': [],
                'allowed_categories': [self._get_category_name(r) for r in user_roles],
            }

        logger.info("[GUARDRAIL:INPUT] passed for user='%s'", username)

        try:
            # Get embedding for the question
            logger.info("[EMBEDDING] generating query embedding for user='%s'", username)
            question_embedding = self.embedding_query.embed_query(question)
            cost_monitor.record_embedding(username, 'text-embedding-3-small', question)
            logger.debug("[EMBEDDING] done for user='%s'", username)

            # Collect results from all user's roles
            answers_by_category = {}
            request_total_cost = 0.0
            
            for role in user_roles:
                category_name = self._get_category_name(role)
                logger.info(
                    "[VECTOR_SEARCH] user='%s' role='%s' querying Pinecone (top_k=4, filter=category)",
                    username, role
                )
                
                # Query Pinecone directly for this role
                try:
                    # Query with metadata filter for the category
                    query_result = self.index.query(
                        vector=question_embedding,
                        top_k=4,
                        filter={"category": {"$eq": role}},
                        include_metadata=True
                    )
                except Exception as filter_error:
                    # If filtering fails, query without filter and filter manually
                    logger.warning(
                        "[VECTOR_SEARCH] filter query failed for role='%s', retrying without filter: %s",
                        role, filter_error
                    )
                    query_result = self.index.query(
                        vector=question_embedding,
                        top_k=10,
                        include_metadata=True
                    )
                
                # Extract documents from Pinecone results
                docs_by_category = []
                retrieved_chunks = []
                
                if query_result and query_result.get('matches'):
                    for match in query_result['matches']:
                        metadata = match.get('metadata', {})
                        if metadata.get('category') == role or not filter_error:
                            retrieved_chunks.append({
                                'text': metadata.get('text', ''),
                                'filename': metadata.get('filename', 'Unknown'),
                                'category': metadata.get('category', 'Unknown'),
                                'score': match.get('score', 0)
                            })
                            if len(retrieved_chunks) >= 4:
                                break
                
                # If filter was applied automatically, limit to role
                if 'filter_error' in locals():
                    retrieved_chunks = [c for c in retrieved_chunks if c['category'] == role][:4]
                
                logger.info(
                    "[VECTOR_SEARCH] user='%s' role='%s' retrieved %d chunks",
                    username, role, len(retrieved_chunks)
                )
                if retrieved_chunks:
                    for i, c in enumerate(retrieved_chunks, 1):
                        logger.info(
                            "[VECTOR_SEARCH]   #%d  file='%s'  category='%s'  vector_score=%.4f  "
                            "text_preview='%.80s'",
                            i, c['filename'], c['category'], c['score'],
                            c['text'].replace('\n', ' ')
                        )

                # ----------------------------------------------------------
                # COHERE RE-RANKING
                # ----------------------------------------------------------
                if self.cohere_client and retrieved_chunks:
                    logger.info(
                        "[RERANK] user='%s' role='%s' re-ranking %d chunks with model=%s",
                        username, role, len(retrieved_chunks), COHERE_RERANK_MODEL
                    )
                    try:
                        rerank_response = self.cohere_client.rerank(
                            model=COHERE_RERANK_MODEL,
                            query=question,
                            documents=[c['text'] for c in retrieved_chunks],
                            top_n=len(retrieved_chunks),
                        )
                        # Reorder chunks by Cohere relevance score (descending)
                        reranked = sorted(
                            [
                                {
                                    **retrieved_chunks[r.index],
                                    'rerank_score': r.relevance_score,
                                }
                                for r in rerank_response.results
                            ],
                            key=lambda c: c['rerank_score'],
                            reverse=True,
                        )
                        logger.info(
                            "[RERANK] user='%s' role='%s' re-ranked %d chunks:",
                            username, role, len(reranked)
                        )
                        for i, c in enumerate(reranked, 1):
                            logger.info(
                                "[RERANK]   #%d  file='%s'  rerank_score=%.4f  "
                                "vector_score=%.4f  text_preview='%.80s'",
                                i, c['filename'], c['rerank_score'], c['score'],
                                c['text'].replace('\n', ' ')
                            )
                        retrieved_chunks = reranked
                    except Exception as rerank_error:
                        logger.warning(
                            "[RERANK] failed for user='%s' role='%s', using original order: %s",
                            username, role, rerank_error
                        )

                # Extract context from chunks
                context = "\n---\n".join([
                    chunk['text'] for chunk in retrieved_chunks
                ]) if retrieved_chunks else "No relevant documents found."
                
                # Create prompt and get answer (versioned, citation-enforced)
                prompt = build_prompt("rag_answer")
                formatted_prompt = prompt.format(
                    category_name=category_name,
                    context=context,
                    question=question,
                )
                logger.info(
                    "[PROMPT] user='%s' role='%s' prompt=rag_answer@v%s:\n%s",
                    username, role, prompt_version("rag_answer"), formatted_prompt
                )
                # Get LLM response
                logger.info(
                    "[LLM] invoking model='%s' for user='%s' role='%s'",
                    OPENAI_MODEL, username, role
                )
                try:
                    response = self.llm.invoke(formatted_prompt)
                    answer_text = response.content if hasattr(response, 'content') else str(response)

                    # Extract token usage from response metadata
                    prompt_tokens = completion_tokens = 0
                    usage = getattr(response, 'usage_metadata', None)
                    if usage:
                        prompt_tokens     = usage.get('input_tokens', 0)
                        completion_tokens = usage.get('output_tokens', 0)
                    elif hasattr(response, 'response_metadata'):
                        tu = response.response_metadata.get('token_usage', {})
                        prompt_tokens     = tu.get('prompt_tokens', 0)
                        completion_tokens = tu.get('completion_tokens', 0)

                    call_cost = cost_monitor.record_llm_call(
                        username, OPENAI_MODEL, prompt_tokens, completion_tokens, role
                    )
                    request_total_cost += call_cost
                    logger.info(
                        "[LLM] response for user='%s' role='%s' prompt_tokens=%d "
                        "completion_tokens=%d cost=$%.6f",
                        username, role, prompt_tokens, completion_tokens, call_cost
                    )

                except Exception as llm_error:
                    logger.error(
                        "[LLM] error for user='%s' role='%s': %s",
                        username, role, llm_error, exc_info=True
                    )
                    answer_text = f"Error getting response: {str(llm_error)}"

                # ----------------------------------------------------------
                # CITATION DECLINE DETECTION
                # ----------------------------------------------------------
                if answer_text.strip().startswith(CITATION_DECLINE_PREFIX):
                    logger.warning(
                        "[CITATION_DECLINE] user='%s' role='%s' — model declined: "
                        "retrieved context did not support the question. "
                        "prompt=rag_answer@v%s",
                        username, role, prompt_version("rag_answer"),
                    )

                # ----------------------------------------------------------
                # OUTPUT GUARDRAIL – redact any PII that leaked into answer
                # ----------------------------------------------------------
                logger.debug(
                    "[GUARDRAIL:OUTPUT] checking answer for user='%s' role='%s'",
                    username, role
                )
                output_check = self.guardrails.check_output(answer_text)
                if output_check.pii_found:
                    logger.warning(
                        "[GUARDRAIL:OUTPUT] PII redacted for user='%s' role='%s' types=%s",
                        username, role, output_check.pii_found
                    )
                    answer_text = output_check.modified_text
                else:
                    logger.debug(
                        "[GUARDRAIL:OUTPUT] passed for user='%s' role='%s'",
                        username, role
                    )
                
                answers_by_category[category_name] = {
                    'answer': answer_text,
                    'evaluation': None,
                    # 'sources': [...]
                }

                # ----------------------------------------------------------
                # RAGAS EVALUATION (optional, per-category)
                # ----------------------------------------------------------
                if run_eval:
                    if self.evaluator:
                        logger.info(
                            "[EVAL] triggering RAGAS evaluation for user='%s' role='%s'",
                            username, role
                        )
                        # Limit to top 2 contexts for RAGAS — Groq free tier
                        # caps gpt-oss-120b at 8000 tokens/request; 4 full chunks
                        # exceed that. Top 2 (highest rerank scores) are sufficient
                        # for faithful scoring.
                        eval_contexts = [c['text'] for c in retrieved_chunks[:2]]
                        eval_result = self.evaluator.evaluate(
                            question=question,
                            answer=answer_text,
                            contexts=eval_contexts,
                            ground_truth=ground_truth,
                            username=username,
                            role=role,
                            prompt_meta=prompt_metadata("rag_answer"),
                        )
                        answers_by_category[category_name]['evaluation'] = eval_result
                    else:
                        logger.warning(
                            "[EVAL] evaluation requested but evaluator not available "
                            "for user='%s' role='%s'",
                            username, role
                        )
                        answers_by_category[category_name]['evaluation'] = {
                            'success': False,
                            'error': 'RAGAS evaluator not available (check installation)',
                            'scores': {},
                        }
            
            # Prepare response
            response_data = {
                'success': True,
                'allowed_categories': [self._get_category_name(r) for r in user_roles],
                'answers_by_category': answers_by_category,
                'username': username,
                'cost_usd': round(request_total_cost, 6),
            }
            
            # If only one role, provide simplified response
            if len(user_roles) == 1:
                role = user_roles[0]
                category_name = self._get_category_name(role)
                response_data['primary_answer'] = answers_by_category[category_name]['answer']
                if run_eval:
                    response_data['primary_evaluation'] = answers_by_category[category_name]['evaluation']
                # response_data['sources'] = answers_by_category[category_name]['sources']
            
            logger.info(
                "[RESPONSE] user='%s' roles=%s categories=%s total_cost=$%.6f",
                username, user_roles,
                list(answers_by_category.keys()),
                request_total_cost
            )
            return response_data
        
        except Exception as e:
            logger.error(
                "[QUERY_ERROR] user='%s': %s",
                username, e, exc_info=True
            )
            return {
                'success': False,
                'answer': f'Error processing query: {str(e)}',
                'sources': [],
                'allowed_categories': [self._get_category_name(r) for r in user_roles]
            }
    
    def check_role_support(self, question, username, requested_role, user_roles):
        """
        Check if user has access to answer question about a specific role
        """
        if not user_has_role(username, requested_role):
            return False, f"Role not supported for {self._get_category_name(requested_role)} Information"
        return True, None

class DocumentProcessor:
    """Helper class to process documents for RAG"""
    
    @staticmethod
    def split_into_chunks(text, chunk_size=1000, overlap=200):
        """Split text into chunks for embedding"""
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk)
        return chunks
    
    @staticmethod
    def create_metadata(filename, category, chunk_index=0, total_chunks=1):
        """Create metadata for a document"""
        return {
            'filename': filename,
            'category': category,
            'chunk': chunk_index,
            'total_chunks': total_chunks
        }
