from langchain_classic.memory import ConversationBufferWindowMemory
from langchain_core.messages import AIMessage, HumanMessage

from app.models import ChatMessage, MessageRole

HISTORY_WINDOW = 4


def chat_messages_to_langchain(messages: list[ChatMessage]) -> list[HumanMessage | AIMessage]:
    recent = messages[-HISTORY_WINDOW:] if len(messages) > HISTORY_WINDOW else messages
    langchain_messages: list[HumanMessage | AIMessage] = []
    for message in recent:
        if message.role == MessageRole.USER:
            langchain_messages.append(HumanMessage(content=message.content))
        else:
            langchain_messages.append(AIMessage(content=message.content))
    return langchain_messages


def build_conversation_buffer(messages: list[ChatMessage]) -> ConversationBufferWindowMemory:
    memory = ConversationBufferWindowMemory(
        k=HISTORY_WINDOW,
        return_messages=True,
        memory_key="chat_history",
    )
    for message in messages:
        if message.role == MessageRole.USER:
            memory.chat_memory.add_user_message(message.content)
        else:
            memory.chat_memory.add_ai_message(message.content)
    return memory


def get_buffered_chat_history(messages: list[ChatMessage]) -> list[HumanMessage | AIMessage]:
    memory = build_conversation_buffer(messages)
    variables = memory.load_memory_variables({})
    history = variables.get("chat_history", [])
    return list(history)
