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

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug.log')
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
    logger.info(f"Python path: {sys.path}")
    logger.info(f"Environment variables:")
    for key in ['GEMINI_API_KEY', 'PUBMED_API_KEY', 'PUBMED_API_EMAIL']:
        value = os.getenv(key)
        logger.info(f"  {key}: {'SET' if value else 'NOT SET'}")
    logger.info("=" * 50)

log_system_info()
try:
    logger.info("Attempting to import main_pipeline...")
    from main_pipeline import run_analysis_pipeline
    logger.info("✅ main_pipeline imported successfully")
    
    logger.info("Attempting to import exporter...")
    from services import exporter
    logger.info("✅ exporter imported successfully")
    logger.info("✅ All imports successful")
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    traceback.print_exc()
    raise


app = FastAPI()

logger.info("FastAPI app created")

# Set up CORS middleware
origins = [
    "http://localhost:3000", # The address of the React frontend
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000"
]

logger.info(f"Setting up CORS for origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("CORS middleware configured")

@app.get("/")
def read_root():
    logger.info("Health check endpoint called")
    return {
        "message": "Clinical Protocol Analysis API is running.",
        "timestamp": datetime.datetime.now().isoformat(),
        "status": "healthy"
    }

@app.post("/analyze")
async def analyze_protocol_document(file: UploadFile = File(...)):
    """
    Accepts a .docx clinical protocol, runs the full analysis pipeline,
    and returns a comprehensive JSON report for all found medications.
    """
    logger.info("=" * 60)
    logger.info("NEW ANALYSIS REQUEST RECEIVED")
    logger.info("=" * 60)
    logger.info(f"File received: {file.filename}")
    logger.info(f"Content type: {file.content_type}")
    logger.info(f"File size: {file.size if hasattr(file, 'size') else 'unknown'}")
    
    if not file.filename.endswith('.docx'):
        logger.warning(f"Invalid file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .docx file.")

    try:
        logger.info(f"Starting analysis for file: {file.filename}")
        logger.info("Reading file content...")
        content = await file.read()
        logger.info(f"File read successfully, size: {len(content)} bytes")
        
        logger.info("Starting analysis pipeline...")
        results = await run_analysis_pipeline(content)
        logger.info(f"Analysis pipeline completed")
        logger.info(f"Results type: {type(results)}")
        
        if isinstance(results, dict) and "error" in results:
            logger.error(f"Pipeline returned error: {results}")
            raise HTTPException(status_code=500, detail=results["error"])
            
        logger.info(f"Analysis completed successfully with {len(results.get('analysis_results', []))} drugs")
        
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
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/export/docx")
async def export_docx(data: list = Body(...)):
    """Accepts analysis JSON data and returns a .docx report."""
    logger.info(f"DOCX export requested for {len(data)} items")
    file_stream = exporter.create_docx_export(data)
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=analysis_report.docx"}
    )

@app.post("/export/xlsx")
async def export_excel(data: list = Body(...)):
    """Accepts analysis JSON data and returns an .xlsx report."""
    logger.info(f"Excel export requested for {len(data)} items")
    file_stream = exporter.create_excel_export(data)
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=analysis_report.xlsx"}
    )

@app.post("/export/json")
async def export_json(data: list = Body(...)):
    """Accepts analysis JSON data and returns it as a downloadable .json file."""
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