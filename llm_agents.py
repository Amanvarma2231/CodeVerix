"""
LLM Agent Base Classes
Two specialized LLM agents:
  - CoderLLM  : generates Python code
  - ValidatorLLM : validates/reviews code and returns structured feedback
"""

import os
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
#  Provider helpers
# ─────────────────────────────────────────────

def _call_gemini(model: str, system_prompt: str, user_message: str, api_key: str) -> str:
    """Call Google Gemini API (uses new google-genai SDK)."""
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
            )
        )
        return response.text
    except ImportError:
        # Fallback to deprecated SDK if new one not installed
        import google.generativeai as genai_old
        genai_old.configure(api_key=api_key)
        full_model = genai_old.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt
        )
        response = full_model.generate_content(user_message)
        return response.text


def _call_openai(model: str, system_prompt: str, user_message: str, api_key: str) -> str:
    """Call OpenAI API."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ]
    )
    return resp.choices[0].message.content


def call_llm(model: str, system_prompt: str, user_message: str) -> str:
    """Unified LLM caller - picks provider from env."""
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        return _call_openai(model, system_prompt, user_message, api_key)
    else:
        api_key = os.getenv("GEMINI_API_KEY", "")
        return _call_gemini(model, system_prompt, user_message, api_key)


# ─────────────────────────────────────────────
#  Message dataclass
# ─────────────────────────────────────────────

class Message:
    """Represents one message in the LLM-to-LLM conversation."""
    def __init__(self, sender: str, role: str, content: str, msg_type: str = "text"):
        self.sender   = sender          # e.g. "CoderLLM", "ValidatorLLM"
        self.role     = role            # "coder" | "validator" | "system"
        self.content  = content
        self.msg_type = msg_type        # "text" | "code" | "validation" | "task"
        self.timestamp = datetime.now().strftime("%H:%M:%S")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender":    self.sender,
            "role":      self.role,
            "content":   self.content,
            "msg_type":  self.msg_type,
            "timestamp": self.timestamp,
        }


# ─────────────────────────────────────────────
#  CoderLLM
# ─────────────────────────────────────────────

CODER_SYSTEM = """You are CoderLLM, an expert Python developer.
Your job is to write clean, correct, and well-commented Python code.

When given a coding task:
1. Think step-by-step.
2. Write complete, runnable Python code.
3. Add docstrings and inline comments.
4. Format your response EXACTLY like this:

EXPLANATION:
<brief explanation of your approach>

```python
<your complete Python code here>
```

NOTES:
<any important notes or assumptions>

Do NOT add anything outside this format.
"""


class CoderLLM:
    """LLM agent that writes Python code."""

    def __init__(self):
        self.name  = "CoderLLM 🤖"
        self.model = os.getenv("CODER_MODEL", "gemini-1.5-flash")
        self.role  = "coder"

    def code(self, task: str, validator_feedback: Optional[str] = None) -> Message:
        """Generate code for a task, optionally incorporating validator feedback."""
        if validator_feedback:
            prompt = f"""Task: {task}

The ValidatorLLM reviewed your previous code and provided this feedback:
{validator_feedback}

Please fix the code based on the feedback and return the improved version."""
        else:
            prompt = f"Task: {task}\n\nWrite the Python code now."

        response = call_llm(self.model, CODER_SYSTEM, prompt)
        return Message(
            sender   = self.name,
            role     = self.role,
            content  = response,
            msg_type = "code"
        )


# ─────────────────────────────────────────────
#  ValidatorLLM
# ─────────────────────────────────────────────

VALIDATOR_SYSTEM = """You are ValidatorLLM, an expert Python code reviewer and QA engineer.
Your job is to rigorously review Python code written by CoderLLM.

For each piece of code you receive, check:
1. ✅ Correctness  - Does the logic work correctly?
2. ✅ Edge cases   - Are edge cases handled?
3. ✅ Best practices - PEP8, naming conventions, docstrings?
4. ✅ Security     - Any obvious security issues?
5. ✅ Performance  - Any obvious inefficiencies?

Format your response EXACTLY like this:

VALIDATION RESULT: PASS ✅  |  VALIDATION RESULT: FAIL ❌  (pick one)

SCORE: X/10

ISSUES FOUND:
- Issue 1 (severity: HIGH/MEDIUM/LOW)
- Issue 2 ...
(write "None" if no issues)

SUGGESTIONS:
- Suggestion 1
- Suggestion 2
(write "None" if no suggestions)

VERDICT:
<one paragraph summary of your overall assessment>

If PASS: state clearly the code is good to use.
If FAIL: state clearly what MUST be fixed before use.
"""


class ValidatorLLM:
    """LLM agent that validates code produced by CoderLLM."""

    def __init__(self):
        self.name  = "ValidatorLLM 🔍"
        self.model = os.getenv("VALIDATOR_MODEL", "gemini-1.5-pro")
        self.role  = "validator"

    def validate(self, task: str, code_message: str) -> Message:
        """Validate the code message produced by CoderLLM."""
        prompt = f"""Original Task: {task}

CoderLLM produced the following:
{code_message}

Please validate this code thoroughly."""

        response = call_llm(self.model, VALIDATOR_SYSTEM, prompt)
        return Message(
            sender   = self.name,
            role     = self.role,
            content  = response,
            msg_type = "validation"
        )

    def is_pass(self, validation_message: Message) -> bool:
        """Check if validation passed."""
        return "VALIDATION RESULT: PASS" in validation_message.content.upper()
