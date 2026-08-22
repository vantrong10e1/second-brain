from pathlib import Path
from dotenv import load_dotenv
from langfuse import get_client

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / "config" / ".env")

langfuse = get_client()

with langfuse.start_as_current_observation(
    name="test-langfuse",
    as_type="span",
    input={"message": "Hello Langfuse"}
) as span:

    span.update(
        output={"message": "Langfuse is working!"}
    )

langfuse.flush()

print("Langfuse test finished!")