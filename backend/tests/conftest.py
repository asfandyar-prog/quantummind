import os
import sys

# Make `import app` work regardless of the directory pytest is invoked from,
# and guarantee the provider validator can construct Settings even without a
# local .env (tests never make real network calls).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("LLM_PROVIDER", "groq")
