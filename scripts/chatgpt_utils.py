import re
import openai

from scripts.json_utils import flatten_json_structure, try_parse_json
from modules import shared

def retry_query_chatgpt(messages, count, temperature, retries):
    chatgpt_answers = []

    for i in range(retries):
        try:
            is_last_retry = i == retries - 1 and retries > 1
            chatgpt_answers = query_chatgpt(messages, count, temperature, is_last_retry)

            if (len(chatgpt_answers) == count):
                return chatgpt_answers
        except Exception as e:
            if (i == retries - 1):
                raise e
            
            print(f"ChatGPT query failed. Retrying. Error: {e}")
        
        temperature = max(0.5, temperature - 0.3)
    
    if (len(chatgpt_answers) != count):
        raise Exception(f"ChatGPT answers doesn't match batch count. Got {len(chatgpt_answers)} answers, expected {count}.")

def query_chatgpt(messages, answer_count, temperature, is_last_retry = False):
    default_system_primer = f"Act like you are a terminal and always format your response as json. Always return exactly {answer_count} anwsers per question."
    default_chat_primer = f"I want you to act as a prompt generator. Compose each answer as a visual sentence. Do not write explanations on replies. Format the answers as javascript json arrays with a single string per answer. Return exactly {answer_count} to my question. Answer the questions exactly. Answer the following question:\r\n"

    system_primer = shared.opts.data.get("chatgpt_system_prompt", default_system_primer)
    chat_primer = shared.opts.data.get("chatgpt_user_prompt", default_chat_primer)    

    messages = normalize_text_for_chat_gpt(messages.strip())
    chat_request = f'{chat_primer}{messages}'

    if (is_last_retry):
        chat_request += f"\r\nReturn exactly {answer_count} answers to my question."

    print(f"ChatGPT request:\r\n{chat_request}\r\n")

    chat_gpt_response = get_chat_completion([ 
        to_message("system", system_primer),
        to_message("user", chat_request)
        ], temperature)    

    result = flatten_json_structure(try_parse_json(chat_gpt_response))

    if (result is None or len(result) == 0):
        print(f"ChatGPT response:\r\n")
        print(f"{chat_gpt_response.strip()}\r\n")
        raise Exception("Failed to parse ChatGPT response. See console for details.")
    
    return result

def to_message(user, content):
    return {"role": user, "content": content}

def normalize_text_for_chat_gpt(text):
    normalized = re.sub(r'(\.|:|,)[\s]*\n[\s]*', r'\1 ', text)
    normalized = re.sub(r'[\s]*\n[\s]*', '. ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized

def get_chat_completion(messages, temperature):
    completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages, temperature=temperature)
    response_content = completion.choices[0].message.content
    if response_content.sd_prompts is not None:
        return response_content.sd_prompts
    else:
        return response_content