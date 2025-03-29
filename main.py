import json
import uuid
import os

from dataclasses import dataclass
from enum import IntEnum

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

import qrcode
from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

app = FastAPI()

ALL_QUALIFICATIONS = ["TH", "AGT", "Sprechfunk", "Maschinist", "Kettensäge", "Klasse C", "Truppführer",
                      "Gruppenführer",
                      "Zugführer",
                      "Verbandsführer", "Sanitäter", "Truppmann"]


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
VIEW_WINDOW_HEIGHT = 19 * 2.834
MARGIN = 5
IMAGE_WIDTH = VIEW_WINDOW_HEIGHT * .75  # 3:4 format
ICON_PADDING = 3


def generate_qr_code(text):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=0,
    )
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")

    img_stream = BytesIO()
    img.save(img_stream, format="PNG")
    img_stream.seek(0)

    return ImageReader(img_stream)


def draw_leading_role_indicator(c, idx, short, x, y, max_width, max_height):
    c.setStrokeColor(colors.darkgrey)
    c.setFillColor(colors.lightgrey)  # set default background
    c.setLineWidth(1)

    beam_width = max_width / 3

    for i in range(3, 0, -1):
        if idx == i:
            c.setFillColor(colors.green)
        c.roundRect(x + i * beam_width - beam_width, y, max_width / 3, max_height, radius=5, fill=1)


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
    c.rect(x_offset, y_offset, CARD_WIDTH, CARD_HEIGHT, stroke=1, fill=0)  # outer border for upper/lower spacings
    c.rect(x_offset, y_offset + (CARD_HEIGHT - VIEW_WINDOW_HEIGHT) / 2, CARD_WIDTH, VIEW_WINDOW_HEIGHT, stroke=1,
           fill=0)

    x_content = x_offset
    y_content = y_offset + (CARD_HEIGHT - VIEW_WINDOW_HEIGHT) / 2

    # Image (if available)
    if True:  # TODO: Switch to image url
        try:
            img = ImageReader("./img.jpg")
            c.drawImage(img, x_content, y_content, width=IMAGE_WIDTH,
                        height=VIEW_WINDOW_HEIGHT, mask="auto", preserveAspectRatio=True)
            c.setStrokeColor(colors.black)
            c.line(x_content + IMAGE_WIDTH, y_content, x_content + IMAGE_WIDTH, y_content + VIEW_WINDOW_HEIGHT)
        except:
            c.setFillColor(colors.black)
            c.rect(x_offset, y_offset, IMAGE_WIDTH, CARD_HEIGHT, fill=1, stroke=0)

    # Name
    c.setFont("Helvetica-Bold", FontSize.last_name)
    c.setFillColor(colors.black)
    c.drawString(x_content + IMAGE_WIDTH + MARGIN, y_content + VIEW_WINDOW_HEIGHT - MARGIN - FontSize.last_name,
                 person.last_name)
    c.setFont("Helvetica", FontSize.first_name)
    c.drawString(x_content + IMAGE_WIDTH + MARGIN,
                 y_content + VIEW_WINDOW_HEIGHT - MARGIN - FontSize.last_name - FontSize.first_name, person.first_name)

    # Vehicle Qualifications
    y_current = y_content + VIEW_WINDOW_HEIGHT
    rect_height = VIEW_WINDOW_HEIGHT / len(person.instructions)
    longest_name = max([stringWidth(i.vehicle, "Helvetica", rect_height - 2) for i in person.instructions])
    box_margin = 2
    box_left_x = x_content + CARD_WIDTH - VIEW_WINDOW_HEIGHT - longest_name - 2 * box_margin
    for i in person.instructions:
        c.setFillColor(colors.cyan)
        c.rect(box_left_x, y_current - rect_height,
               longest_name + 2 * box_margin, rect_height, fill=i.value)
        y_current -= rect_height
        c.setFont("Helvetica", rect_height - 2)
        c.setFillColor(colors.black)
        c.drawString(box_left_x + box_margin, y_current + box_margin,
                     i.vehicle)

    # Leading Qualifications and TOJ
    mapping = {"Verbandsführer": ("VF", 3),
               "Zugführer": ("ZF", 3),
               "Gruppenführer": ("GF", 2),
               "Truppführer": ("TF", 1),
               "Truppmann": ("TM", 0)}

    highest_role = None
    highest_value = 0

    for qualification, (short, value) in mapping.items():
        if person.qualifications[qualification]:
            if value >= highest_value:
                highest_role = (short, value)

    if highest_role:
        short, idx = highest_role
        draw_leading_role_indicator(c, idx, short, x_content + IMAGE_WIDTH + MARGIN, y_content + MARGIN,
                                    box_left_x - x_content - IMAGE_WIDTH - VIEW_WINDOW_HEIGHT / 2 - 2 * MARGIN, 12)
    else:
        c.setFont("Helvetica-Bold", FontSize.first_name)
        c.setFillColor(colors.coral)
        c.drawString(x_content + IMAGE_WIDTH + MARGIN, y_content + MARGIN, "Anwärter")

    # AGT or Maschinist
    rect_left_x = x_content + CARD_WIDTH - VIEW_WINDOW_HEIGHT
    c.setStrokeColor(colors.black)
    if person.qualifications["AGT"] and person.qualifications["Klasse C"]:
        c.rect(rect_left_x, y_content, VIEW_WINDOW_HEIGHT, VIEW_WINDOW_HEIGHT, fill=0)

        path1 = c.beginPath()
        path1.moveTo(rect_left_x, y_content + VIEW_WINDOW_HEIGHT)  # top left
        path1.lineTo(rect_left_x + VIEW_WINDOW_HEIGHT, y_content + VIEW_WINDOW_HEIGHT)  # top right
        path1.lineTo(rect_left_x, y_content)  # bottom left
        path1.close()
        c.setFillColor(colors.red)
        c.drawPath(path1, fill=1, stroke=0)

        path2 = c.beginPath()
        path2.moveTo(rect_left_x + VIEW_WINDOW_HEIGHT, y_content + VIEW_WINDOW_HEIGHT)  # top right
        path2.lineTo(rect_left_x + VIEW_WINDOW_HEIGHT, y_content)  # bottom right
        path2.lineTo(rect_left_x, y_content)  # bottom left
        path2.close()
        c.setFillColor(colors.blue)
        c.drawPath(path2, fill=1, stroke=0)

    elif person.qualifications["Maschinist"]:
        c.rect(rect_left_x, y_content, VIEW_WINDOW_HEIGHT, VIEW_WINDOW_HEIGHT, fill=0)
        # clipping region
        c.saveState()
        path = c.beginPath()
        path.rect(rect_left_x, y_content, VIEW_WINDOW_HEIGHT, VIEW_WINDOW_HEIGHT)
        c.clipPath(path, stroke=0, fill=0)

        c.setStrokeColor(colors.blue)
        c.setLineWidth(1)
        line_spacing = 3

        for i in range(-int(VIEW_WINDOW_HEIGHT), int(VIEW_WINDOW_HEIGHT), line_spacing):
            c.line(rect_left_x + i, y_content, rect_left_x + i + VIEW_WINDOW_HEIGHT, y_content + VIEW_WINDOW_HEIGHT)

        c.restoreState()

        if person.qualifications["AGT"]:
            path1 = c.beginPath()
            path1.moveTo(rect_left_x, y_content + VIEW_WINDOW_HEIGHT)  # top left
            path1.lineTo(rect_left_x + VIEW_WINDOW_HEIGHT, y_content + VIEW_WINDOW_HEIGHT)  # top right
            path1.lineTo(rect_left_x, y_content)  # bottom left
            path1.close()
            c.setFillColor(colors.red)
            c.drawPath(path1, fill=1, stroke=0)

    elif person.qualifications["AGT"]:
        c.setFillColor(colors.red)
        c.rect(rect_left_x, y_content, VIEW_WINDOW_HEIGHT, VIEW_WINDOW_HEIGHT, fill=1)

    elif person.qualifications["Klasse C"]:
        c.setFillColor(colors.blue)
        c.rect(rect_left_x, y_content, VIEW_WINDOW_HEIGHT, VIEW_WINDOW_HEIGHT, fill=1)

    # other qualifications
    if person.qualifications["TH"]:
        c.drawImage("./icons/th.png",
                    x_content + CARD_WIDTH - VIEW_WINDOW_HEIGHT + ICON_PADDING,
                    y_content + VIEW_WINDOW_HEIGHT / 2 + ICON_PADDING,
                    VIEW_WINDOW_HEIGHT / 2 - 2 * ICON_PADDING,
                    VIEW_WINDOW_HEIGHT / 2 - 2 * ICON_PADDING, mask="auto")

    if person.qualifications["Kettensäge"]:
        c.drawImage("./icons/chainsaw.png",
                    x_content + CARD_WIDTH - VIEW_WINDOW_HEIGHT + ICON_PADDING,
                    y_content + ICON_PADDING,
                    VIEW_WINDOW_HEIGHT / 2 - 2 * ICON_PADDING,
                    VIEW_WINDOW_HEIGHT / 2 - 2 * ICON_PADDING, mask="auto")

    if person.qualifications["Sprechfunk"]:
        c.drawImage("./icons/radio.png",
                    x_content + CARD_WIDTH - VIEW_WINDOW_HEIGHT / 2 + ICON_PADDING,
                    y_content + VIEW_WINDOW_HEIGHT / 2 + ICON_PADDING,
                    VIEW_WINDOW_HEIGHT / 2 - 2 * ICON_PADDING,
                    VIEW_WINDOW_HEIGHT / 2 - 2 * ICON_PADDING, mask="auto")

    if person.qualifications["Sanitäter"]:
        c.drawImage("./icons/medic.png",
                    x_content + CARD_WIDTH - VIEW_WINDOW_HEIGHT / 2 + ICON_PADDING,
                    y_content + ICON_PADDING,
                    VIEW_WINDOW_HEIGHT / 2 - 2 * ICON_PADDING,
                    VIEW_WINDOW_HEIGHT / 2 - 2 * ICON_PADDING, mask="auto")

    # QR Code TODO: replace with QR Code
    c.setFillColor(colors.grey)
    c.rect(box_left_x - VIEW_WINDOW_HEIGHT / 2, y_content, VIEW_WINDOW_HEIGHT / 2,
           VIEW_WINDOW_HEIGHT / 2, fill=0)
    c.drawImage(generate_qr_code(person.personnel_id),
                box_left_x - VIEW_WINDOW_HEIGHT / 2,
                y_content,
                VIEW_WINDOW_HEIGHT / 2,
                VIEW_WINDOW_HEIGHT / 2)


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
    with open('./nameplate_examples.json', 'r') as f:
        test_data = json.load(f)

    persons = [Person.from_json(p) for p in test_data]
    print("Persons: ", persons)
    request = PdfRequest(title="Namensschilder", persons=persons)

    create_pdf(request, "./nameplate_examples.pdf")
