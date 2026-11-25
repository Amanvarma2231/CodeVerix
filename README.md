# CodeVerix 🤖 — LLM-to-LLM Communication System

> **Internship Task** | Druidot Consulting Private Limited | Python Development

---

## 📋 What This Does

CodeVerix is a **human-observable, multi-round LLM-to-LLM communication system** where:

1. **CoderLLM** receives a coding task and writes Python code
2. **ValidatorLLM** reviews the code and provides structured feedback
3. If validation **fails** → feedback is sent back to CoderLLM for fixes
4. The loop continues until the code **passes** or max rounds is reached
5. **Humans can watch every message in real time** via the web UI or CLI

```
 Human Input
      │
      ▼
 Orchestrator
  ┌───────────┐
  │ CoderLLM  │──── writes code ────►
  └───────────┘                      │
                                     ▼
  ┌──────────────┐           ValidatorLLM
  │  PASS ✅     │◄─── validates ────┤
  │  FAIL ❌     │    (loops back)   │
  └──────────────┘
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Key
```bash
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY (free at https://aistudio.google.com)
```

### 3. Run the Web App
```bash
streamlit run app.py
```

### 4. OR Run from CLI
```bash
# Single task
python run_cli.py "Write a Python function to find prime numbers up to N"

# Interactive mode
python run_cli.py
```

### 5. Run Tests
```bash
python test_system.py
```

---

## 📁 Project Structure

```
CodeVerix/
├── app.py              # Streamlit web dashboard (main UI)
├── llm_agents.py       # CoderLLM and ValidatorLLM agent classes
├── orchestrator.py     # Conversation loop orchestrator
├── run_cli.py          # CLI runner with rich output
├── test_system.py      # Unit tests (all pass without API key)
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
└── README.md           # This file
```

---

## ⚙️ Configuration

| Variable          | Description                          | Default              |
|-------------------|--------------------------------------|----------------------|
| `LLM_PROVIDER`    | `gemini` or `openai`                 | `gemini`             |
| `GEMINI_API_KEY`  | Google Gemini API key                | —                    |
| `OPENAI_API_KEY`  | OpenAI API key (optional)            | —                    |
| `CODER_MODEL`     | Model for CoderLLM                   | `gemini-1.5-flash`   |
| `VALIDATOR_MODEL` | Model for ValidatorLLM               | `gemini-1.5-pro`     |

---

## 🔑 Getting a Free Gemini API Key

1. Go to [https://aistudio.google.com](https://aistudio.google.com)
2. Sign in with your Google account
3. Click **"Get API key"**
4. Copy the key into your `.env` file

---

## ✅ Features

- [x] Two distinct LLM agents (Coder & Validator)
- [x] Human-observable conversation (all messages visible)
- [x] Multi-round feedback loop (up to N rounds)
- [x] Streamlit web dashboard with live updates
- [x] CLI runner with rich terminal output
- [x] JSON conversation export
- [x] Works with Gemini (free) and OpenAI (paid)
- [x] Full unit test suite (no API key needed)
- [x] Quick task examples in UI

---

## 🧪 Running Tests (No API Key Needed)

```bash
python test_system.py
```

Expected output:
```
test_always_fail ................. ok
test_fail_then_pass .............. ok
test_history_dict_format ......... ok
test_on_message_callback ......... ok
test_pass_on_first_round ......... ok
...
Ran 10 tests in 0.03s
OK
```

---

*Built for Druidot Consulting Python Development Internship*
