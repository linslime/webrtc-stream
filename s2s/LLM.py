from openai import OpenAI


def chat(text):
    print(text)
    result = None
    try:
        client = OpenAI(
            # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
            api_key="sk-1f727c797463408fafccd49a0140f504",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        
        completion = client.chat.completions.create(
            model="qwen-turbo",  # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
            messages=[
                {'role': 'system', 'content': 'You are my friend.'},
                {'role': 'user', 'content': text}
            ]
        )
        result = completion.choices[0].message.content
    except Exception as e:
        result = '不好意思，我不理解你的意思'
        print(f"错误信息：{e}")
        print("请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code")
    print(result)
    return result


if __name__ == "__main__":
    result = chat("你什么时候去上课")
    print(result)
    