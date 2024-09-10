from dotenv import load_dotenv
import os
import gradio as gr
from groq import Groq
from swarmauri.standard.agents.concrete.SimpleConversationAgent import SimpleConversationAgent
from swarmauri.standard.conversations.concrete.MaxSystemContextConversation import MaxSystemContextConversation
from swarmauri.standard.llms.base.LLMBase import LLMBase
from pydantic import BaseModel, Field
from typing import Any, Dict

# Load environment variables from .env file
load_dotenv()

# Initialize Groq client
groq_api_key = os.getenv("GROQ_API_KEY")  # Use the environment variable for security
groq_client = Groq(api_key=groq_api_key)

# Define available models
available_models = [
    "llama3-8b-8192",
    "llama2-70b-4096",
    "mixtral-8x7b-32768",
    "gemma-7b-it",
]

# Simple Message class
class Message(BaseModel):
    content: str
    role: str = "assistant"

# Custom GroqModel class to integrate with SwarmAuri
class CustomGroqModel(LLMBase):
    client: Any = Field(default=None)
    model_name: str = Field(default="")
    
    class Config:
        protected_namespaces = ()
    
    def __init__(self, client: Any, model_name: str):
        super().__init__()
        self.client = client
        self.model_name = model_name

    def generate(self, prompt: str, previous_messages: list) -> Message:
        messages = previous_messages + [{"role": "user", "content": prompt}]
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model_name,
            )
            content = chat_completion.choices[0].message.content
            return Message(content=content)
        except Exception as e:
            return Message(content=f"Error: {str(e)}")

# Store conversation history for each model
conversation_histories = {model: [] for model in available_models}

# Initialize conversations and agents for each model
system_context = "You are a helpful assistant. Provide detailed responses."
conversations = {model: MaxSystemContextConversation(system_context=system_context) for model in available_models}
agents = {model: SimpleConversationAgent(conversation=conversations[model], llm=CustomGroqModel(groq_client, model)) for model in available_models}

# Define a function to generate a response
def generate_response(model_name, user_input):
    history = conversation_histories[model_name]
    agent = agents[model_name]
    response = agent.llm.generate(user_input, history)  # Pass history to generate
    # Update conversation history
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": response.content})
    return response.content

# Create the Gradio interface
iface = gr.Interface(
    fn=generate_response,
    inputs=[
        gr.Dropdown(choices=available_models, label="Select Model"),
        gr.Textbox(label="Enter your message:", lines=2, placeholder="Type your message here..."),
    ],
    outputs=gr.Textbox(label="Response:"),
    title="Chatbot with SwarmAuri, Groq, and Gradio",
    description="Select a model from the dropdown and enter your message to get a response.",
)

# Launch the Gradio interface
iface.launch()



