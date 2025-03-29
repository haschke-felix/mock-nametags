import json
import uuid
import os

from dataclasses import dataclass
from enum import Enum, IntEnum

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

app = FastAPI()

ALL_QUALIFICATIONS = ["TH", "AGT", "Sprechfunk", "Maschinist", "Kettensäge", "Klasse C", "Truppführer",
                      "Gruppenführer",
                      "Zugführer",
                      "Verbandsführer", "Sanitäter"]


@dataclass
class Instruction:
    vehicle: str
    value: bool


class Person(BaseModel):
    first_name: str
    last_name: str
    personnel_id: str | None
    image_url: str | None
    qualifications: dict[str, bool]
    instructions: list[Instruction]

    @classmethod
    def from_json(cls, data: dict):
        qualifications_dict = {q: q in data["qualifications"] for q in ALL_QUALIFICATIONS}
        return cls(
            first_name=data["first_name"],
            last_name=data["last_name"],
            personnel_id=data["personnel_id"],
            image_url=data["image_url"],
            qualifications=qualifications_dict,
            instructions=[Instruction(**instr) for instr in data["instructions"]],

        )


class PdfRequest(BaseModel):
    title: str
    persons: list[Person]


class FontSize(IntEnum):
    last_name = 15
    first_name = 12
    leading_qualification = 16


CARD_WIDTH = 100 * 2.834  # mm to pt
CARD_HEIGHT = 22.45 * 2.834
MARGIN = 5
IMAGE_WIDTH = CARD_HEIGHT * .75  # 3:4 format


def draw_single_card(c, person: Person, x_offset: float, y_offset: float):
    """
    Draws a single card on the canvas.

    Args:
        c: The canvas object.
        person: The Person object containing the data for the card.
        x_offset: The x-offset for the card.
        y_offset: The y-offset for the card.
    """

    # Border
    c.setStrokeColor(colors.black)
    c.rect(x_offset, y_offset, CARD_WIDTH, CARD_HEIGHT, stroke=1, fill=0)

    # Divider lines
    c.setStrokeColor(colors.black)
    c.line(x_offset + CARD_WIDTH - CARD_HEIGHT, y_offset, x_offset + CARD_WIDTH - CARD_HEIGHT,
           y_offset + CARD_HEIGHT)

    # Image (if available)
    if True:  # TODO: Switch to image url
        try:
            img = ImageReader("./img.jpg")
            c.drawImage(img, x_offset, y_offset, width=IMAGE_WIDTH,
                        height=CARD_HEIGHT, mask="auto", preserveAspectRatio=True)
            c.setStrokeColor(colors.black)
            c.line(x_offset + IMAGE_WIDTH, y_offset, x_offset + IMAGE_WIDTH, y_offset + CARD_HEIGHT)
        except:
            c.setFillColor(colors.black)
            c.rect(x_offset, y_offset, IMAGE_WIDTH, CARD_HEIGHT, fill=1, stroke=0)

    # Name
    c.setFont("Helvetica-Bold", FontSize.last_name)
    c.setFillColor(colors.black)
    c.drawString(x_offset + IMAGE_WIDTH + MARGIN, y_offset + CARD_HEIGHT - MARGIN - FontSize.last_name,
                 person.last_name)
    c.setFont("Helvetica", FontSize.first_name)
    c.drawString(x_offset + IMAGE_WIDTH + MARGIN,
                 y_offset + CARD_HEIGHT - MARGIN - FontSize.last_name - FontSize.first_name, person.first_name)

    # Leading Qualifications and TOJ
    mapping = {"Verbandsführer": "VF", "Zugführer": "ZF", "Gruppenführer": "GF", "Truppführer": "TF"}
    for qualification in ["Verbandsführer", "Zugführer", "Gruppenführer", "Truppführer"]:
        if person.qualifications[qualification]:
            c.setFillColor(colors.darkgrey)
            c.setStrokeColor(colors.black)
            corner_radius = 2
            c.roundRect(x_offset + IMAGE_WIDTH + MARGIN, y_offset + MARGIN, 22, 22, corner_radius, fill=1)

            c.setFillColor(colors.orangered)
            c.setFont("Helvetica-Bold", FontSize.leading_qualification)
            c.drawString(x_offset + IMAGE_WIDTH + MARGIN + 1, y_offset + MARGIN + 5, mapping[qualification])

            break

    # Vehicle Qualifications
    y_current = y_offset + CARD_HEIGHT
    rect_height = CARD_HEIGHT / len(person.instructions)
    longest_name = max([stringWidth(i.vehicle, "Helvetica", rect_height - 2) for i in person.instructions])
    box_margin = 2
    box_left_x = x_offset + CARD_WIDTH - CARD_HEIGHT - longest_name - 2 * box_margin
    for i in person.instructions:
        c.setFillColor(colors.cyan)
        c.rect(box_left_x, y_current - rect_height,
               longest_name + 2 * box_margin, rect_height, fill=i.value)
        y_current -= rect_height
        c.setFont("Helvetica", rect_height - 2)
        c.setFillColor(colors.black)
        c.drawString(box_left_x + box_margin, y_current + box_margin,
                     i.vehicle)

    # AGT or Maschinist
    rect_left_x = x_offset + CARD_WIDTH - CARD_HEIGHT
    c.setStrokeColor(colors.black)
    if person.qualifications["AGT"] and person.qualifications["Klasse C"]:
        c.rect(rect_left_x, y_offset, CARD_HEIGHT, CARD_HEIGHT, fill=0)

        path1 = c.beginPath()
        path1.moveTo(rect_left_x, y_offset + CARD_HEIGHT)  # top left
        path1.lineTo(rect_left_x + CARD_HEIGHT, y_offset + CARD_HEIGHT)  # top right
        path1.lineTo(rect_left_x, y_offset)  # bottom left
        path1.close()
        c.setFillColor(colors.red)
        c.drawPath(path1, fill=1, stroke=0)

        path2 = c.beginPath()
        path2.moveTo(rect_left_x + CARD_HEIGHT, y_offset + CARD_HEIGHT)  # top right
        path2.lineTo(rect_left_x + CARD_HEIGHT, y_offset)  # bottom right
        path2.lineTo(rect_left_x, y_offset)  # bottom left
        path2.close()
        c.setFillColor(colors.blue)
        c.drawPath(path2, fill=1, stroke=0)

    elif person.qualifications["Maschinist"]:
        c.rect(rect_left_x, y_offset, CARD_HEIGHT, CARD_HEIGHT, fill=0)
        # clipping region
        c.saveState()
        path = c.beginPath()
        path.rect(rect_left_x, y_offset, CARD_HEIGHT, CARD_HEIGHT)
        c.clipPath(path, stroke=0, fill=0)

        c.setStrokeColor(colors.blue)
        c.setLineWidth(1)
        line_spacing = 3

        for i in range(-int(CARD_HEIGHT), int(CARD_HEIGHT), line_spacing):
            c.line(rect_left_x + i, y_offset, rect_left_x + i + CARD_HEIGHT, y_offset + CARD_HEIGHT)

        c.restoreState()

        if person.qualifications["AGT"]:
            path1 = c.beginPath()
            path1.moveTo(rect_left_x, y_offset + CARD_HEIGHT)  # top left
            path1.lineTo(rect_left_x + CARD_HEIGHT, y_offset + CARD_HEIGHT)  # top right
            path1.lineTo(rect_left_x, y_offset)  # bottom left
            path1.close()
            c.setFillColor(colors.red)
            c.drawPath(path1, fill=1, stroke=0)

    elif person.qualifications["AGT"]:
        c.setFillColor(colors.red)
        c.rect(rect_left_x, y_offset, CARD_HEIGHT, CARD_HEIGHT, fill=1)

    elif person.qualifications["Klasse C"]:
        c.setFillColor(colors.blue)
        c.rect(rect_left_x, y_offset, CARD_HEIGHT, CARD_HEIGHT, fill=1)

    # other qualifications
    if person.qualifications["TH"]:
        c.drawImage("./icons/th.png", x_offset + CARD_WIDTH - CARD_HEIGHT, y_offset + CARD_HEIGHT / 2,
                    CARD_HEIGHT / 2, CARD_HEIGHT / 2, mask="auto")

    if person.qualifications["Kettensäge"]:
        c.drawImage("./icons/chainsaw.png", x_offset + CARD_WIDTH - CARD_HEIGHT, y_offset, CARD_HEIGHT / 2,
                    CARD_HEIGHT / 2, mask="auto")

    if person.qualifications["Sprechfunk"]:
        c.drawImage("./icons/radio.png", x_offset + CARD_WIDTH - CARD_HEIGHT / 2, y_offset + CARD_HEIGHT / 2,
                    CARD_HEIGHT / 2, CARD_HEIGHT / 2, mask="auto")

    if person.qualifications["Sanitäter"]:
        c.drawImage("./icons/medic.png", x_offset + CARD_WIDTH - CARD_HEIGHT / 2, y_offset, CARD_HEIGHT / 2,
                    CARD_HEIGHT / 2, mask="auto")

    # QR Code TODO: replace with QR Code
    c.setFillColor(colors.grey)
    c.rect(box_left_x - CARD_HEIGHT / 2, y_offset, CARD_HEIGHT / 2,
           CARD_HEIGHT / 2, fill=1)




PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
EDGE_MARGIN = 15
GRID_MARGIN_X = 10
GRID_MARGIN_Y = 0

def create_pdf(data: PdfRequest, filename: str):
    pdf_path = f"./{filename}"
    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))

    x_offset = EDGE_MARGIN
    y_offset = PAGE_HEIGHT - CARD_HEIGHT - EDGE_MARGIN

    for idx, person in enumerate(data.persons):
        if y_offset < EDGE_MARGIN:
            c.showPage()
            x_offset = EDGE_MARGIN
            y_offset = PAGE_HEIGHT - CARD_HEIGHT - EDGE_MARGIN

        # Draw a single card
        draw_single_card(c, person, x_offset, y_offset)

        # Move for next plate
        x_offset += CARD_WIDTH + GRID_MARGIN_X
        if x_offset + CARD_WIDTH > PAGE_WIDTH - EDGE_MARGIN:
            x_offset = EDGE_MARGIN
            y_offset -= CARD_HEIGHT + GRID_MARGIN_Y  # next line
    c.save()
    return pdf_path


@app.post("/generate-pdf/")
async def generate_pdf(request: PdfRequest):
    filename = f"{uuid.uuid4()}.pdf"
    pdf_path = create_pdf(request, filename)
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)


if __name__ == '__main__':
    with open('./nameplates.json', 'r') as f:
        test_data = json.load(f)

    persons = [Person.from_json(p) for p in test_data]
    print("Persons: ", persons)
    request = PdfRequest(title="Namensschilder", persons=persons)

    create_pdf(request, "./nameplate_examples.pdf")
