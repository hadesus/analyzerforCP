from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback
import logging
import json
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from main_pipeline import run_analysis_pipeline
    from services import exporter
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    traceback.print_exc()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Set up CORS middleware
origins = [
    "http://localhost:3000", # The address of the React frontend
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
    return {"message": "Clinical Protocol Analysis API is running."}

@app.post("/analyze")
async def analyze_protocol_document(file: UploadFile = File(...)):
    """
    Accepts a .docx clinical protocol, runs the full analysis pipeline,
    and returns a comprehensive JSON report for all found medications.
    """
    if not file.filename.endswith('.docx'):
        logger.warning(f"Invalid file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .docx file.")

    try:
        logger.info(f"Starting analysis for file: {file.filename}")
        content = await file.read()
        logger.info(f"File read successfully, size: {len(content)} bytes")
        results = await run_analysis_pipeline(content)
        logger.info(f"Analysis completed successfully")
        if isinstance(results, dict) and "error" in results:
             logger.error(f"Pipeline error: {results}")
             raise HTTPException(status_code=500, detail=results)
        return {"filename": file.filename, "analysis_results": results}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/export/docx")
async def export_docx(data: list = Body(...)):
    """Accepts analysis JSON data and returns a .docx report."""
    file_stream = exporter.create_docx_export(data)
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=analysis_report.docx"}
    )

@app.post("/export/xlsx")
async def export_excel(data: list = Body(...)):
    """Accepts analysis JSON data and returns an .xlsx report."""
    file_stream = exporter.create_excel_export(data)
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=analysis_report.xlsx"}
    )

@app.post("/export/json")
async def export_json(data: list = Body(...)):
    """Accepts analysis JSON data and returns it as a downloadable .json file."""
    json_string = json.dumps(data, indent=2, ensure_ascii=False)
    return StreamingResponse(
        iter([json_string]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=analysis_report.json"}
    )
