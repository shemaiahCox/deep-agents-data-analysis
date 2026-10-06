# ---- Data Analysis ----
# A simple example of a data analysis agent that uses a custom tool to send messages to Slack.

# -- Imports --

import csv
import io
import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_core.utils.uuid import uuid7
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from slack_sdk import WebClient

# -- Load environment variables --
# This is a simple example of how to load environment variables from a .env file.

load_dotenv()
# llama3.1:8b returns real Ollama tool calls and fits a 16 GB Mac.
# num_ctx has to cover the deep-agent prompt plus the tool list.
olla_model = ChatOllama(model="llama3.1:8b", temperature=0, num_ctx=16384)

# ---- Local shell backend ----
# Runs file and shell commands on this machine. No isolation.

workspace = Path(__file__).parent / "workspace"
workspace.mkdir(exist_ok=True)
backend = LocalShellBackend(root_dir=workspace, inherit_env=True)

# ---- Import data ----

# Create sample sales data
data = [
    ["Date", "Product", "Units Sold", "Revenue"],
    ["2025-08-01", "Widget A", 10, 250],
    ["2025-08-02", "Widget B", 5, 125],
    ["2025-08-03", "Widget A", 7, 175],
    ["2025-08-04", "Widget C", 3, 90],
    ["2025-08-05", "Widget B", 8, 200],
]

# Convert to CSV bytes
text_buf = io.StringIO()
writer = csv.writer(text_buf)
writer.writerows(data)
csv_bytes = text_buf.getvalue().encode("utf-8")
text_buf.close()

# Upload to backend
backend.upload_files([("/data/sales_data.csv", csv_bytes)])

# ---- Custom tools ----


slack_token = os.environ["SLACK_USER_TOKEN"]
slack_client = WebClient(token=slack_token)
channel = "C0C6TPUFU85"  # specify your own channel here

@tool(parse_docstring=True)
def slack_send_message(text: str, file_path: str | None = None) -> str:
    """Send message, optionally including attachments such as images.

    Args:
        text: (str) text content of the message
        file_path: (str) file path of attachment in the filesystem.
    """
    if not file_path:
        slack_client.chat_postMessage(channel=channel, text=text)
    else:
        fp = backend.download_files([file_path])
        slack_client.files_upload_v2(
            channel=channel,
            content=fp[0].content,
            initial_comment=text,
        )

    return "Message sent."


# ---- Create agent ----

checkpointer = InMemorySaver()

agent = create_deep_agent(
    model=olla_model,
    tools=[slack_send_message],
    system_prompt=(
        "Do this in two separate turns, one tool call each.\n"
        "1. Call execute once. Run Python that reads data/sales_data.csv and "
        "writes a PNG to data/sales_plot.png. Use matplotlib and do not call plt.show().\n"
        "2. After execute succeeds, call slack_send_message once. "
        "Pass only text and file_path='/data/sales_plot.png'. "
        "Do not pass a shell command, and do not invent a file path."
    ),
    backend=backend,
    checkpointer=checkpointer,
)

thread_id = str(uuid7())
config = {"configurable": {"thread_id": thread_id}}

# ---- Run agent ----

input_message = {
    "role": "user",
    "content": (
        "Analyze data/sales_data.csv, save a plot to data/sales_plot.png, "
        "then send the analysis and the plot to Slack."
    ),
}
stream = agent.stream_events(
    {"messages": [input_message]},
    config,
    version="v3",
)
for snapshot in stream.values:
    snapshot["messages"][-1].pretty_print()