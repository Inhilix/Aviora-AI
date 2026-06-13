"""
Retrieval-Augmented Generation pipeline.
Embeddings are generated via the guardrail container (reuses all-MiniLM-L6-v2).
Retrieval is pure PostgreSQL / pgvector — no external vector DB.
"""
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.agents.llm_agent import call_haiku_safe
from app.config import settings

GUARDRAIL_EMBED_URL = settings.guardrail_url.replace("/classify", "/embed")
TOP_K = 5


async def embed_text(text_input: str) -> list[float]:
    """Call guardrail container to get sentence embedding."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(GUARDRAIL_EMBED_URL, json={"text": text_input[:1000]})
    return resp.json()["embedding"]


async def retrieve_context(query: str, country: str | None, db: AsyncSession) -> list[dict]:
    """
    Cosine similarity search against knowledge_base using pgvector.
    Returns top-K most relevant chunks.
    """
    embedding = await embed_text(query)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    where_clause = "WHERE country = :country" if country else ""
    params: dict = {"embedding": embedding_str, "k": TOP_K}
    if country:
        params["country"] = country

    rows = await db.execute(
        text(f"""
            SELECT topic, country, content,
                   1 - (embedding <=> :embedding::vector) AS similarity
            FROM knowledge_base
            {where_clause}
            ORDER BY embedding <=> :embedding::vector
            LIMIT :k
        """),
        params,
    )
    return [
        {"topic": r.topic, "country": r.country, "content": r.content, "similarity": r.similarity}
        for r in rows.fetchall()
    ]


async def answer_with_rag(
    query: str,
    country: str | None,
    student_id: str,
    student_name: str,
    redis_client,
    db: AsyncSession,
) -> dict:
    """
    Full RAG pipeline:
    1. Retrieve relevant knowledge base chunks
    2. Build grounded prompt
    3. Call Haiku with retrieved context injected
    4. Return answer + source topics used
    """
    chunks = await retrieve_context(query, country, db)

    if not chunks:
        return {
            "answer": "I don't have specific information on that topic yet. Please consult the official embassy or university website.",
            "sources": [],
        }

    context_block = "\n\n".join(
        f"[{c['topic']} — {c['country']}]\n{c['content']}" for c in chunks
    )

    prompt = f"""You are answering a question about studying abroad based ONLY on the provided reference material.
Do not fabricate facts not present in the references. If the references don't answer the question, say so.

REFERENCE MATERIAL:
{context_block}

STUDENT QUESTION:
{query}

Answer clearly and concisely. Cite which topic/country section supports each claim."""

    answer = await call_haiku_safe(
        prompt, student_id, "visa_guidance", student_name, redis_client, db
    )

    return {
        "answer": answer,
        "sources": [{"topic": c["topic"], "country": c["country"]} for c in chunks],
    }


async def seed_knowledge_base(entries: list[dict], db: AsyncSession) -> int:
    """
    Insert knowledge base entries with embeddings.
    entries: [{"topic": str, "country": str, "content": str}]
    Returns count of inserted rows.
    """
    inserted = 0
    for entry in entries:
        embedding = await embed_text(entry["content"][:1000])
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        await db.execute(
            text("""
                INSERT INTO knowledge_base (topic, country, content, embedding)
                VALUES (:topic, :country, :content, :embedding::vector)
                ON CONFLICT DO NOTHING
            """),
            {
                "topic": entry["topic"],
                "country": entry["country"],
                "content": entry["content"],
                "embedding": embedding_str,
            },
        )
        inserted += 1
    await db.commit()
    return inserted
