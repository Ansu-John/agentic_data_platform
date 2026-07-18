from typing import Any

import structlog
from langchain_core.prompts import ChatPromptTemplate
from src.api.agents.nlq_agent.state import NLQAgentState
from src.api.utils.bedrock_client import BedrockClientFactory

logger = structlog.get_logger()

def generate_sql(state: NLQAgentState) -> dict[str, Any]:
    """Generates precise AWS Athena (Presto/Trino SQL syntax) based on the context."""
    if state.get("error_trace"):
        return {}

    logger.info("generating_athena_sql", user_query=state["user_query"])

    system_prompt = (
        "You are an expert Senior Data Engineer and AWS Athena SQL Optimizer.\n"
        "Your task is to convert the user's plain text query into a high-performance, "
        "valid Athena SQL query.\n\n"
        "CRITICAL RULES:\n"
        "1. Only use the tables and columns explicitly provided in the Data Catalog Context.\n"
        "2. Return ONLY the raw SQL code. Do not wrap it in markdown block quotes "
        "(e.g. do not use ```sql).\n"
        "3. Ensure the SQL complies strictly with Presto/Trino SQL syntax supported by Athena.\n"
        "4. Output SELECT statements only. Never write destructive operations.\n\n"
        "Data Catalog Context:\n{catalog_context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Generate the SQL query for: {user_query}")
    ])

    try:
        llm = BedrockClientFactory.get_llm()
        chain = prompt | llm
        response = chain.invoke({
            "catalog_context": state["catalog_context"],
            "user_query": state["user_query"]
        })

        sql = str(response.content).strip()
        # Edge case cleanup for loose LLM behavior
        if sql.startswith("```"):
            sql = sql.replace("```sql", "").replace("```", "").strip()

        logger.info("sql_generation_complete", generated_sql=sql)
        return {"generated_sql": sql}

    except Exception as e:
        logger.error("llm_sql_generation_failed", error=str(e))
        return {"error_trace": f"LLM SQL generation step failed: {str(e)}"}
