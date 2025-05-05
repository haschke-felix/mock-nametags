import json
import uuid
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas

from src.FormatClasses import Person
from src.card.Card import Card


class PdfRequest(BaseModel):
    title: str
    persons: list[Person]


app = FastAPI()

PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
EDGE_MARGIN = 15
GRID_MARGIN_X = 10
GRID_MARGIN_Y = 0
CARD_WIDTH = 100  # mm
CARD_HEIGHT = 22.45  # mm
TOP_BOTTOM_PADDING = 1.725  # mm


def create_pdf(data: PdfRequest, paper_size: Literal["A4", "Label"], filename=str):
    pdf_path = f"./{filename}"

    if paper_size == "A4":
        c = canvas.Canvas(pdf_path, pagesize=landscape(A4))

        x_offset = EDGE_MARGIN
        y_offset = PAGE_HEIGHT - CARD_HEIGHT * 2.834 - EDGE_MARGIN
        for idx, person in enumerate(data.persons):
            if y_offset < EDGE_MARGIN:
                c.showPage()
                x_offset = EDGE_MARGIN
                y_offset = PAGE_HEIGHT - CARD_HEIGHT * 2.834 - EDGE_MARGIN

            card = Card(c, person, x_offset, y_offset, CARD_WIDTH, CARD_HEIGHT, TOP_BOTTOM_PADDING)
            card.draw()

            x_offset += CARD_WIDTH * 2.834
            if x_offset + CARD_WIDTH * 2.834 > PAGE_WIDTH - EDGE_MARGIN:
                x_offset = EDGE_MARGIN
                y_offset -= CARD_HEIGHT * 2.834 + GRID_MARGIN_Y  # next line
        c.save()
    else:
        c = canvas.Canvas(pdf_path, pagesize=(CARD_WIDTH * 2.834, CARD_HEIGHT * 2.834))
        for idx, person in enumerate(data.persons):
            card = Card(c, person, 0, 0, CARD_WIDTH, CARD_HEIGHT, TOP_BOTTOM_PADDING)
            card.draw()
            c.showPage()
        c.save()
    return pdf_path


@app.post("/generate-pdf/")
async def generate_pdf(
        data: PdfRequest,
        paper_size: Literal["A4", "Label"] = Query("Label")
):
    filename = f"{uuid.uuid4()}.pdf"
    pdf_path = create_pdf(data, filename, paper_size)
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)


if __name__ == '__main__':
    with open("example_datasets/nameplates.json", "r") as f:
        test_data = json.load(f)

    persons = [Person.from_json(p) for p in test_data]
    request = PdfRequest(title="Namensschilder", persons=persons)

    create_pdf(request, "Label", "example_datasets/nameplate_examples.pdf")
