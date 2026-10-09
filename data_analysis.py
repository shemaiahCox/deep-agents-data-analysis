# ---- Data Analysis ----
# A data analysis agent that runs in a LangSmith sandbox and sends results to Slack.

# -- Imports --

import csv
import getpass
import io
import os

from deepagents import create_deep_agent
from deepagents.backends.langsmith import LangSmithSandbox
from langchain.agents.middleware import TodoListMiddleware
from langchain.tools import tool
from langchain_core.utils.uuid import uuid7
from langgraph.checkpoint.memory import InMemorySaver
from langsmith.sandbox import SandboxClient
from slack_sdk import WebClient

# -- Load environment variables --
# LangSmith reads these when the sandbox client starts.

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = getpass.getpass()

# ---- LangSmith sandbox backend ----
# Runs the agent in a remote LangSmith sandbox.

client = SandboxClient()
ls_sandbox = client.create_sandbox()
backend = LangSmithSandbox(sandbox=ls_sandbox)

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
backend.upload_files([("/root/data/sales_data.csv", csv_bytes)])

# ---- Custom tools ----

slack_token = os.environ["SLACK_USER_TOKEN"]
slack_client = WebClient(token=slack_token)
channel = "C0123456ABC"  # specify your own channel here


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
    model="google_genai:gemini-3.6-flash",
    tools=[slack_send_message],
    backend=backend,
    checkpointer=checkpointer,
    middleware=[TodoListMiddleware()],
)

thread_id = str(uuid7())
config = {"configurable": {"thread_id": thread_id}}

# ---- Run agent ----

input_message = {
    "role": "user",
    "content": (
        "Analyze ./data/sales_data.csv in the current dir and generate a beautiful plot. "
        "When finished, send your analysis and the plot to Slack using the tool."
    ),
}
stream = agent.stream_events(
    {"messages": [input_message]},
    config,
    version="v3",
)
for snapshot in stream.values:
    snapshot["messages"][-1].pretty_print()
