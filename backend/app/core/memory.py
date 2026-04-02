# ── app/core/memory.py ────────────────────────────────────────
#
# Creates a single shared checkpointer instance used by all agents.
#
# Why a singleton?
# Creating a new database connection per request is wasteful.
# One shared connection, reused across all requests, is the
# standard pattern for database connections in web servers.

import os
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
# AsyncSqliteSaver — async version of the SQLite checkpointer.
# We use async because FastAPI is async — mixing sync DB calls
# into async routes causes the server to block.

from app.core.config import settings

# ── Ensure data directory exists ──────────────────────────────
# SQLite needs the parent folder to exist before creating the file.
DB_PATH = "./data/memory.db"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
# exist_ok=True means: don't raise an error if folder already exists.


# ── Checkpointer instance ─────────────────────────────────────
# This is created once when the module is first imported.
# Every agent imports this same instance — one DB connection shared.
checkpointer = AsyncSqliteSaver.from_conn_string(DB_PATH)

# What does this checkpointer do?
# After every node in the graph, LangGraph calls:
#   checkpointer.aput(thread_id, state)
# Which saves the full graph state to SQLite.
#
# On the next request with the same thread_id, LangGraph calls:
#   checkpointer.aget(thread_id)
# Which loads the previous state and resumes from there.
#
# The student's entire conversation history, which nodes ran,
# what each agent decided — all of it is preserved automatically.
# You write zero serialization code — LangGraph handles it all.