import asyncio
import io
from docx import Document

# Import all our services
from backend.services import protocol_parser
from backend.services import drug_normalizer
from backend.services import regulatory_checker
from backend.services import pubmed_client
from backend.services import ai_analyzer

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
    Runs the full analysis pipeline for a single drug entry extracted from the document.
    """
    source_name = drug_info.get("drug_name_source")
    if not source_name:
        return None

    normalization_result = await drug_normalizer.normalize_drug(source_name)
    inn_name = normalization_result.get("inn_name")

    if not inn_name:
        return {
            "source_data": drug_info,
            "normalization": normalization_result,
            "regulatory_checks": None,
            "pubmed_articles": None,
            "ai_analysis": None
        }

    regulatory_task = regulatory_checker.check_all_regulators(
        inn_name=inn_name,
        source_dosage=drug_info.get("dosage_source", "")
    )
    pubmed_task = pubmed.search_articles(
        inn_name=inn_name,
        brand_name=source_name,
        disease_context=drug_info.get("context_indication", "")
    )

    regulatory_results, pubmed_articles = await asyncio.gather(regulatory_task, pubmed_task)

    full_drug_data = {
        "source_data": drug_info,
        "normalization": normalization_result,
        "regulatory_checks": regulatory_results,
        "pubmed_articles": pubmed_articles,
    }

    final_analysis = await ai_analyzer.generate_ai_analysis(full_drug_data)
    full_drug_data["ai_analysis"] = final_analysis

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

    if isinstance(extracted_drugs, dict) and "error" in extracted_drugs:
        return {"error": "Failed to extract drugs from document.", "details": extracted_drugs["details"]}

    if not extracted_drugs:
        return {
            "document_summary": document_summary,
            "analysis_results": [],
            "message": "No drugs were found in the document."
        }

    analysis_tasks = [process_single_drug(drug) for drug in extracted_drugs]
    analysis_results = await asyncio.gather(*analysis_tasks)
    analysis_results = [res for res in analysis_results if res is not None]

    return {
        "document_summary": document_summary,
        "analysis_results": analysis_results
    }
