import dashscope
from pathlib import Path

dashscope.api_key = "sk-49dd3d589cfe4e55b72d63e35a771fff"


def call_llm_with_context(text: str, question: str) -> str:
    prompt_template = Path("prompt_template.txt").read_text(encoding="utf-8")
    prompt = prompt_template.replace("{{context}}", text)

    try:
        response = dashscope.Generation.call(
            model='qwen-turbo',
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": question}
            ],
            result_format='message',
            temperature=0.7
        )

        if not response or "output" not in response:
            raise ValueError("LLM 返回为空或格式错误")

        # print("🔍 通义返回：", response)

        return response.output.choices[0].message.content

    except Exception as e:
        print("❌ 通义千问调用失败：", e)
        raise RuntimeError("LLM 调用失败：" + str(e))