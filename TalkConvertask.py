import re 
import json
import requests

def Convertask(prompt, response_schema = None):
    try:
        print("Connecting")
        response = requests.post(
            "http://host.docker.internal:11434/api/generate", 
            headers = {"Content-Type" : "application/json"}, 
            data = json.dumps({
                "model": "llama3:8b-instruct-16k", 
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "seed": 42,
                    "num_predict": 8192,
                    "repeat_penalty": 1.2,
                    "num_ctx" : 16384
                    
            }
        })
        )

        response.raise_for_status()
        output = response.json()

        if output.get("response"):
            raw_output = output["response"]

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
            print(f"[ERROR] Ollama API response structure unexpected (no 'response' key): {output}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request to Ollama API failed: {e}")
        return None
    

BASE_PROMPT = """
You are a highly intelligent strategic advisor and operations expert.

You will be given a transcript of a founder or team discussing their ideas, plans, or goals for a startup or venture studio. Your task is to carefully read the transcript, understand the core intent, and generate a clear, insightful, and structured response.

❗Avoid giving explanations of your process. DO NOT include "thinking", reflections, or your reasoning. Your job is to generate the final output ONLY.

⚠️Prompt for Integrating Additional User Input:
"In addition to the primary analysis of the transcript, you will also receive an 'Additional User Prompt.' 
Your task is to carefully consider this prompt and integrate its requirements into your final output.
If the 'Additional User Prompt' is related to the transcript: Incorporate its directives seamlessly into your analysis and structured response, leveraging information from the transcript where relevant. Adapt your output structure to best address both.
If the 'Additional User Prompt' is distinct or unrelated: Address it comprehensively and independently within your response. You may create a separate section for it or adjust the overall flow to provide the most helpful answer, clearly acknowledging its distinction from the transcript's main content."
If its empty, give it out "null"
🎯 Your response should:
- Understand the context and purpose of the transcript (e.g., pitch, planning, operations, team, fundraising, roadmap).
- Summarize the key themes, ideas, and initiatives.


⚠️⚠️ CRITICAL INSTRUCTIONS:
- NO explanations, NO thinking process, NO reasoning
- NO phrases like "First, I need to", "Let me break this down", "Putting this together"
- Start IMMEDIATELY with the structured output
- Be direct and actionable only

📌 Output Structure Guidelines:
- You may use sections like:
  - Vision / Goals
  - Key Projects
  - Risks & Roadblocks
  - Next Steps
  - Resources or Team Needs
- BUT: Only use these if relevant. You may invent better headings if the content suggests so.
- The goal is **clarity, structure, and actionability** — not rigid templates.

❗Avoid:
- Explanations or reasoning
- Loose text blocks without formatting

📝 Output Format Instructions (MANDATORY):
- Use clear **Markdown** structure:
    - `##` for main sections (e.g., ## Vision / Long-term Goals)
    - `###` for sub-sections
    - `-` for bullet points
    - `**Bold**` for key labels or highlights
- Always begin with a title: `## Convertask Strategic Plan`
- Do NOT include free-flowing paragraphs without structure
- No explanation, reasoning, or filler

❗Avoid giving explanations of your process. DO NOT include "thinking", reflections, or your reasoning. Your job is to generate the final output ONLY.

Now process the following transcript:

{transcript_text}
"""


        
def clean_response(raw_response):
    if not raw_response:
        return raw_response
    
    unwanted_phrases = [
          
        r"Okay, so I'm trying to help.*?Now he's asking for a plan\.",
        r"First, I need to figure out.*?Let me break this down into actionable steps\.",
        r"Putting all this together.*?structured plan",
        r"Let me.*?",
        r"I think.*?",
        r"Maybe.*?",
        r"Perhaps.*?",
        r"So.*?",
        r"Well.*?",
        r"Hmm.*?",
        r"Looking back, in the initial conversation,*?",
    ]
    cleaned = raw_response
    for phrase in unwanted_phrases:
        cleaned = re.sub(phrase, "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    lines = cleaned.split('\n')
    start_idx = 0

    for i, line in enumerate(lines):
        if (line.strip().startswith('#') or 
            line.strip().startswith('**') or
            'Strategic Plan' in line or
            'Action Plan' in line or
            'Actionable Plan' in line):
            start_idx = i
            break
    
    if start_idx > 0:
        cleaned = '\n'.join(lines[start_idx:])
    
    return cleaned.strip()


def Convertask_AI(transcript_text: str, user_prompt_1: str = "") -> dict:
    if not transcript_text or not transcript_text.strip():
        return {"error": "Transcript text is empty for summarization."}
    
    prompt_info_1 = f"Additional prompt from user: {user_prompt_1}" if user_prompt_1 else ""
    all_input = f"Transcript:\n{transcript_text} \n  {prompt_info_1} "
    summary_prompt = BASE_PROMPT.format(
        transcript_text=all_input
    )
    
    structured_summary = Convertask(summary_prompt)

    if structured_summary is None:
        print("[ERROR] Failed to get structured summary from LLM.")
        return {"error": "Failed to generate structured summary. LLM response was problematic."}
    
    cleaned_summary = clean_response(structured_summary)
    return {"plan": cleaned_summary}


    

    

        