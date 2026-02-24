# AMD-Hack-Question-Answer-LLM

## ✨ AMD AI Premier League (AAIPL) — Question & Answer LLM Agents

This repository contains our solution for the AMD AI Premier League hackathon, where we built two LLM-based agents:

1. **Question Agent (Q-Agent)** — Generates puzzle-based logical reasoning questions from given topics.
2. **Answer Agent (A-Agent)** — Answers questions posed by opposing Q-Agents in a tournament format.

---

## 🏋️ Trained Models (HuggingFace)

| Agent | Model | Link |
|-------|-------|------|
| Answer Agent (SFT) | AAPIL_SFT_AAgent_final | [https://huggingface.co/Aayushktyagi/AAPIL_SFT_AAgent_final](https://huggingface.co/Aayushktyagi/AAPIL_SFT_AAgent_final) |
| Question Agent (GRPO) | AAPIL_GRPO_QAGent | [https://huggingface.co/Aayushktyagi/AAPIL_GRPO_QAGent](https://huggingface.co/Aayushktyagi/AAPIL_GRPO_QAGent) |

---

## 🚀 Main Training Notebooks

- **Answer Agent Training**: [Train_A-agent_Qwen.ipynb](Train_A-agent_Qwen.ipynb) — SFT fine-tuning of the Answer Agent using Qwen.
- **Question Agent Training**: [Train_Q_Agent_GRPO.ipynb](Train_Q_Agent_GRPO.ipynb) — GRPO training of the Question Agent.

---

## 📂 Project Structure

```
AAIPL/
├── agents/              # Agent wrappers and model definitions
│   ├── answer_agent.py
│   ├── answer_model.py
│   ├── question_agent.py
│   └── question_model.py
├── assets/              # Sample I/O formats, topics
├── data/                # Data processing scripts & generators
│   ├── generators/      # Synthetic data generation
│   └── parsers/         # Data format conversion
├── logical_reasoning/   # Logical reasoning data & sources
├── utils/               # Prompt building utilities
├── Train_A-agent_Qwen.ipynb   # ⭐ A-Agent training
├── Train_Q_Agent_GRPO.ipynb   # ⭐ Q-Agent training
├── eval_aagent.py             # A-Agent evaluation
├── verify_qagent.py           # Q-Agent verification
└── tutorial.ipynb             # Tutorial & tips
```

---

## 🏅 How It Works

- **Tournament format**: 1v1 knockout matches where teams alternate between asking and answering questions.
- **Q-Agent** generates N challenging logical reasoning questions from provided topics.
- **A-Agent** answers questions from the opposing team's Q-Agent.
- Final score = Q-Agent score + A-Agent score across two innings.

For full details, see [README.ipynb](README.ipynb).