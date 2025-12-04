from openai import OpenAI

client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

response = client.chat.completions.create(
    model="qwen/qwen3-4b-2507",
    messages=[
        {"role": "system", "content": "You are a high school teacher"},
        {"role": "user", "content": "How to solve 3x^2 + 5x - 2 = 0?"},
    ],
)

print(response.choices[0].message.content)
