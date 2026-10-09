import csv
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

# 1. Initialize LangSmith Sandbox Backend
client = SandboxClient()
ls_sandbox = client.create_sandbox()
backend = LangSmithSandbox(sandbox=ls_sandbox)

# 2. Upload Sample Sales Data to Sandbox
data = [
    ["Date", "Product", "Units Sold", "Revenue"],
    ["2025-08-01", "Widget A", 10, 250],
    ["2025-08-02", "Widget B", 5, 125],
    ["2025-08-03", "Widget A", 7, 175],
    ["2025-08-04", "Widget C", 3, 90],
    ["2025-08-05", "Widget B", 8, 200],
]

text_buf = io.StringIO()
writer = csv.writer(text_buf)
writer.writerows(data)
csv_bytes = text_buf.getvalue().encode("utf-8")
text_buf.close()

backend.upload_files([("/root/data/sales_data.csv", csv_bytes)])

# 3. Define Slack Integration Tool
slack_token = os.environ["SLACK_USER_TOKEN"]
slack_client = WebClient(token=slack_token)
channel = "C0123456ABC"  # Specify your target Slack channel ID


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


# 4. Create Deep Agent with Task Planning Middleware
checkpointer = InMemorySaver()

agent = create_deep_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[slack_send_message],
    backend=backend,
    checkpointer=checkpointer,
    middleware=[TodoListMiddleware()],
)

# 5. Execute Agent Stream
if __name__ == "__main__":
    thread_id = str(uuid7())
    config = {"configurable": {"thread_id": thread_id}}

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