import os
from zai import ZhipuAiClient
from typing import List, Dict, Optional

class GLM_AI:
    """A wrapper class for the ZhipuAI API to provide chat functionalities."""

    def __init__(self, api_key: str = "6e5c64b5def14289a42299b6d6bf9b25.hsfmUcWHCjfxk9J9", model: str = "glm-4.6"):
        """
        Initializes the ZhipuAI client.

        Args:
            api_key (str): The API key for ZhipuAI. Defaults to the hardcoded key.
            model (str): The model to use for the chat completion, e.g., 'glm-4.6'.
        """
        if not api_key:
            raise ValueError("API key cannot be empty.")
        
        self.client = ZhipuAiClient(api_key=api_key)
        self.model = model

    def chat(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = False, 
        temperature: float = 0.7, 
        top_p: float = 0.8,
        max_tokens: int = 32768
    ) -> str:
        """
        Creates a chat completion request and returns the response.

        Args:
            messages (List[Dict[str, str]]): A list of messages comprising the conversation so far.
            stream (bool): Whether to stream the response.
            temperature (float): Controls randomness. Lower is more deterministic.
            top_p (float): Nucleus sampling parameter.
            max_tokens (int): Maximum number of tokens to generate.

        Returns:
            str: The content of the AI's response.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=stream,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens
        )

        if stream:
            # This part is for handling streaming responses, not fully implemented for single return
            # You might want to yield chunks instead
            full_response = ""
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                full_response += content
            return full_response
        else:
            return response.choices[0].message.content

# Example usage block
if __name__ == "__main__":
    try:
        # Initialize the client. The API key is hardcoded in the class.
        ai_client = GLM_AI(model="glm-4.6")
        
        # Example conversation
        conversation = [
            {
                "role": "system",
                "content": "你是一个有用的AI助手。"
            },
            {
                "role": "user",
                "content": "你好，请介绍一下自己。"
            }
        ]
        
        print("Sending request to AI...")
        reply = ai_client.chat(conversation)
        print("\nAI Response:")
        print(reply)

    except Exception as e:
        print(f"An error occurred: {e}")