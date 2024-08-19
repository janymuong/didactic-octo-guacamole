import os
import openai
from dotenv import load_dotenv
import time

# load the OpenAI API key from the .env file
load_dotenv('.env', override=True)
openai.api_key = os.getenv('OPENAI_API_KEY')

# define the models
PRIMARY_MODEL = "gpt-4o-mini"
FALLBACK_MODEL = "gpt-4o"

def request_completion(prompt, model):
    """Helper function to request completion from OpenAI."""
    try:
        completion = openai.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful but terse AI assistant who gets straight to the point.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        response = completion.choices[0].message['content']
        return response
    except Exception as e:
        if "rate limit" in str(e).lower():
            print("Rate limit exceeded. Trying fallback model.")
            return request_completion(prompt, FALLBACK_MODEL)
        else:
            print("Error:", str(e))
            return None

def print_llm_response(prompt):
    """This function takes as input a prompt and passes it to OpenAI's GPT-4 or GPT-4o Mini model.
    It then prints the response of the model.
    """
    try:
        if not isinstance(prompt, str):
            raise ValueError("Input must be a string enclosed in quotes.")
        response = request_completion(prompt, PRIMARY_MODEL)
        if response:
            print("_" * 100)
            print(response)
            print("_" * 100)
            print("\n")
    except ValueError as e:
        print("Error:", str(e))

def get_llm_response(prompt):
    """This function takes as input a prompt and passes it to OpenAI's GPT-4 or GPT-4o Mini model.
    It returns the response of the model as a string.
    """
    response = request_completion(prompt, PRIMARY_MODEL)
    return response

def get_chat_completion(prompt, history):
    """This function takes a prompt and conversation history, and passes it to OpenAI's GPT-4 
    or GPT-4o Mini model, returning the response.
    """
    history_string = "\n\n".join(["\n".join(turn) for turn in history])
    prompt_with_history = f"{history_string}\n\n{prompt}"
    response = request_completion(prompt_with_history, PRIMARY_MODEL)
    return response
