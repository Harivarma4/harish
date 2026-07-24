"""Lightweight, dependency-free agent orchestration (custom, not LangGraph/CrewAI).

Kept deliberately small and deterministic so the pipeline is fully testable
offline. A LangGraph or CrewAI runner can wrap this later without touching agents.
"""
