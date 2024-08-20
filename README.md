# NOT didactic-octo-guacamole

Using Python w/  OpenAI's language models (LLMs). By leveraging OpenAI's powerful API, you can create intelligent scripts to handle  automated tasks with natural language processing.

<div style="
    background: linear-gradient(135deg, #0f7073, #203a43, #2c5364);
    border-radius: 10px;
    padding: 20px;
    color: white;
    font-family: Arial, sans-serif;
    text-align: left;
">
    <p>Don't worry about the repo name - I let GitHub autogenerate this, because it's memorable :)  </p>
</div>


## Requirements

- Python 3.12
- `openai` library
- `.env` file with `OPENAI_API_KEY`

## Setup

1. **Install Dependencies**

   ```bash
   # create virtaul environment if need be;
   pip install openai python-dotenv
   ```

2. **Create a `.env` File**

   ```plaintext
   OPENAI_API_KEY=your_openai_api_key
   ```
   ```bash
   # or export as environment variable;
   export OPENAI_API_KEY=your_openai_api_key 
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
response = request_completion('PokeAPI', MODEL)
print(response)
```
