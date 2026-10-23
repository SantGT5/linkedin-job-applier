'''
GLM (Zhipu AI / Z.ai) connection for the LinkedIn Auto Job Applier.

GLM models (e.g. `glm-4.6`, `glm-4.5`) are served through an OpenAI-compatible
endpoint, so this module talks to them with the official OpenAI Python SDK
(`openai`) pointed at GLM's base URL — the same helper set the Claude module
exposes (client creation, skill extraction, question answering, and AI-powered
job relevance filtering), so the bot only applies to jobs that match your profile.

Configure your key, model, endpoint, and thinking depth in Settings → AI (keys in .env)
(`glm_api_key`, `glm_model`, `glm_api_url`, `glm_reasoning_effort`).
'''

from config.secrets import use_AI, glm_api_key, glm_model, glm_api_url, glm_reasoning_effort
from config.settings import showAiErrorAlerts
from modules.helpers import print_lg, critical_error_log
from modules.ai.prompts import (
    extract_skills_prompt,
    ai_answer_prompt,
    job_relevance_prompt,
)

from modules.helpers import safe_confirm as confirm
from typing import Literal

import json
import openai
from openai import OpenAI


def _escape_control_chars(s: str) -> str:
    '''
    Rewrites raw control characters (bytes < 0x20) found INSIDE JSON string
    literals into their escaped forms, leaving everything outside strings and
    already-escaped sequences untouched. GLM sometimes emits a literal newline
    (or tab) inside a string value, which strict `json.loads` rejects.
    '''
    out: list[str] = []
    in_string = False
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if not in_string:
            if c == '"':
                in_string = True
            out.append(c)
            i += 1
            continue
        # Inside a string literal:
        if c == '\\' and i + 1 < n:
            # Keep escape sequences intact, whatever they escape.
            out.append(c)
            out.append(s[i + 1])
            i += 2
            continue
        if c == '"':
            in_string = False
            out.append(c)
        elif c == '\n':
            out.append('\\n')
        elif c == '\r':
            out.append('\\r')
        elif c == '\t':
            out.append('\\t')
        elif ord(c) < 0x20:
            out.append('\\u%04x' % ord(c))
        else:
            out.append(c)
        i += 1
    return ''.join(out)


def _parse_glm_json(raw: str) -> dict:
    '''
    Decodes the JSON object GLM was asked to return. Tolerates models that wrap
    the payload in Markdown code fences, add stray prose around it, or emit
    literal control characters inside string values.
    '''
    s = raw.strip()

    # Strip a leading ```json / ``` fence and its closing counterpart.
    if s.startswith("```"):
        s = s[3:]
        nl = s.find("\n")
        if nl >= 0:
            s = s[nl + 1:]  # drop the optional language tag on the first line
        s = s.strip()
        if s.endswith("```"):
            s = s[:-3].strip()

    # Fall back to the outermost object if the model added surrounding prose.
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end >= start:
        s = s[start:end + 1]

    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # Re-escape stray control characters and try once more.
        return json.loads(_escape_control_chars(s))


def glm_show_error_alert(message: str, e: Exception) -> None:
    '''
    Logs a GLM error and optionally shows an alert (honors `showAiErrorAlerts`).
    '''
    global showAiErrorAlerts
    critical_error_log(message, e)
    if showAiErrorAlerts:
        if "Pause AI error alerts" == confirm(
            f"{message}\n{str(e)}",
            "GLM Connection Error",
            ["Pause AI error alerts", "Okay Continue"],
        ):
            showAiErrorAlerts = False


def glm_create_client() -> "OpenAI | None":
    '''
    Creates and validates a GLM client using the OpenAI-compatible SDK.
    * Reads `glm_api_key`, `glm_model`, and `glm_api_url` from Settings → AI (keys in .env).
    * Validates the key + model with a single, cheap completion "ping".
    * Returns an `OpenAI` client bound to the GLM endpoint, or `None` on error.
    '''
    try:
        print_lg("Creating GLM (Zhipu AI) client...")
        if not use_AI:
            raise ValueError("AI is not enabled! Turn on 'Use AI' in Settings → AI.")
        if not glm_api_key or glm_api_key in ("", "not-needed"):
            raise ValueError(
                "GLM API key is missing. Set GLM_API_KEY in .env and run `make up`."
            )

        client = OpenAI(api_key=glm_api_key, base_url=glm_api_url)

        # Validates both the API key and the configured model in one cheap call.
        # (Unlike Anthropic, the GLM endpoint has no free model-metadata lookup, so
        # a tiny completion is the reliable way to confirm the key + model work.)
        client.chat.completions.create(
            model=glm_model,
            max_tokens=16,
            messages=[{"role": "user", "content": "ping"}],
        )

        print_lg(f"Connected to GLM, model {glm_model} at {glm_api_url}.")
        return client
    except openai.AuthenticationError as e:
        glm_show_error_alert(
            "GLM API key is invalid or revoked. Please check GLM_API_KEY in .env.", e
        )
        return None
    except openai.NotFoundError as e:
        glm_show_error_alert(
            f"GLM model `{glm_model}` was not found. Check the model in Settings → AI.", e
        )
        return None
    except Exception as e:
        glm_show_error_alert("Error occurred while creating the GLM client.", e)
        return None


