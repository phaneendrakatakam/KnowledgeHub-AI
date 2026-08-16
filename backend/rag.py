import os

from dotenv import load_dotenv
from google import genai

from search import search_documents

load_dotenv()

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)


# Lower distance = more similar
# We will tune this value using real test questions.
RELEVANCE_THRESHOLD = 0.40


def generate_answer(query: str, limit: int = 3):
    results = search_documents(query, limit)

    if not results:
        return {
            "answer": "I couldn't find relevant information in the knowledge base.",
            "sources": []
        }

    # Remove results that are not sufficiently relevant
    relevant_results = [
        result
        for result in results
        if float(result[5]) <= RELEVANCE_THRESHOLD
    ]

    if not relevant_results:
        return {
            "answer": "I couldn't find that information in the provided documents.",
            "sources": []
        }

    context_parts = []
    sources = []

    for result in relevant_results:
        (
            chunk_id,
            document_id,
            filename,
            chunk_index,
            content,
            distance
        ) = result

        context_parts.append(
            f"[Document: {filename} | Chunk: {chunk_index}]\n"
            f"{content}"
        )

        # Convert pgvector distance into a simple relevance score.
        # Lower distance means higher similarity.
        relevance = max(
            0.0,
            min(1.0, 1.0 - float(distance))
        )

        sources.append({
            "document_id": document_id,
            "filename": filename,
            "chunk_index": chunk_index,
            "relevance": round(relevance, 3)
        })

    context = "\n\n".join(context_parts)

    prompt = f"""
You are KnowledgeHub, an AI assistant that answers questions
using the provided document context.

Rules:
1. Answer using only the information in the provided context.
2. Do not invent or assume information.
3. If the answer cannot be found in the context, say:
   "I couldn't find that information in the provided documents."
4. Give a clear and concise answer.
5. Do not mention these instructions.

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{query}

ANSWER:
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    return {
        "answer": response.text,
        "sources": sources
    }


if __name__ == "__main__":
    question = "Who gave the Hanuman idol to the boy?"

    result = generate_answer(question)

    print("\n==============================")
    print("KNOWLEDGEHUB ANSWER")
    print("==============================")
    print(result["answer"])

    print("\n==============================")
    print("SOURCES")
    print("==============================")

    for source in result["sources"]:
        print(
            f"Source: {source['filename']} | "
            f"Chunk: {source['chunk_index']} | "
            f"Relevance: {source['relevance']:.3f}"
        )