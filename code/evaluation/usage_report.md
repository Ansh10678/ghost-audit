# LLM & Token Usage Report

## 1. Overview
Summary of model invocations, token consumption, and cost estimates for the complete evaluation dataset run:

| Metric | Value |
|---|---|
| **Model Provider** | Google Cloud / Gemini API |
| **Model Name** | gemini-2.5-flash |
| **Total Model Invocations** | 0 |
| **Prompt Tokens** | 0 |
| **Completion Tokens** | 0 |
| **Total Tokens** | 0 |
| **Average Tokens per Request** | 0.0 |
| **Estimated Total Cost (USD)** | $0.0000 |
| **Estimated Cost per Request (USD)** | $0.000000 |

## 2. Architecture Trade-offs
- **Deterministic Core**: In accordance with the system specification, 100% of identity graph resolution, evidence scanning, SQL/JSON parsing, rule evaluation, and step serialization are executed deterministically.
- **LLM Role**: LLMs are reserved for unstructured intent ambiguity resolution and multilingual request classification with on-disk caching, keeping token consumption minimal and deterministic.
