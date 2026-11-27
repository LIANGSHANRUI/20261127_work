#消息类型

from langchain.messages import HumanMessage, AIMessage, SystemMessage

from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="qwen4-max",api_key="sk-ws-H.XDMIIPR.51wT.MEUCIQCDjMFzBh7urRi-3KsXQrkiKCLo3eumedEdF5WDu53ADwIgfhGUe6jLeFk--wkPNSIGo-R7XafeNoAjm7jhvSnmkuM",base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    temperature=1.2,
                    top_p=0.9,
                    extra_body={"enable_thinking": False}
                   )


#构建发给模型的内容 使用消息列表
messages = [
  {"role": "system", "content": """你是一个聊天助手，你的语言风格很幽默，可以参考郭德纲的语言风格，可以适当使用网络流行语"""}  
]


while True:
    user_input = input("请输入：")
    messages.append(HumanMessage(content=user_input))
    res = model.invoke(messages)
    messages.append(res)
    print(res.content)