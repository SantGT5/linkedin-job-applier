'''
Claude (Anthropic) AI connection for the LinkedIn Auto Job Applier.

Uses the official Anthropic Python SDK (`anthropic`) — NOT an OpenAI-compatible
shim. Provides skill extraction, question answering, and AI-powered job relevance
filtering so the bot only applies to jobs that match your profile.

Configure your key and model in Settings → AI (keys in .env) (`claude_api_key`, `claude_model`).
'''

from config.secrets import use_AI, claude_api_key, claude_model
from config.settings import showAiErrorAlerts
from modules.helpers import print_lg, critical_error_log, convert_to_json
from modules.ai.prompts import (
    extract_skills_prompt,
    claude_extract_skills_response_schema,
    ai_answer_prompt,
    job_relevance_prompt,
    job_relevance_response_schema,
)

from modules.helpers import safe_confirm as confirm
from typing import Literal

import anthropic


def _model_supports_effort(model_name: str) -> bool:
    '''
    The `effort` output_config parameter is supported on Opus 4.5+, Opus 4.6/4.7/4.8,
    Sonnet 4.6 and Fable 5, but NOT on Haiku 4.5 or older Sonnets (those return an error).
    '''
    name = (model_name or "").lower()
    return "haiku" not in name


def claude_show_error_alert(message: str, e: Exception) -> None:
    '''
    Logs a Claude error and optionally shows an alert (honors `showAiErrorAlerts`).
    '''
    global showAiErrorAlerts
    critical_error_log(message, e)
    if showAiErrorAlerts:
        if "Pause AI error alerts" == confirm(
            f"{message}\n{str(e)}",
            "Claude Connection Error",
            ["Pause AI error alerts", "Okay Continue"],
        ):
            showAiErrorAlerts = False


def claude_create_client() -> "anthropic.Anthropic | None":
    '''
    Creates and validates an Anthropic client using the official SDK.
    * Reads `claude_api_key` and `claude_model` from Settings → AI (keys in .env).
    * Validates the key + model by retrieving model metadata.
    * Returns an `anthropic.Anthropic` client, or `None` on error.
    '''
    try:
        print_lg("Creating Claude (Anthropic) client...")
        if not use_AI:
            raise ValueError("AI is not enabled! Turn on 'Use AI' in Settings → AI.")
        if not claude_api_key or "sk-ant" not in claude_api_key:
            raise ValueError(
                "Claude API key is missing or looks invalid. Set CLAUDE_API_KEY in .env and run `make up`."
            )

        client = anthropic.Anthropic(api_key=claude_api_key)

        # Validates both the API key and the configured model in one cheap call.
        model_info = client.models.retrieve(claude_model)

        print_lg(f"Connected to Claude, model {getattr(model_info, 'display_name', model_info.id)} ({model_info.id}).")
        return client
    except anthropic.AuthenticationError as e:
        claude_show_error_alert(
            "Claude API key is invalid or revoked. Please check CLAUDE_API_KEY in .env.", e
        )
        return None
    except anthropic.NotFoundError as e:
        claude_show_error_alert(
            f"Claude model `{claude_model}` was not found. Check the model in Settings → AI.", e
        )
        return None
    except Exception as e:
        claude_show_error_alert("Error occurred while creating the Claude client.", e)
        return None


def claude_completion(
    client: "anthropic.Anthropic",
    prompt: str,
    response_schema: dict | None = None,
    effort: Literal["low", "medium", "high", "xhigh", "max"] = "low",
    max_tokens: int = 1024,
) -> dict | str:
    '''
    Runs a single Claude completion.
    * `response_schema`: an Anthropic `output_config.format` JSON schema. If given,
      the response is constrained to valid JSON and returned as a parsed `dict`.
    * `effort`: thinking/effort depth. Kept low for fast, cheap, per-job calls.
    * Returns parsed JSON `dict` (when `response_schema` is set) or plain text `str`.
    '''
    if not client:
        raise ValueError("Claude client is not available!")

    output_config: dict = {}
    if _model_supports_effort(claude_model):
        output_config["effort"] = effort
    if response_schema:
        output_config["format"] = response_schema

    params: dict = {
        "model": claude_model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if output_config:
        params["output_config"] = output_config

    message = client.messages.create(**params)

    # Safety classifiers can decline a request (HTTP 200 with stop_reason "refusal").
    if getattr(message, "stop_reason", None) == "refusal":
        raise ValueError("Claude declined to respond to this request (safety refusal).")

    result = "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )

    if response_schema:
        return convert_to_json(result)
    return result


def claude_extract_skills(client: "anthropic.Anthropic", job_description: str) -> dict:
    '''
    Extracts and classifies skills from a job description using Claude.
    * Returns a `dict` with keys: tech_stack, technical_skills, other_skills,
      required_skills, nice_to_have.
    '''
    try:
        prompt = extract_skills_prompt.format(job_description)
        return claude_completion(
            client, prompt, response_schema=claude_extract_skills_response_schema, effort="low"
        )
    except Exception as e:
        critical_error_log("Error occurred while extracting skills with Claude!", e)
        return {"error": str(e)}


def claude_answer_question(
    client: "anthropic.Anthropic",
    question: str,
    options: list[str] | None = None,
    question_type: Literal['text', 'textarea', 'single_select', 'multiple_select'] = 'text',
    job_description: str = None,
    about_company: str = None,
    user_information_all: str = None,
) -> str:
    '''
    Generates a concise, human-like answer for an application question using Claude.
    '''
    try:
        prompt = ai_answer_prompt.format(user_information_all or "N/A", question)

        if options and question_type in ('single_select', 'multiple_select'):
            prompt += "\n\nOPTIONS:\n" + "\n".join(f"- {option}" for option in options)
            prompt += (
                "\n\nSelect exactly ONE option from the list above."
                if question_type == 'single_select'
                else "\n\nYou may select MULTIPLE options from the list above if appropriate."
            )
        if job_description and job_description != "Unknown":
            prompt += f"\n\nJOB DESCRIPTION:\n{job_description}"
        if about_company and about_company != "Unknown":
            prompt += f"\n\nABOUT COMPANY:\n{about_company}"

        return claude_completion(client, prompt, effort="low")
    except Exception as e:
        critical_error_log("Error occurred while answering question with Claude!", e)
        return {"error": str(e)}


def claude_check_job_relevance(
    client: "anthropic.Anthropic",
    job_description: str,
    about_company: str | None = None,
    user_information_all: str = None,
) -> dict:
    '''
    Scores how well a job matches the candidate's profile (0-100) so the bot can
    skip poor fits.
    * Returns a `dict`: match_score (int), recommend_apply (bool), reasons (str),
      matched_skills (list), missing_skills (list).
    * Raises on API error so the caller can decide to apply anyway (fail-open).
    '''
    company_line = (
        f" (Company: {about_company})" if about_company and about_company != "Unknown" else ""
    )
    prompt = job_relevance_prompt.format(user_information_all or "N/A", company_line, job_description)
    # Use a slightly higher effort here — this is the judgment that decides whether to apply.
    return claude_completion(client, prompt, response_schema=job_relevance_response_schema, effort="medium")


def claude_close_client(client: "anthropic.Anthropic") -> None:
    '''
    Closes the Claude client. The Anthropic SDK doesn't strictly require this;
    provided for symmetry with the other providers.
    '''
    try:
        if client and hasattr(client, "close"):
            client.close()
    except Exception as e:
        print_lg("Failed to close Claude client (safe to ignore):", e)
