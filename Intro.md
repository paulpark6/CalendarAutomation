
Hey everyone — I wanted to share a project I’ve been working on that’s closely related to what the CRM project is doing.

**Project Overview**
The goal of the project is to convert unstructured natural language input (e.g., meeting notes, reminders) into structured JSON that can be directly consumed by the Google Calendar API.
The focus is on reliability and correctness of structured output, not just raw model performance.

**LLM & Training Pipeline**
Im trying to  fine-tuned an LLM to act as a probabilistic event parser (not an executor).
Training data was generated using synthetic data from a pretrained model with human verification to cover edge cases and formatting variations.
Used Supervised Fine-Tuning (SFT) to teach the model to output strictly structured JSON.
A pretrained model is used as a judge to evaluate output quality during training and iteration.

**Evaluation & Validation**
I’m actively building custom evaluation logic, including:
Slot-level F1 scores to verify extraction of key fields (title, date, time, location, etc.)
Strict JSON schema validation to guarantee API-safe outputs
Length-normalized log-likelihood to compare model confidence across different fine-tuned variants
These checks are designed to fail fast and avoid silent errors before anything touches the Calendar API.

**Tech Stack**
Modeling & Training: PyTorch, Hugging Face Transformers
Evaluation: Custom Python evaluation functions (F1, schema validation, confidence metrics)
API Target: Google Calendar API–compatible JSON
UI (WIP): Streamlit app for testing, debugging, and manual inspection

**Current Status**
The Streamlit app and LLM evaluation pipeline are still under active development, especially on the confidence and validation side.
I wanted to share early because there’s a lot of overlap with fine-tuning LLMs for structured output, which seems very aligned with what the CRM project is exploring.
Happy to chat more or share details if useful :thumbsup:

You can check out the project here https://github.com/paulpark6/CalendarAutomation
