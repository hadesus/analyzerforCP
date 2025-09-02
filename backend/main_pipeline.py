import asyncio
import io
from docx import Document

# Import all our services
from services import protocol_parser
from services import drug_normalizer
from services import regulatory_checker
from services import pubmed_client
from services import ai_analyzer

# Instantiate clients/services that need it
pubmed = pubmed_client.PubMedClient()

async def generate_document_summary(full_text: str) -> str:
    """Uses Gemini to generate a brief summary of the entire document."""
    if not full_text:
        return "Текст документа пуст."

    prompt = f"""
    Проанализируй следующий текст из клинического протокола и напиши краткое резюме из 3-5 предложений.
    Резюме должно обобщать ключевые темы документа, такие как основное заболевание, целевая популяция пациентов и общие подходы к лечению.

    Текст для анализа:
    ---
    {full_text[:10000]}
    ---
    """
    try:
        # Using the same model as the other services for consistency
        response = await ai_analyzer.gemini_model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating document summary: {e}")
        return "Не удалось сгенерировать общее резюме для документа."


async def process_single_drug(drug_info: dict):
    """
    Processes a single drug through the complete analysis pipeline.
    Returns comprehensive data including normalization, regulatory checks, and literature.
    """
    source_name = drug_info.get("drug_name_source")
    if not source_name:
        print(f"Skipping drug with no source name: {drug_info}")
        return None

    print(f"Processing drug: {source_name}")
    
    normalization_result = await drug_normalizer.normalize_drug(source_name)
    inn_name = normalization_result.get("inn_name")

    if not inn_name:
        print(f"No INN found for {source_name}, returning partial data")
        return {
            "source_data": drug_info,
            "normalization": normalization_result,
            "regulatory_checks": {"regulatory_checks": {}, "dosage_check": {}},
            "pubmed_articles": [],
            "ai_analysis": {
                "ud_ai_grade": "Unknown",
                "ud_ai_justification": "Не удалось определить МНН препарата",
                "ai_summary_note": "Требуется ручная проверка названия препарата"
            }
        }

    print(f"Found INN: {inn_name}, proceeding with full analysis")
    
    regulatory_task = regulatory_checker.check_all_regulators(
        inn_name=inn_name,
        source_dosage=drug_info.get("dosage_source", "")
    )
    pubmed_task = pubmed.search_articles(
        inn_name=inn_name,
        brand_name=source_name,
        disease_context=drug_info.get("context_indication", "")
    )

    try:
        regulatory_results, pubmed_articles = await asyncio.gather(
            regulatory_task, 
            pubmed_task, 
            return_exceptions=True
        )
        
        # Handle exceptions in results
        if isinstance(regulatory_results, Exception):
            print(f"Regulatory check failed: {regulatory_results}")
            regulatory_results = {"regulatory_checks": {}, "dosage_check": {}}
            
        if isinstance(pubmed_articles, Exception):
            print(f"PubMed search failed: {pubmed_articles}")
            pubmed_articles = []
            
    except Exception as e:
        print(f"Error in parallel tasks: {e}")
        regulatory_results = {"regulatory_checks": {}, "dosage_check": {}}
        pubmed_articles = []

    full_drug_data = {
        "source_data": drug_info,
        "normalization": normalization_result,
        "regulatory_checks": regulatory_results,
        "pubmed_articles": pubmed_articles,
    }

    try:
        final_analysis = await ai_analyzer.generate_ai_analysis(full_drug_data)
    except Exception as e:
        print(f"AI analysis failed for {source_name}: {e}")
        final_analysis = {
            "ud_ai_grade": "Error",
            "ud_ai_justification": "Ошибка при генерации анализа",
            "ai_summary_note": "Не удалось сгенерировать анализ"
        }
        
    full_drug_data["ai_analysis"] = final_analysis
    
    print(f"Completed analysis for: {source_name}")

    return full_drug_data


async def run_analysis_pipeline(file_content: bytes):
    """
    The main orchestrator for the document analysis pipeline.
    """
    file_stream = io.BytesIO(file_content)
    document = Document(file_stream)

    all_text = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                all_text.append(cell.text)
    full_text = "\n".join(all_text)

    if not full_text.strip():
        return {"error": "The document is empty."}

    # Generate summary and extract drugs concurrently
    summary_task = generate_document_summary(full_text)
    extraction_task = protocol_parser.extract_drugs_from_text(full_text)

    document_summary, extracted_drugs = await asyncio.gather(summary_task, extraction_task)

    if not extracted_drugs:
        return {
            "document_summary": document_summary,
            "analysis_results": [],
            "message": "No drugs were found in the document."
        }

    print(f"Processing {len(extracted_drugs)} extracted drugs")

    analysis_tasks = [process_single_drug(drug) for drug in extracted_drugs]
    analysis_results = await asyncio.gather(*analysis_tasks)
    analysis_results = [res for res in analysis_results if res is not None]

    return {
        "document_summary": document_summary,
        "analysis_results": analysis_results
    }
