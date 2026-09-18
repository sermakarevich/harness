"""Tells the saved store which conversation to continue."""

from __future__ import annotations


def thread_config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}
