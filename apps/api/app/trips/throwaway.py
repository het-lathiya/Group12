"""Throw-away module for TC-002: a vendor import outside the Gemini adapter. Never merged."""

from google import genai


def client_type_name() -> str:
    return genai.Client.__name__
