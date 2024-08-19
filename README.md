# NOT didactic-octo-guacamole
> Don't worry about the repo name - I let GitHub autogenerate this, because it's memorable :)  

Using Python w/  OpenAI's language models (LLMs). By leveraging OpenAI's powerful API, you can create intelligent scripts to handle various automated tasks with natural language processing.

## Requirements

- Python 3.x
- `openai` library
- `.env` file with `OPENAI_API_KEY`

## Setup

1. **Install Dependencies**

   ```bash
   pip install openai python-dotenv
   ```

2. **Create a `.env` File**

   ```plaintext
   OPENAI_API_KEY=your_openai_api_key
   ```

###  **[`Helper Script`](./helper_functions.py)**

   - **`request_completion(prompt, model)`**: requests a completion from OpenAI's LLM.
   - **`print_llm_response(prompt)`**: prints the response of the model for a given prompt.
   - **`get_llm_response(prompt)`**: returns the model’s response as a string.
   - **`get_chat_completion(prompt, history)`**: retrieves a response considering the conversation history.

### **[`Helper Script`](./helper_functions.py)** - Shortened;

```python
import openai
from dotenv import load_dotenv
import os

# load API key
load_dotenv('.env')
openai.api_key = os.getenv('OPENAI_API_KEY')

# define the model
MODEL = 'gpt-4' # has to be a valid model name

def request_completion(prompt, model):
    '''requests completion from OpenAI.'''
    completion = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return completion.choices[0].message['content']

# sample usage
response = request_completion("How can I automate tasks with Python?", MODEL)
print(response)
```

