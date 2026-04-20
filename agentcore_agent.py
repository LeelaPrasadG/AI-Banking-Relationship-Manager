"""
AWS Bedrock AgentCore Runtime entry point.
Wraps the existing RAG pipeline as a serverless AgentCore agent.

Deploy with: agentcore deploy
Invoke with: agentcore invoke
"""
from bedrock_agentcore import BedrockAgentCoreApp
from dotenv import load_dotenv
import os

load_dotenv()

from rag_pipeline import RAGPipeline

app = BedrockAgentCoreApp()

# Lazy-initialize the pipeline (avoid cold-start cost at import time)
_pipeline: RAGPipeline | None = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline


@app.entrypoint
async def handler(request: dict):
    """
    Expected request payload:
    {
        "question":   "What is the auto-loan interest rate?",
        "username":   "john_doe",
        "user_roles": ["auto-loan", "credit-card"]
    }
    """
    question = request.get("question", "").strip()
    username = request.get("username", "anonymous")
    user_roles = request.get("user_roles", [])

    if not question:
        yield {"success": False, "error": "question is required"}
        return

    if not user_roles:
        yield {"success": False, "error": "user_roles is required"}
        return

    pipeline = get_pipeline()
    result = pipeline.query(question, username, user_roles)
    yield result


if __name__ == "__main__":
    app.run()
