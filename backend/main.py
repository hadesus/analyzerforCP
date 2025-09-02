from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback
import logging
import json
import sys
import os
import datetime
import io

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def log_system_info():
    """Log system information for debugging"""
    logger.info("=" * 50)
    logger.info("SYSTEM STARTUP DIAGNOSTICS")
    logger.info("=" * 50)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Files in current directory: {os.listdir('.')}")
    if os.path.exists('services'):
        logger.info(f"Files in services: {os.listdir('services')}")
    logger.info(f"Environment variables:")
    for key in ['GEMINI_API_KEY', 'PUBMED_API_KEY', 'PUBMED_API_EMAIL']:
        value = os.getenv(key)
        logger.info(f"  {key}: {'SET' if value else 'NOT SET'}")
    logger.info("=" * 50)

log_system_info()

# Import our modules with error handling
try:
    logger.info("Attempting to import main_pipeline...")
    from main_pipeline import run_analysis_pipeline
    logger.info("✅ main_pipeline imported successfully")
    
    logger.info("Attempting to import exporter...")
    from services.exporter import create_docx_export, create_excel_export
    logger.info("✅ exporter imported successfully")
    
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    # Don't raise here, let the server start but handle errors in endpoints
    run_analysis_pipeline = None
    create_docx_export = None
    create_excel_export = None

app = FastAPI()
logger.info("FastAPI app created")

# Set up CORS middleware
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000", 
    "http://127.0.0.1:5000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    logger.info("Health check endpoint called")
    return {
        "message": "Clinical Protocol Analysis API is running.",
        "timestamp": datetime.datetime.now().isoformat(),
        "status": "healthy",
        "imports_status": {
            "pipeline": run_analysis_pipeline is not None,
            "exporter": create_docx_export is not None
        }
    }

@app.post("/analyze")
async def analyze_protocol_document(file: UploadFile = File(...)):
    """Analyze clinical protocol document"""
    logger.info("=" * 60)
    logger.info("NEW ANALYSIS REQUEST RECEIVED")
    logger.info("=" * 60)
    logger.info(f"File received: {file.filename}")
    
    if run_analysis_pipeline is None:
        logger.error("❌ Pipeline not available due to import errors")
        raise HTTPException(status_code=500, detail="Server not properly initialized - import errors")
    
    if not file.filename.endswith('.docx'):
        logger.warning(f"Invalid file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .docx file.")

    try:
        logger.info(f"Starting analysis for file: {file.filename}")
        content = await file.read()
        logger.info(f"File read successfully, size: {len(content)} bytes")
        
        results = await run_analysis_pipeline(content)
        logger.info(f"Analysis pipeline completed")
        
        if isinstance(results, dict) and "error" in results:
            logger.error(f"Pipeline returned error: {results}")
            raise HTTPException(status_code=500, detail=results["error"])
            
        response_data = {
            "filename": file.filename,
            "document_summary": results.get("document_summary"),
            "analysis_results": results.get("analysis_results", [])
        }
        logger.info(f"Returning response with {len(response_data['analysis_results'])} results")
        return response_data
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR in analyze endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/export/docx")
async def export_docx(data: list = Body(...)):
    """Export analysis data as DOCX"""
    if create_docx_export is None:
        raise HTTPException(status_code=500, detail="Export functionality not available")
    
    logger.info(f"DOCX export requested for {len(data)} items")
    file_stream = create_docx_export(data)
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=analysis_report.docx"}
    )

@app.post("/export/xlsx")
async def export_excel(data: list = Body(...)):
    """Export analysis data as Excel"""
    if create_excel_export is None:
        raise HTTPException(status_code=500, detail="Export functionality not available")
    
    logger.info(f"Excel export requested for {len(data)} items")
    file_stream = create_excel_export(data)
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=analysis_report.xlsx"}
    )

@app.post("/export/json")
async def export_json(data: list = Body(...)):
    """Export analysis data as JSON"""
    logger.info(f"JSON export requested for {len(data)} items")
    json_string = json.dumps(data, indent=2, ensure_ascii=False)
    return StreamingResponse(
        iter([json_string]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=analysis_report.json"}
    )

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")