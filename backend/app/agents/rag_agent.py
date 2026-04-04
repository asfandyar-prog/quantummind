# ── app/agents/rag_agent.py ──────────────────────────────────
#
# LangGraph RAG Agent
#
# Graph flow:
#   retrieve_context → generate_answer → grade_answer
#                                            ↙       ↘
#                                      retry      assemble
#                                   (max 1x)

from typing import TypedDict, Annotated
import operator
import os

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.core.prompts import RAG_PROMPT, build_rag_prompt
from app.core.memory import get_checkpointer

# ── ChromaDB setup ────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_DIR = os.path.join(BASE_DIR, "data", "chroma")


def get_vectorstore():
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
        collection_name="quantummind_course",
    )


# ── STATE ─────────────────────────────────────────────────────
class RAGAgentState(TypedDict):
    messages:         Annotated[list[BaseMessage], operator.add]
    week:             int          # current course week (for filtered retrieval)
    retrieved_chunks: list[str]    # text chunks from ChromaDB
    answer:           str          # generated answer
    grade_feedback:   str          # pass / fail
    retry_count:      int
    final_response:   str


def get_llm(temperature: float = 0.3) -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=temperature,
    )


# ════════════════════════════════════════════════════════════════
# NODES
# ════════════════════════════════════════════════════════════════

async def retrieve_context(state: RAGAgentState) -> dict:
    """
    Node 1 — Retrieve relevant chunks from ChromaDB.

    Filters by week number so the agent only uses content
    from the current lesson — not the entire course.

    If no content exists for this week yet (files not uploaded),
    returns empty list — the agent will answer from general knowledge.
    """
    # Get the latest user message
    last_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_msg = msg.content
            break

    week = state.get("week", 0)

    try:
        vectorstore = get_vectorstore()

        # Filter by week if specified, otherwise search all
        if week > 0:
            retriever = vectorstore.as_retriever(
                search_kwargs={
                    "k": 5,
                    "filter": {"week": week},
                }
            )
        else:
            retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

        docs = retriever.invoke(last_msg)
        chunks = [doc.page_content for doc in docs]
        print(f"[RAGAgent] retrieve_context → {len(chunks)} chunks (week {week})")

    except Exception as e:
        print(f"[RAGAgent] ChromaDB error: {e} — using empty context")
        chunks = []

    return {"retrieved_chunks": chunks, "grade_feedback": ""}


async def generate_answer(state: RAGAgentState) -> dict:
    """
    Node 2 — Generate answer using retrieved context.

    If chunks exist: uses RAG prompt (grounded in course material).
    If no chunks: falls back to general knowledge with a note.
    """
    llm = get_llm(temperature=0.3)

    last_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_msg = msg.content
            break

    chunks = state.get("retrieved_chunks", [])

    if chunks:
        # Use retrieved context
        system_prompt = build_rag_prompt(last_msg, chunks)
    else:
        # No course content uploaded yet — answer from general knowledge
        system_prompt = f"""{RAG_PROMPT}

No course-specific material has been uploaded for this week yet.
Answer using your general quantum computing knowledge, and note that
the answer is from general knowledge, not the course materials."""

    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    # On retry — add feedback
    if state.get("grade_feedback") == "fail" and state.get("retry_count", 0) > 0:
        messages.append(HumanMessage(content="Please improve your previous answer. Be more specific and cite the course material more directly."))

    answer = await (llm | StrOutputParser()).ainvoke(messages)
    print(f"[RAGAgent] generate_answer → {len(answer)} chars")
    return {"answer": answer}


async def grade_answer(state: RAGAgentState) -> dict:
    """
    Node 3 — Check if the answer is grounded in the retrieved context.
    """
    llm = get_llm(temperature=0.0)
    chunks = state.get("retrieved_chunks", [])

    if not chunks:
        # No context to grade against — pass automatically
        return {"grade_feedback": "pass"}

    context_preview = "\n".join(chunks[:2])[:600]

    prompt = f"""Grade this answer based on how well it uses the provided course material.

Course material excerpt:
{context_preview}

Answer:
{state["answer"]}

Does the answer reference the course material accurately?
Respond with ONLY: "pass" or "fail" """

    grade = await (llm | StrOutputParser()).ainvoke([HumanMessage(content=prompt)])
    grade = grade.strip().lower()
    if grade not in ("pass", "fail"):
        grade = "pass"

    print(f"[RAGAgent] grade_answer → {grade}")
    return {"grade_feedback": grade}


async def retry_node(state: RAGAgentState) -> dict:
    count = state.get("retry_count", 0) + 1
    print(f"[RAGAgent] retry → {count}/1")
    return {"retry_count": count}


async def assemble_response(state: RAGAgentState) -> dict:
    answer = state.get("answer", "")
    chunks = state.get("retrieved_chunks", [])

    # Add source attribution if we used course material
    if chunks:
        week = state.get("week", 0)
        source_note = f"\n\n*— Based on Week {week} course materials*" if week > 0 else ""
        final = answer + source_note
    else:
        final = answer + "\n\n*— General knowledge (no course material uploaded for this week yet)*"

    return {
        "final_response": final,
        "messages": [AIMessage(content=final)],
    }


# ════════════════════════════════════════════════════════════════
# CONDITIONAL EDGES
# ════════════════════════════════════════════════════════════════

def should_retry_or_assemble(state: RAGAgentState) -> str:
    grade      = state.get("grade_feedback", "pass")
    retry_count = state.get("retry_count", 0)
    if grade == "fail" and retry_count < 1:
        return "retry"
    return "done"


# ════════════════════════════════════════════════════════════════
# GRAPH
# ════════════════════════════════════════════════════════════════

def build_rag_agent_graph():
    graph = StateGraph(RAGAgentState)

    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_answer",  generate_answer)
    graph.add_node("grade_answer",     grade_answer)
    graph.add_node("retry_node",       retry_node)
    graph.add_node("assemble_response", assemble_response)

    graph.set_entry_point("retrieve_context")

    graph.add_edge("retrieve_context", "generate_answer")
    graph.add_edge("generate_answer",  "grade_answer")
    graph.add_edge("retry_node",       "generate_answer")
    graph.add_edge("assemble_response", END)

    graph.add_conditional_edges(
        "grade_answer",
        should_retry_or_assemble,
        {"retry": "retry_node", "done": "assemble_response"}
    )

    return graph.compile(checkpointer=get_checkpointer())


_rag_graph = None

def get_rag_graph():
    global _rag_graph
    if _rag_graph is None:
        _rag_graph = build_rag_agent_graph()
    return _rag_graph


# ════════════════════════════════════════════════════════════════
# PUBLIC INTERFACE
# ════════════════════════════════════════════════════════════════

async def run_rag_agent(
    user_message: str,
    chat_history: list | None = None,
    thread_id: str = "default",
    week: int = 0,
) -> str:
    initial_state: RAGAgentState = {
        "messages":         [HumanMessage(content=user_message)],
        "week":             week,
        "retrieved_chunks": [],
        "answer":           "",
        "grade_feedback":   "",
        "retry_count":      0,
        "final_response":   "",
    }
    config = {"configurable": {"thread_id": f"{thread_id}_rag"}}
    result = await get_rag_graph().ainvoke(initial_state, config=config)
    return result.get("final_response", "Sorry, I could not find an answer.")


async def stream_rag_agent(
    user_message: str,
    chat_history: list | None = None,
    thread_id: str = "default",
    week: int = 0,
):
    response = await run_rag_agent(user_message, chat_history, thread_id, week)
    words = response.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")