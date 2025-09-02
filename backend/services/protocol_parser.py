import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

genai.configure(api_key=GEMINI_API_KEY)

# Set up the model
generation_config = {
  "temperature": 0.1,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 8192,
}

model = genai.GenerativeModel(model_name="gemini-2.5-flash",
                              generation_config=generation_config)

def get_extraction_prompt():
    return """
    You are a highly skilled medical data analyst. Your task is to analyze the provided text from a clinical protocol and extract all mentions of medications (лекарственные средства).
    For each medication found, you must extract the following details and return them as a JSON object.

    The JSON output should be a list of objects, where each object represents a single medication entry.

    Here is the required JSON schema for each medication object:
    {
      "drug_name_source": "The exact name of the drug as mentioned in the text (e.g., 'Ацетилсалициловая кислота', 'Ибупрофен').",
      "dosage_source": "The dosage and regimen as mentioned in the text (e.g., '75-150 мг/сут', 'по 1 таблетке 2 раза в день').",
      "route_source": "The route of administration as mentioned in thetext (e.g., 'внутрь', 'в/в капельно').",
      "evidence_level_source": "The level of evidence (УДД/УУР) if mentioned for this drug in the text (e.g., 'A1', 'C5'). If not present, use null.",
      "context_indication": "The clinical context or indication for which the drug is prescribed, based on the surrounding text."
    }

    Analyze the following text and provide the output in a single valid JSON list. Do not include any explanatory text or markdown formatting before or after the JSON.

    Text to analyze:
    ---
    {text}
    ---
    """

async def extract_drugs_from_text(text: str) -> list:
    """
    Uses Gemini to extract drug information from text parsed from a clinical protocol.
    """
    if not text:
        return []

    prompt = get_extraction_prompt().format(text=text)

    try:
        response = await model.generate_content_async(prompt)

        # Clean the response more thoroughly to get only the JSON part
        json_response_text = response.text.strip()
        
        # Remove markdown code blocks
        json_response_text = json_response_text.replace("```json", "").replace("```", "")
        
        # Remove any leading/trailing whitespace and newlines
        json_response_text = json_response_text.strip()
        
        # Find the first '[' and last ']' to extract just the JSON array
        start_idx = json_response_text.find('[')
        end_idx = json_response_text.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_response_text = json_response_text[start_idx:end_idx + 1]
        
        # Additional cleanup for common issues
        json_response_text = json_response_text.replace('\n', ' ').replace('\r', ' ')
        
        print(f"Cleaned JSON response: {json_response_text[:200]}...")  # Debug log

        # Parse the JSON string into a Python list of dictionaries
        extracted_data = json.loads(json_response_text)
        
        # Validate that we got a list
        if not isinstance(extracted_data, list):
            print(f"Expected list but got {type(extracted_data)}")
            return []
            
        return extracted_data
    except Exception as e:
        # Handle potential errors, e.g., JSON parsing errors or API errors
        print(f"Error during Gemini extraction: {e}")
        print(f"Raw response text: {response.text if 'response' in locals() else 'No response'}")
        # In a real app, you'd want more robust error handling/logging
        return {"error": "Failed to extract data using AI", "details": str(e)}
