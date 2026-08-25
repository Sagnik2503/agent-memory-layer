# Expense Tracker

AI expense tracker using Python and LangGraph.

## Features

- Intent classification (expense vs other)
- Structured expense extraction from natural language
- Expense validation
- Natural language responses

## Installation

1. Clone the repository
2. Install dependencies: `uv sync`
3. Set up environment variables in `.env`

## Usage

1. Start the server: `uvicorn app.main:app --reload`
2. Send chat messages to `/chat` endpoint

## Testing

Run tests: `pytest`

Run tests excluding LLM-dependent tests: `pytest -m "not expensive"`

## Architecture

- LangGraph StateGraph with conditional routing
- Pydantic models for data validation
- HuggingFace LLM integration
- Modular node-based architecture