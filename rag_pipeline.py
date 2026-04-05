from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone
from config import OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME, OPENAI_MODEL
from auth import user_has_role
import json
import os
from dotenv import load_dotenv

load_dotenv()

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
        Query the RAG system with role-based access control
        """
        
        if not user_roles:
            return {
                'success': False,
                'answer': 'Error: User has no assigned roles.',
                'sources': [],
                'allowed_categories': []
            }
        
        try:
            # Get embedding for the question
            question_embedding = self.embedding.embed_query(question)
            
            # Collect results from all user's roles
            answers_by_category = {}
            
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
                except Exception as llm_error:
                    print(f"LLM Error for {role}: {str(llm_error)}")
                    answer_text = f"Error getting response: {str(llm_error)}"
                
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
                'username': username
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
