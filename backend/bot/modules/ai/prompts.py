"""
Author:     Sai Vignesh Golla
LinkedIn:   https://www.linkedin.com/in/saivigneshgolla/

Copyright (C) 2024 Sai Vignesh Golla

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

Support me: https://github.com/sponsors/GodsScion

version:    26.01.20.5.08
"""


##> Common Response Formats
array_of_strings = {"type": "array", "items": {"type": "string"}}
"""
Response schema to represent array of strings `["string1", "string2"]`
"""
#<


##> Extract Skills

# Structure of messages = `[{"role": "user", "content": extract_skills_prompt}]`

extract_skills_prompt = """
You are a job requirements extractor and classifier. Your task is to extract all skills mentioned in a job description and classify them into five categories:
1. "tech_stack": Identify all skills related to programming languages, frameworks, libraries, databases, and other technologies used in software development. Examples include Python, React.js, Node.js, Elasticsearch, Algolia, MongoDB, Spring Boot, .NET, etc.
2. "technical_skills": Capture skills related to technical expertise beyond specific tools, such as architectural design or specialized fields within engineering. Examples include System Architecture, Data Engineering, System Design, Microservices, Distributed Systems, etc.
3. "other_skills": Include non-technical skills like interpersonal, leadership, and teamwork abilities. Examples include Communication skills, Managerial roles, Cross-team collaboration, etc.
4. "required_skills": All skills specifically listed as required or expected from an ideal candidate. Include both technical and non-technical skills.
5. "nice_to_have": Any skills or qualifications listed as preferred or beneficial for the role but not mandatory.
Return the output in the following JSON format with no additional commentary:
{{
    "tech_stack": [],
    "technical_skills": [],
    "other_skills": [],
    "required_skills": [],
    "nice_to_have": []
}}

JOB DESCRIPTION:
{}
"""
"""
Use `extract_skills_prompt.format(job_description)` to insert `job_description`.
"""

#<

##> ------ Dheeraj Deshwal : dheeraj9811 Email:dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Feature ------
##> Answer Questions
# Structure of messages = `[{"role": "user", "content": answer_questions_prompt}]`

ai_answer_prompt = """
You are an intelligent AI assistant filling out a form and answer like human,.
Respond concisely based on the type of question:

1. If the question asks for **years of experience, duration, or numeric value**, return **only a number** (e.g., "2", "5", "10").
2. If the question is **a Yes/No question**, return **only "Yes" or "No"**.
3. If the question requires a **short description**, give a **single-sentence response**.
4. If the question requires a **detailed response**, provide a **well-structured and human-like answer and keep no of character <350 for answering**.
5. Do **not** repeat the question in your answer.
6. here is user information to answer the questions if needed:
**User Information:**
{}

**QUESTION Strat from here:**
{}
"""
#<


##> ------ Claude (Anthropic) prompts & schemas ------

# Anthropic `output_config.format` schema for skill extraction:
# `{"type": "json_schema", "schema": {...}}`.
claude_extract_skills_response_schema = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "tech_stack": array_of_strings,
            "technical_skills": array_of_strings,
            "other_skills": array_of_strings,
            "required_skills": array_of_strings,
            "nice_to_have": array_of_strings,
        },
        "required": [
            "tech_stack",
            "technical_skills",
            "other_skills",
            "required_skills",
            "nice_to_have",
        ],
        "additionalProperties": False,
    },
}
"""Anthropic structured-output schema reused for `claude_extract_skills`."""


# Job relevance / fit screening prompt.
# `.format(user_information_all, company_line, job_description)`:
#   {0} -> candidate profile, {1} -> " (Company: X)" or "", {2} -> job description
job_relevance_prompt = """You are screening job postings for one specific candidate.
Given the candidate's profile and a job posting, judge how well the role fits the
candidate's experience, core tech stack, role type, and seniority.

Score the match from 0 to 100:
- 80-100: excellent fit — core stack, role type, and seniority align strongly.
- 50-79: reasonable fit — meaningful overlap, worth applying.
- 1-49: weak fit — different stack, seniority mismatch, or only loosely related.
- 0: not a relevant software/engineering role for this candidate at all.

Be objective and decisive. Reward overlap in core technologies, role type, and
seniority. Penalize hard mismatches: a stack the candidate does not have, a
junior/intern role for a senior candidate (or vice versa), a non-engineering role,
required years of experience far above the candidate's, or a primary language the
candidate is explicitly avoiding.

Also detect whether the posting asks the candidate to APPLY BY EMAIL (e.g. "send your
CV to ...", "email your resume to ...", "apply at name@company.com"). If so, extract
the exact email address and the requested subject line (if any).

Return ONLY a JSON object with these keys:
- "match_score": integer from 0 to 100
- "recommend_apply": boolean
- "reasons": one or two short sentences explaining the score
- "matched_skills": array of skills the candidate has that the job wants
- "missing_skills": array of important skills the job wants that the candidate lacks
- "apply_by_email": boolean — true ONLY if the posting instructs applying via email
- "apply_email": the email address to send the application to, or "" if none
- "email_subject": the exact subject line the posting asks for, or "" if none specified

CANDIDATE PROFILE:
{0}

JOB POSTING{1}:
{2}
"""

# Anthropic `output_config.format` schema for the relevance verdict.
# (Structured outputs do not support numeric min/max, so the 0-100 range is
# enforced by the prompt rather than the schema.)
job_relevance_response_schema = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "match_score": {"type": "integer"},
            "recommend_apply": {"type": "boolean"},
            "reasons": {"type": "string"},
            "matched_skills": array_of_strings,
            "missing_skills": array_of_strings,
            "apply_by_email": {"type": "boolean"},
            "apply_email": {"type": "string"},
            "email_subject": {"type": "string"},
        },
        "required": [
            "match_score",
            "recommend_apply",
            "reasons",
            "matched_skills",
            "missing_skills",
            "apply_by_email",
            "apply_email",
            "email_subject",
        ],
        "additionalProperties": False,
    },
}
"""Anthropic structured-output schema for `claude_check_job_relevance`."""
#<