def glm_thinking_params(reasoning_effort: str) -> dict:
    '''
    Request params for GLM's thinking, from `glm_reasoning_effort` in Settings → AI (keys in .env).
    * GLM-5.3 models always think (sending "disabled" is rejected); `reasoning_effort`
      ("low", "high", "max") sets how deeply.
    * "none" (or "") turns thinking off, for older models that support that.
    '''
    if reasoning_effort in ("", "none"):
        return {"thinking": {"type": "disabled"}}
    return {"thinking": {"type": "enabled"}, "reasoning_effort": reasoning_effort}


def glm_completion(
    client: "OpenAI",
    prompt: str,
    as_json: bool = False,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> dict | str:
    '''
    Runs a single GLM completion.
    * `as_json`: when `True`, asks the endpoint for a JSON object
      (`response_format={"type": "json_object"}`) and returns a parsed `dict`.
    * `temperature`: kept low for deterministic, per-job calls.
    * Thinking depth comes from `glm_reasoning_effort` (see `glm_thinking_params`).
    * Returns parsed JSON `dict` (when `as_json` is set) or plain text `str`.
    '''
    if not client:
        raise ValueError("GLM client is not available!")

    params: dict = {
        "model": glm_model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
        "extra_body": glm_thinking_params(glm_reasoning_effort),
    }
    if as_json:
        # The prompts already instruct the model to return JSON; this constrains
        # the output so `_parse_glm_json` gets clean, parseable text.
        params["response_format"] = {"type": "json_object"}

    completion = client.chat.completions.create(**params)

    result = completion.choices[0].message.content
    if not result:
        raise ValueError("GLM returned an empty response.")

    if as_json:
        return _parse_glm_json(result)
    return result


def glm_extract_skills(client: "OpenAI", job_description: str) -> dict:
    '''
    Extracts and classifies skills from a job description using GLM.
    * Returns a `dict` with keys: tech_stack, technical_skills, other_skills,
      required_skills, nice_to_have.
    '''
    try:
        prompt = extract_skills_prompt.format(job_description)
        return glm_completion(client, prompt, as_json=True, temperature=0.0)
    except Exception as e:
        critical_error_log("Error occurred while extracting skills with GLM!", e)
        return {"error": str(e)}


def glm_answer_question(
    client: "OpenAI",
    question: str,
    options: list[str] | None = None,
    question_type: Literal['text', 'textarea', 'single_select', 'multiple_select'] = 'text',
    job_description: str = None,
    about_company: str = None,
    user_information_all: str = None,
) -> str:
    '''
    Generates a concise, human-like answer for an application question using GLM.
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

        return glm_completion(client, prompt, temperature=0.5)
    except Exception as e:
        critical_error_log("Error occurred while answering question with GLM!", e)
        return {"error": str(e)}


def glm_check_job_relevance(
    client: "OpenAI",
    job_description: str,
    about_company: str | None = None,
    user_information_all: str = None,
) -> dict:
    '''
    Scores how well a job matches the candidate's profile (0-100) so the bot can
    skip poor fits.
    * Returns a `dict`: match_score (int), recommend_apply (bool), reasons (str),
      matched_skills (list), missing_skills (list), apply_by_email (bool),
      apply_email (str), email_subject (str).
    * Raises on API error so the caller can decide to apply anyway (fail-open).
    '''
    company_line = (
        f" (Company: {about_company})" if about_company and about_company != "Unknown" else ""
    )
    prompt = job_relevance_prompt.format(user_information_all or "N/A", company_line, job_description)
    # Use a slightly higher token budget here — this is the judgment that decides whether to apply.
    return glm_completion(client, prompt, as_json=True, temperature=0.2, max_tokens=1536)


def glm_close_client(client: "OpenAI") -> None:
    '''
    Closes the GLM client. Provided for symmetry with the other providers.
    '''
    try:
        if client and hasattr(client, "close"):
            client.close()
    except Exception as e:
        print_lg("Failed to close GLM client (safe to ignore):", e)
