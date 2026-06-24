"""Proof: exactly one module imports an LLM SDK.

This encodes the Phase 0 guarantee — "grep the codebase: zero direct LLM-SDK
imports outside llm.py" — as an enforced test.
"""
import ast
import os

import app

# SDKs that may only ever be imported by the seam.
BANNED_ROOTS = {"langchain_groq", "langchain_openai", "openai", "groq"}
SEAM = "core/llm.py"


def _python_files(root):
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(dirpath, f)


def _imported_roots(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                yield n.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module.split(".")[0]


def test_no_llm_sdk_imported_outside_seam():
    root = os.path.dirname(app.__file__)
    violations = []
    for path in _python_files(root):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        if rel == SEAM:
            continue
        for imported in _imported_roots(path):
            if imported in BANNED_ROOTS:
                violations.append((rel, imported))
    assert not violations, f"LLM SDK imported outside {SEAM}: {violations}"
