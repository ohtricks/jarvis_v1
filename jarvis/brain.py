from openai import OpenAI
import os

client = OpenAI(
    api_key="anything",
    base_url="http://localhost:4000/v1"
)

def ask_brain(messages):
    response = client.chat.completions.create(
        model="brain",
        messages=messages,
        temperature=0.3
    )

    return response.choices[0].message.content