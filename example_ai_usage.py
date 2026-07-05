"""
Example script demonstrating how to use the GLM_AI utility class.
"""

from utils import GLM_AI

def run_ai_example():
    """Initializes the AI client and runs a sample conversation."""
    print("Initializing AI client...")
    
    try:
        # Create an instance of the AI client.
        # The API key is already hardcoded in the GLM_AI class.
        # You can specify the model, for example, "glm-4.6".
        ai_client = GLM_AI(model="glm-4.6")

        # Prepare the messages for the AI.
        # This can be a simple question or a more complex conversation history.
        messages_to_send = [
            {
                "role": "system",
                "content": "You are a helpful assistant that analyzes sentiment."
            },
            {
                "role": "user",
                "content": "Analyze the sentiment of this comment: 'This video is amazing, I love it!'"
            }
        ]

        print("Sending request to the AI...")
        # Call the chat method to get a response.
        ai_response = ai_client.chat(messages_to_send)
        
        print("\n--- AI Response ---")
        print(ai_response)
        print("-------------------")

    except Exception as e:
        print(f"An error occurred while running the AI example: {e}")

if __name__ == "__main__":
    run_ai_example()
