from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
import uuid
import json
from src.FormatClasses import Person
from typing import Literal



from mangum import Mangum  # adapter for serverless

from src.create_pdf import create_pdf, PdfRequest

app = FastAPI()


@app.post("/api/generate-pdf/")
async def generate_pdf(
        data: PdfRequest,
        paper_size: Literal["A4", "Label"] = Query("Label")
):
    filename = f"{uuid.uuid4()}.pdf"
    pdf_path = create_pdf(data, filename, paper_size)
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)


# if __name__ == '__main__':
#     with open("example_datasets/nameplates.json", "r") as f:
#         test_data = json.load(f)

#     persons = [Person.from_json(p) for p in test_data]
#     request = PdfRequest(title="Namensschilder", persons=persons)

#     create_pdf(request, "Label", "example_datasets/nameplate_examples.pdf")


handler = Mangum(app)
