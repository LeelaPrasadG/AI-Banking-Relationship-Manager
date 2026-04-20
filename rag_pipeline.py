from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone
from config import OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME, OPENAI_MODEL
from config import GUARDRAIL_LLM_SCOPE_CHECK_ENABLED, GUARDRAIL_LOG_LEVEL
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
logging.basicConfig(level=getattr(logging, GUARDRAIL_LOG_LEVEL, logging.WARNING))

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
        self._scope_prompt = PromptTemplate(
            input_variables=["question", "categories"],
            template=(
                "You are a strict topic classifier for a banking assistant.\n"
                "The assistant can ONLY answer questions about: {categories}.\n\n"
                "Question: {question}\n\n"
                "Reply with exactly one word: RELEVANT or IRRELEVANT.\n"
                "- RELEVANT: the question is clearly about banking, loans, credit cards, "
                "account management, or financial products.\n"
                "- IRRELEVANT: the question has nothing to do with banking/finance.\n\n"
                "Classification:"
            ),
        )

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
        if not OPENAI_API_KEY:
            raise ValueError('OPENAI_API_KEY is not set. Please check your .env file')
        
        self.llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
            temperature=0.3,
            max_tokens=1000
        )
        self.embedding = OpenAIEmbeddings(
            api_key=OPENAI_API_KEY,
            model='text-embedding-3-small'
        )
        self.index_name = PINECONE_INDEX_NAME
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=PINECONE_API_KEY)
        self.index = self.pc.Index(self.index_name)

        # Guardrails
        self.guardrails = Guardrails(self.llm)
    
    def _get_category_name(self, category):
        """Convert category code to readable name"""
        names = {
            'auto-loan': 'Auto Loan',
            'credit-card': 'Credit Card',
            'banking': 'Banking'
        }
        return names.get(category, category)
    
    def _create_category_prompt(self, category):
        """Create a role-specific prompt"""
        category_name = self._get_category_name(category)
        
        template = f"""You are a helpful customer service assistant for {category_name} products at a bank.
        
Based on the provided {category_name} documents, answer the customer's question accurately and professionally.

If the question is not related to {category_name} or cannot be answered from the provided documents, 
politely inform the user that you can only assist with {category_name} related queries.

Context from documents:
{{context}}

Question: {{question}}

Answer:"""
        
        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )
    
    def query(self, question, username, user_roles):
        """
        Query the RAG system with role-based access control and guardrails.
        Guardrails applied:
          - Input:  PII redaction, out-of-scope detection
          - Output: PII redaction on LLM answers
        """
        
        if not user_roles:
            return {
                'success': False,
                'answer': 'Error: User has no assigned roles.',
                'sources': [],
                'allowed_categories': []
            }

        # ------------------------------------------------------------------
        # INPUT GUARDRAIL
        # ------------------------------------------------------------------
        input_check = self.guardrails.check_input(question, user_roles)

        if input_check.pii_found:
            # Use the redacted version for all downstream processing
            question = input_check.modified_text
            logger.info(
                "User '%s': PII removed from question – types: %s",
                username, input_check.pii_found
            )

        if not input_check.passed:
            logger.info(
                "User '%s': question blocked by input guardrail – %s",
                username, input_check.reason
            )
            return {
                'success': False,
                'guardrail_blocked': True,
                'answer': input_check.reason,
                'sources': [],
                'allowed_categories': [self._get_category_name(r) for r in user_roles],
            }

        try:
            # Get embedding for the question
            question_embedding = self.embedding.embed_query(question)
            cost_monitor.record_embedding(username, 'text-embedding-3-small', question)

            # Collect results from all user's roles
            answers_by_category = {}
            request_total_cost = 0.0
            
            for role in user_roles:
                category_name = self._get_category_name(role)
                
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
                    print(f"Filter query failed, trying without filter: {str(filter_error)}")
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
                
                # Extract context from chunks
                context = "\n---\n".join([
                    chunk['text'] for chunk in retrieved_chunks
                ]) if retrieved_chunks else "No relevant documents found."
                
                # Create prompt and get answer
                prompt = self._create_category_prompt(role)
                formatted_prompt = prompt.format(context=context, question=question)
                
                # Get LLM response
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

                except Exception as llm_error:
                    print(f"LLM Error for {role}: {str(llm_error)}")
                    answer_text = f"Error getting response: {str(llm_error)}"

                # ----------------------------------------------------------
                # OUTPUT GUARDRAIL – redact any PII that leaked into answer
                # ----------------------------------------------------------
                output_check = self.guardrails.check_output(answer_text)
                if output_check.pii_found:
                    logger.warning(
                        "User '%s' / category '%s': PII removed from LLM answer – types: %s",
                        username, role, output_check.pii_found
                    )
                    answer_text = output_check.modified_text
                
                answers_by_category[category_name] = {
                    'answer': answer_text,
                    # 'sources': [
                    #     {
                    #         'filename': chunk['filename'],
                    #         'category': chunk['category'],
                    #         'relevance_score': round(chunk['score'], 3)
                    #     }
                    #     for chunk in retrieved_chunks
                    # ]
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
                # response_data['sources'] = answers_by_category[category_name]['sources']
            
            return response_data
        
        except Exception as e:
            print(f"Error in RAG query: {str(e)}")
            import traceback
            traceback.print_exc()
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
