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

async def process_single_drug(drug_info: dict):
    """
    Runs the full analysis pipeline for a single drug entry extracted from the document.
    """
    source_name = drug_info.get("drug_name_source")
    if not source_name:
        return None # Skip if no drug name was extracted

    # Step 1: Normalize the drug name
    normalization_result = await drug_normalizer.normalize_drug(source_name)
    inn_name = normalization_result.get("inn_name")

    # If we couldn't even identify an INN, we can't proceed much further
    if not inn_name:
        # We can still return the data we have
        return {
            "source_data": drug_info,
            "normalization": normalization_result,
            "regulatory_checks": None,
            "pubmed_articles": None,
            "ai_analysis": None
        }

    # Step 2: Run regulatory and PubMed checks in parallel
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

    # Step 3: Aggregate all data
    full_drug_data = {
        "source_data": drug_info,
        "normalization": normalization_result,
        "regulatory_checks": regulatory_results,
        "pubmed_articles": pubmed_articles,
    }

    # Step 4: Generate the final AI analysis based on all collected data
    final_analysis = await ai_analyzer.generate_ai_analysis(full_drug_data)

    full_drug_data["ai_analysis"] = final_analysis

    return full_drug_data


async def run_analysis_pipeline(file_content: bytes):
    """
    The main orchestrator for the document analysis pipeline.
    """
    # Parse the .docx file content
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

    # Get initial list of drugs from the document
    extracted_drugs = await protocol_parser.extract_drugs_from_text(full_text)

    if isinstance(extracted_drugs, dict) and "error" in extracted_drugs:
        return {"error": "Failed to extract drugs from document.", "details": extracted_drugs["details"]}

    if not extracted_drugs:
        return {"message": "No drugs were found in the document."}

    # Process each extracted drug concurrently
    analysis_tasks = [process_single_drug(drug) for drug in extracted_drugs]
    final_results = await asyncio.gather(*analysis_tasks)

    # Filter out any None results
    final_results = [res for res in final_results if res is not None]

    return final_results
