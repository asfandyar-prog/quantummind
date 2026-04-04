import os
from langgraph.checkpoint.memory import MemorySaver

# MemorySaver stores state in RAM.
# Memory persists as long as the server is running.
# Lost on server restart 
# Upgrade path: swap MemorySaver for AsyncPostgresSaver in one line.

_checkpointer = None

async def init_checkpointer():
    global _checkpointer
    _checkpointer = MemorySaver()
    print("[Memory] MemorySaver checkpointer ready")
    return _checkpointer

def get_checkpointer():
    return _checkpointer