from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.responses import StreamingResponse
from backend.main_pipeline import run_analysis_pipeline
from backend.services import exporter
import json

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Clinical Protocol Analysis API is running."}

@app.post("/analyze")
async def analyze_protocol_document(file: UploadFile = File(...)):
    """
    Accepts a .docx clinical protocol, runs the full analysis pipeline,
    and returns a comprehensive JSON report for all found medications.
    """
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .docx file.")

    try:
        content = await file.read()
        results = await run_analysis_pipeline(content)
        if isinstance(results, dict) and "error" in results:
             raise HTTPException(status_code=500, detail=results)
        return {"filename": file.filename, "analysis_results": results}
    except Exception as e:
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
