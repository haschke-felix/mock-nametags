import os
from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import uuid
from typing import Literal

from mangum import Mangum  # adapter for serverless

from src.create_pdf import create_pdf, PdfRequest
from src.create_preview import create_preview, JpgRequest
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Handler initialized")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust as needed
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    allow_credentials=True  # Set to True if credentials are needed
)

# Add custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

@app.post("/api/generate-pdf/")
async def generate_pdf(
        data: PdfRequest,
        paper_size: Literal["A4", "Label"] = Query("Label")
):
    filename = f"{uuid.uuid4()}.pdf"
    pdf_path = create_pdf(data, paper_size, filename)
    response = FileResponse(pdf_path, media_type="application/pdf", filename=filename)
    return response

@app.post("/api/generate-preview/")
async def generate_preview(data: JpgRequest):
    filename = f"{uuid.uuid4()}"
    jpg_path = create_preview(data, filename)
    response = FileResponse(jpg_path, media_type="image/png", filename=f"{filename}.png")
    return response

handler = Mangum(app)
