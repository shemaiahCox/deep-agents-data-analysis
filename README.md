# deep-agents

A local data-analysis agent. It writes sample sales data, asks an [Ollama](https://ollama.com) model to plot it with matplotlib, then posts the analysis and the chart to Slack through a custom tool.

The agent is built with [Deep Agents](https://github.com/langchain-ai/deepagents) and `llama3.1:8b`.

## Prerequisites

- Python 3.12
- [Ollama](https://ollama.com) running locally
- A Slack user token that can post messages and upload files in your target channel

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull llama3.1:8b
cp .env.example .env
```

Edit `.env` and set `SLACK_USER_TOKEN`.

In `data_analysis.py`, replace the hardcoded Slack channel id with your own:

```python
channel = "C0C6TPUFU85"  # specify your own channel here
```

## Run

Ollama must be running and `llama3.1:8b` must already be pulled.

```bash
source .venv/bin/activate
python data_analysis.py
```

The script:

1. Writes `workspace/data/sales_data.csv`.
2. Asks the agent to plot that file to `workspace/data/sales_plot.png`.
3. Sends the analysis and the plot to the Slack channel.

## Configuration

| Variable | Required | Purpose |
| --- | --- | --- |
| `SLACK_USER_TOKEN` | Yes | Slack user token used by `slack_send_message` |
| `LANGSMITH_API_KEY` | No | Enables LangSmith tracing when set |
| `LANGSMITH_TRACING` | No | Set to `true` to turn tracing on |
| `LANGSMITH_PROJECT` | No | LangSmith project name |
| `LANGSMITH_ENDPOINT` | No | LangSmith API endpoint |

The model is `llama3.1:8b` with `num_ctx=16384`, chosen to fit a 16 GB Mac and the deep-agent prompt. Change it in `data_analysis.py` if you use a different Ollama model.
