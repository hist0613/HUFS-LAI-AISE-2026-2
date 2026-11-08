from openai import OpenAI

client = OpenAI(api_key="placeholder", base_url="https://oss-japa.hufs.jae.one/v1")

response = client.chat.completions.create(
    model="placeholder", messages=[{"role": "user", "content": "한국외대 설명 ㄱㄱ"}]
)

print("content:", response.choices[0].message.content)
print("reasoning:", response.choices[0].message.reasoning_content)
