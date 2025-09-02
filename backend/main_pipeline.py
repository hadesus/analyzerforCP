import asyncio
import io
import traceback
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
        print("❌ Empty text for summary generation")
        return "Текст документа пуст."

    print("📝 Generating document summary...")
    
    prompt = f"""Напиши краткое резюме клинического протокола (2-3 предложения).
    Укажи основное заболевание, целевую группу пациентов и подходы к лечению.

    Текст:
    ---
    {full_text[:10000]}
    ---
    """
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"temperature": 0.2, "max_output_tokens": 500}
        )
        response = await model.generate_content_async(prompt)
        summary = response.text.strip()
        print(f"✅ Summary generated: {len(summary)} chars")
        return summary
    except Exception as e:
        print(f"❌ Error generating document summary: {e}")
        traceback.print_exc()
        return "Не удалось сгенерировать общее резюме для документа."


async def process_single_drug(drug_info: dict):
    """
    Processes a single drug through the complete analysis pipeline.
    Returns comprehensive data including normalization, regulatory checks, and literature.
    """
    source_name = drug_info.get("drug_name_source")
    if not source_name:
        print(f"❌ Skipping drug with no source name: {drug_info}")
        return None

    print(f"💊 Processing drug: {source_name}")
    
    try:
        normalization_result = await drug_normalizer.normalize_drug(source_name)
        inn_name = normalization_result.get("inn_name")
    except Exception as e:
        print(f"❌ Normalization failed for {source_name}: {e}")
        normalization_result = {"inn_name": None, "source": "Error", "confidence": "none"}
        inn_name = None

    if not inn_name:
        print(f"⚠️ No INN found for {source_name}, returning partial data")
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

    print(f"✅ Found INN: {inn_name}, proceeding with full analysis")
    
    try:
        print(f"🔍 Starting regulatory and PubMed checks for {inn_name}")
        regulatory_task = regulatory_checker.check_all_regulators(
            inn_name=inn_name,
            source_dosage=drug_info.get("dosage_source", "")
        )
        pubmed_task = pubmed.search_articles(
            inn_name=inn_name,
            brand_name=source_name,
            disease_context=drug_info.get("context_indication", "")
        )

        regulatory_results, pubmed_articles = await asyncio.gather(
            regulatory_task, 
            pubmed_task, 
            return_exceptions=True
        )
        
        # Handle exceptions in results
        if isinstance(regulatory_results, Exception):
            print(f"❌ Regulatory check failed: {regulatory_results}")
            regulatory_results = {"regulatory_checks": {}, "dosage_check": {}}
            
        if isinstance(pubmed_articles, Exception):
            print(f"❌ PubMed search failed: {pubmed_articles}")
            pubmed_articles = []
            
    except Exception as e:
        print(f"❌ Error in parallel tasks: {e}")
        traceback.print_exc()
        regulatory_results = {"regulatory_checks": {}, "dosage_check": {}}
        pubmed_articles = []

    full_drug_data = {
        "source_data": drug_info,
        "normalization": normalization_result,
        "regulatory_checks": regulatory_results,
        "pubmed_articles": pubmed_articles,
    }

    try:
        print(f"🧠 Generating final analysis for {source_name}")
        final_analysis = await ai_analyzer.generate_ai_analysis(full_drug_data)
        print(f"✅ Analysis completed for {source_name}")
    except Exception as e:
        print(f"❌ Analysis failed for {source_name}: {e}")
        traceback.print_exc()
        final_analysis = {
            "ud_ai_grade": "Error",
            "ud_ai_justification": "Ошибка при генерации анализа",
            "ai_summary_note": "Не удалось сгенерировать анализ"
        }
        
    full_drug_data["ai_analysis"] = final_analysis
    
    print(f"✅ Completed analysis for: {source_name}")

    return full_drug_data


async def run_analysis_pipeline(file_content: bytes):
    """
    The main orchestrator for the document analysis pipeline.
    """
    print("🚀 Starting analysis pipeline")
    
    file_stream = io.BytesIO(file_content)
    
    try:
        document = Document(file_stream)
        print("✅ Document loaded successfully")
    except Exception as e:
        print(f"❌ Error loading document: {e}")
        traceback.print_exc()
        return {"error": f"Не удалось загрузить документ: {e}"}

    all_text = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                all_text.append(cell.text)
    full_text = "\n".join(all_text)
    print(f"📄 Extracted text length: {len(full_text)} chars")

    if not full_text.strip():
        print("❌ Document is empty")
        return {"error": "The document is empty."}

    try:
        # Generate summary and extract drugs concurrently
        print("🔄 Starting summary and drug extraction")
        summary_task = generate_document_summary(full_text)
        extraction_task = protocol_parser.extract_drugs_from_text(full_text)

        document_summary, extracted_drugs = await asyncio.gather(summary_task, extraction_task)
        print(f"✅ Summary and extraction completed. Found {len(extracted_drugs)} drugs")
    except Exception as e:
        print(f"❌ Error in summary/extraction: {e}")
        traceback.print_exc()
        return {"error": f"Ошибка при анализе документа: {e}"}

    if not extracted_drugs:
        print("⚠️ No drugs found in document")
        return {
            "document_summary": document_summary,
            "analysis_results": [],
            "message": "No drugs were found in the document."
        }

    print(f"🔄 Processing {len(extracted_drugs)} extracted drugs")

    try:
        analysis_tasks = [process_single_drug(drug) for drug in extracted_drugs]
        analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Filter out exceptions and None results
        valid_results = []
        for i, result in enumerate(analysis_results):
            if isinstance(result, Exception):
                print(f"❌ Analysis failed for drug {i}: {result}")
            elif result is not None:
                valid_results.append(result)
        
        print(f"✅ Pipeline completed. {len(valid_results)} drugs analyzed successfully")
        
        return {
            "document_summary": document_summary,
            "analysis_results": valid_results
        }
        
    except Exception as e:
        print(f"❌ Error in drug analysis: {e}")
        traceback.print_exc()
        return {"error": f"Ошибка при анализе препаратов: {e}"}
