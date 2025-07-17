import dashscope

dashscope.api_key = 'sk-49dd3d589cfe4e55b72d63e35a771fff'

from dashscope import Generation

def generate_question(prompt: str) -> str:
    response = Generation.call(
        model="qwen-turbo",
        prompt=prompt,
        result_format="message"
    )

    return response.output.choices[0].message['content']
