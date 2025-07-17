import requests
import json 
import re 
import os 

def AiModel(prompt, response_schema = None):
    try:
        print("Posting to Ollama")
        response = requests.post(
            "http://host.docker.internal:11434/api/generate", 
            headers={"Content-Type": "application/json"},
            data = json.dumps({
                "model": "mistral:7b-instruct-v0.2-q6_K", 
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0,
                    "seed": 42,
                    "num_predict": 8192,
                    "repeat_penalty": 1.1,
                    "num_ctx" : 16384
                    
            }
            })
        )

        response.raise_for_status()
        result = response.json()

        if result.get("response"):
            raw_output = result["response"]

            if response_schema:
                cleaned = raw_output.strip()
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError as e:
                    if cleaned.endswith('"null"') and not cleaned.endswith('}'):
                        try:
                            return json.loads(cleaned + "}")
                        except json.JSONDecodeError:
                            pass
                    if "```" in cleaned:
                        cleaned = re.sub(r"```json|```", "", cleaned).strip()

                    json_match = re.search(r"\{[\s\S]*\}", cleaned)

                    if json_match:
                        cleaned = json_match.group(0).strip()
                        json_str = json_match.group(0)
                        json_str = json_str.replace(": None", ": null")
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError as e:
                            print(f"[ERROR] Failed to decode JSON from Ollama response: {e}. Raw: {json_str[:500]}")
                            return None
                    if not json_match:
                        print(f"[ERROR] No JSON object found in Ollama response. Raw:\n{cleaned}")
                        return None
                    else:
                        print(f"[ERROR] No JSON object found in Ollama response when schema expected. Raw: {raw_output[:500]}")
                        return None
            else:
                return raw_output
        else:
            print(f"[ERROR] Ollama API response structure unexpected (no 'response' key): {result}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request to Ollama API failed: {e}")
        return None
    

TYPE_IDENTIFICATION_PROMPT = """
You are an intelligent assistant tasked with classifying the type of interaction from a given transcript.
Your response must be a **JSON object only** with a single key 'interaction_type' and its value being one of the following: 'Meeting', 'Brainstorm', 'Review', 'General Discussion', 'Unknown'.
Analyze the transcript content, vocabulary, and flow to determine the most fitting category.

Transcript:
{transcript_text}

Return ONLY the JSON object. Example: {{"interaction_type": "Meeting"}}
"""


TYPE_IDENTIFICATION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "interaction_type": {
            "type": "STRING",
            "enum": ["Meeting", "Brainstorm", "Review", "General Discussion", "Unknown"]
        }
    },
    "required": ["interaction_type"]
}
BASE_SUMMARY_PROMPT = """
You are an expert assistant that extracts structured insights from the provided transcript of a {interaction_type_here}.
Your task is to return ONLY a valid JSON object — no explanation, no markdown, no surrounding text.
If a user-provided context is given before the transcript, use it to guide your summary accordingly.
Keys to extract:
- 'summary': A concise overview of the main topics and outcomes. Note:- **SUMMARY IS VERY IMPORTANT, ALWAYS PROVIDE IT.**
- 'speaker_minutes': Key points or significant statements, potentially tagged with speaker labels if available in the transcript (e.g., 'Speaker X: ...'). If speaker labels are not present, provide main discussion points.
- 'actions': A numbered list of clear, actionable items that needs to be completed.
- 'decisions': Brief descriptions of any decisions made or conclusions reached.
- 'tasks': Clearly defined, actionable tasks. Can overlap with 'actions' but focus on work items.
- 'followups': Topics or issues that require further discussion or action in the future.
- 'deadlines': Any mentioned deadlines or due dates, with associated tasks if possible (e.g., "Complete report by EOD Friday").
- 'prompt_based': This field is for a specific user query. Since no specific user query is provided, return 'null'.

Return ONLY the JSON object. Do not provide any explanation or analysis. Your entire response MUST be a valid JSON object. If you cannot extract data, return empty strings or arrays as defined.

{{
  "summary": "...",
  "speaker_minutes": "...",
  "actions": ["...", "..."],
  "decisions": ["...", "..."],
  "tasks": ["...", "..."],
  "followups": ["...", "..."],
  "deadlines": ["...", "..."],
  "prompt_based": "null"
}}

🛑 Notes:
- You must return ONLY the JSON object — no explanation, no prose, no markdown, no triple backticks.
- If a field has no data, return an empty string `""` or an empty list `[]` as appropriate.
- For `prompt_based`, return `"null"` since no user query was provided.
- For `deadlines`, try to include task + due date if mentioned.
- The keys and structure must be exact — do not add or rename fields.

Transcript:
{transcript_text}
"""


SUMMARY_EXTRACTION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING"},
        "speaker_minutes": {"type": "STRING"},
        "actions": {"type": "ARRAY", "items": {"type": "STRING"}},
        "decisions": {"type": "ARRAY", "items": {"type": "STRING"}},
        "tasks": {"type": "ARRAY", "items": {"type": "STRING"}},
        "followups": {"type": "ARRAY", "items": {"type": "STRING"}},
        "deadlines": {"type": "ARRAY", "items": {"type": "STRING"}}
 
    },
    "required": ["summary", "speaker_minutes", "actions", "decisions", "tasks", "followups", "deadlines"]
}


def process_transcript_for_summary(transcript_text: str, user_prompt: str = "") -> dict:
    if not transcript_text or not transcript_text.strip():
        return {"error": "Transcript text is empty for summarization."}


    print("[INFO] Step 1: Identifying interaction type...")
    type_prompt = TYPE_IDENTIFICATION_PROMPT.format(transcript_text=transcript_text)
    
    type_response = AiModel(type_prompt, response_schema=TYPE_IDENTIFICATION_SCHEMA)

    interaction_type = "Unknown"
    if type_response and isinstance(type_response, dict) and "interaction_type" in type_response:
        interaction_type = type_response["interaction_type"]
        print(f"[INFO] Identified interaction type: {interaction_type}")
    else:
        print(f"[WARNING] Could not definitively identify interaction type. Ollama response: {type_response}. Defaulting to 'Unknown'.")

    
    print(f"[INFO] Step 2: Generating structured summary for {interaction_type}...")
    prompt_info = f"Context from user: {user_prompt}" if user_prompt else ""
    combined_input = f"{prompt_info}Transcript:\n{transcript_text}"
    summary_prompt = BASE_SUMMARY_PROMPT.format(
        interaction_type_here=interaction_type,
        transcript_text=combined_input
    )
    
    structured_summary = AiModel(summary_prompt, response_schema=SUMMARY_EXTRACTION_SCHEMA)

    if structured_summary is None:
        print("[ERROR] Failed to get structured summary from LLM.")
        return {"error": "Failed to generate structured summary. LLM response was problematic."}

    
    for key in ["actions", "decisions", "tasks", "followups", "deadlines"]:
        if isinstance(structured_summary.get(key), str):
           
            structured_summary[key] = [item.strip() for item in structured_summary[key].split(',') if item.strip()] if structured_summary[key] else []
        elif not isinstance(structured_summary.get(key), list):
            structured_summary[key] = [] 

    
    if structured_summary.get("prompt_based") == "":
        structured_summary["prompt_based"] = "null"



    structured_summary["interaction_type"] = interaction_type

    print("[INFO] Structured summary generated.")
    return structured_summary
