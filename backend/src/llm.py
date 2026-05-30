# llm.py

import os
import json
import requests
from typing import Optional

from pydantic import BaseModel, Field

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from util import logger


# Clip the history for limited token
def clip_history(history: str, max_chars: int = 16000) -> str:
    if len(history) > max_chars:
        return history[-max_chars:]
    return history

def get_llm(llm_model, api_key):

    # openai case
    if "gpt" in llm_model.lower() or "o1" in llm_model.lower() or "o3" in llm_model.lower():
        from langchain_openai import ChatOpenAI
        os.environ["OPENAI_API_KEY"] = api_key
        llm = ChatOpenAI(temperature=0, model=llm_model, api_key=api_key).bind(response_format={"type": "json_object"})
        logger(f"Using OpenAI model: {llm_model}")

        return llm
    # cannot work now, need langchain fix error
    if "google" in llm_model.lower():
        logger("no suport google LLM")
        return None        

    # ollama case
    if llm_model:
        from langchain_ollama import ChatOllama
        ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")  # Default value if envvar is not set
        llm = ChatOllama(
            model=llm_model,
            base_url=ollama_base_url,
            format="json",
            temperature=0)

        logger(f"Using {llm_model}")
        return llm



def get_node_llm(llm_config: dict | None, global_llm, global_model: str, global_key: str):
    """
    Return the LLM for a single node.
    - If llm_config is None or use_default=True  → return the pre-built global_llm.
    - Otherwise build a fresh LLM from the node's own provider/model/api_key.
    """
    if not llm_config or llm_config.get("use_default", True):
        return global_llm

    provider = llm_config.get("provider", "openai")
    model = llm_config.get("model") or global_model
    key = llm_config.get("api_key") or global_key

    return get_llm(model, key) if provider == "openai" or "gpt" in model.lower() else get_llm(model, key)


def ChatBot(llm, question):
    # Define the prompt template
    template = """
        {question}
        you reply json in {{ reply:"<content>" }}
    """

    prompt = PromptTemplate.from_template(clip_history(template))

    # Format the prompt with the input variable
    formatted_prompt = prompt.format(question=question)

    llm_chain = prompt | llm | StrOutputParser()
    generation = llm_chain.invoke(formatted_prompt)
    
    data = json.loads(generation)
    reply = data.get("reply", "")

    return reply


def create_llm_chain(prompt_template: str, llm, history: str) -> str:
    """
    Creates and invokes an LLM chain using the prompt template and the history.
    """
    prompt = PromptTemplate.from_template(prompt_template)
    llm_chain = prompt | llm | StrOutputParser()
    inputs = {"history": history}
    generation = llm_chain.invoke(inputs)

    return generation

def create_llm_chain_google(prompt_template: str, llm, history: Optional[str] = None) -> str:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # If history exists, include it in the prompt
    full_prompt = f"{history}\n{prompt_template}, you reply in json file" if history else prompt_template
    
    data = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }]
    }
    
    params = {
        "key": "your google key"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, params=params)
        response.raise_for_status()
        
        json_response = response.json()
        
        # Extract the text from candidates[0].content.parts[0].text
        if (json_response.get("candidates") and 
            len(json_response["candidates"]) > 0 and 
            json_response["candidates"][0].get("content") and 
            json_response["candidates"][0]["content"].get("parts") and 
            len(json_response["candidates"][0]["content"]["parts"]) > 0):
            
            output = json_response["candidates"][0]["content"]["parts"][0]["text"]
        else:
            raise ValueError("Unexpected response structure from Gemini API")
            
        output = str(output)
        output = output[7:-3]
        output = json.dumps({"output": output})
        logger("printing:")        
        logger(output)

        return output

    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")
    except ValueError as e:
        raise Exception(f"Error processing response: {str(e)}")