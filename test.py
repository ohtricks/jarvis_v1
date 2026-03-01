from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4000",
    api_key="anything"
)

response = client.chat.completions.create(
    model="brain",
    messages=[
        {"role": "user", "content": "Diga: Jarvis online"}
    ]
)

print(response.choices[0].message.content)