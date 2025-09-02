import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# --- AI Configuration ---
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash")

def get_final_analysis_prompt(full_drug_data: dict) -> str:
    # Convert dict to a pretty JSON string for clear presentation in the prompt
    context_str = json.dumps(full_drug_data, indent=2, ensure_ascii=False)

    return f"""
    You are a clinical pharmacologist and an expert in evidence-based medicine. Your task is to provide a final analysis of a drug based on the comprehensive data provided below.

    **Provided Data:**
    ```json
    {context_str}
    ```

    **Your Tasks:**

    1.  **Generate a GRADE Evidence Level (ud_ai_grade):**
        Based on all the provided data (especially the source evidence level and the list of PubMed articles), assign a GRADE rating to the evidence for this drug's use in the specified indication.
        The rating must be one of: "High", "Moderate", "Low", or "Very Low".

    2.  **Provide a Brief Justification:**
        In one sentence, explain your reasoning for the assigned GRADE rating.

    3.  **Write a Short AI Summary Note (ai_summary_note):**
        In 1-2 sentences and in **Russian**, write a concise summary for a clinician. The summary should highlight the most critical information, such as the drug's regulatory status, evidence level, and any notable dosage concerns.

    **Output Format:**
    Your entire response must be a single, valid JSON object with the following keys. Do not include any other text or markdown.

    {{
      "ud_ai_grade": "...",
      "ud_ai_justification": "...",
      "ai_summary_note": "..."
    }}
    """

async def generate_ai_analysis(full_drug_data: dict) -> dict:
    """
    Generates the final AI analysis (GRADE score and summary) using Gemini.
    """
    prompt = get_final_analysis_prompt(full_drug_data)

    try:
        response = await gemini_model.generate_content_async(prompt)
        
        # Clean the response more thoroughly
        json_response_text = response.text.strip()
        json_response_text = json_response_text.replace("```json", "").replace("```", "")
        json_response_text = json_response_text.strip()
        
        # Find the first '{' and last '}' to extract just the JSON object
        start_idx = json_response_text.find('{')
        end_idx = json_response_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_response_text = json_response_text[start_idx:end_idx + 1]
        
        # Remove newlines that might break JSON parsing
        json_response_text = json_response_text.replace('\n', ' ').replace('\r', ' ')
        
        print(f"Cleaned AI analysis JSON: {json_response_text[:200]}...")  # Debug log
        
        analysis = json.loads(json_response_text)
        return analysis
    except Exception as e:
        print(f"Error during final AI analysis: {e}")
        print(f"Raw response text: {response.text if 'response' in locals() else 'No response'}")
        return {
            "ud_ai_grade": "Error",
            "ud_ai_justification": "Failed to generate AI analysis.",
            "ai_summary_note": "Ошибка при генерации финального анализа."
        }
