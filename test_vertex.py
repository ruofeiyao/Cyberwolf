from google import genai
from google.genai.types import HttpOptions

PROJECT_ID = "bold-passkey-418620"
LOCATION = "us-central1"

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
    http_options=HttpOptions(api_version="v1"),
)

resp = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="You are a Werewolf player. Say one short strategic sentence in English."
)

print(resp.text)