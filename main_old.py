import json
import uuid
import os

from dataclasses import dataclass
from enum import IntEnum
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

import qrcode
from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

from PIL import Image, ImageOps

app = FastAPI()

ALL_QUALIFICATIONS = ["TH", "AGT", "Sprechfunk", "Maschinist", "Kettensäge", "Klasse C", "Truppführer",
                      "Gruppenführer",
                      "Zugführer",
                      "Verbandsführer", "Sanitäter", "Truppmann"]
ALL_FUNCTIONS = ["Mannschaft", "Kraftfahrer", "Führung"]
QUALIFICATION_COLORS = {"TH": colors.yellow, "AGT": colors.red, "Maschinist": colors.dodgerblue,
                        "Kettensäge": colors.green}

IMG_PATH = "./pictures/"


@dataclass
class Instruction:
    vehicle: str
    value: bool


class Person(BaseModel):
    first_name: str
    last_name: str
    personnel_id: str | None
    image_url: str | None
    function: str | None
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
            function=data["function"],
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
    function_text = 6
    function_bar = 8
    personnel_id = 8


CARD_WIDTH = 100 * 2.834  # mm to pt
CARD_HEIGHT = 22.45 * 2.834
VIEW_WINDOW_HEIGHT = 19 * 2.834
MARGIN = 5
IMAGE_HEIGHT = VIEW_WINDOW_HEIGHT - int(FontSize.function_text) - 2
IMAGE_WIDTH = IMAGE_HEIGHT * .75  # 3:4 format
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


def get_icon(path, invert=False):
    img = Image.open(path).convert("RGBA")
    if invert:
        r, g, b, a = img.split()
        rgb_image = Image.merge("RGB", (r, g, b))
        inverted_rgb = ImageOps.invert(rgb_image)
        img = Image.merge("RGBA", (inverted_rgb.split() + (a,)))

    img_stream = BytesIO()
    img.save(img_stream, format="PNG")
    img_stream.seek(0)

    return ImageReader(img_stream)


def create_square_path(c: canvas, x, y, side_length):
    path = c.beginPath()
    path.moveTo(x, y)
    path.lineTo(x + side_length, y)
    path.lineTo(x + side_length, y + side_length)
    path.lineTo(x, y + side_length)
    path.close()
    return path


def draw_rotated_image(c: canvas, image, x, y, angle, side_length):
    c.saveState()
    c.translate(x, y)
    c.rotate(angle)
    c.drawImage(image, 0, 0, width=side_length, height=side_length)
    c.restoreState()


def draw_leading_role_indicator(c, idx, short, x, y, max_width, max_height):
    c.setStrokeColor(colors.darkgrey)
    c.setFillColor(colors.lightgrey)  # set default background
    c.setLineWidth(1)

    beam_width = max_width / 4

    # roles = ["TF", "GF", "VF" if short == "VF" else "ZF"]
    roles = ["TF", "GF", "ZF", "VF"]

    for i in range(4, 0, -1):
        c.setFillColor(colors.green if idx >= i else colors.lightgrey)
        c.roundRect(x + (i - 1) * beam_width, y, beam_width, max_height, radius=5, fill=1)
        c.setFillColor(colors.white if idx >= i else colors.black)
        str_width = stringWidth(roles[i - 1], "Helvetica-Bold", FontSize.function_bar)
        c.setFont("Helvetica-Bold", FontSize.function_bar + 2)
        c.drawString(x + (i - 1) * beam_width + (beam_width - str_width) / 2,
                     y + (max_height - FontSize.function_bar) / 2,
                     roles[i - 1])


def draw_qualifications_only_squares(c: canvas, person: Person, left: float, bottom: float, side_length: float):
    field_coords = {"TH": (left, bottom + side_length / 2),
                    "Maschinist": (left + side_length / 2, bottom + side_length / 2), "Kettensäge": (left, bottom),
                    "AGT": (left + side_length / 2, bottom)}
    for key in field_coords.keys():
        if not person.qualifications[key]:
            continue
        color, field = QUALIFICATION_COLORS[key], field_coords[key]
        c.setFillColor(color)
        c.setStrokeColor(colors.black)
        path = create_square_path(c, *field, side_length / 2)
        c.drawPath(path, fill=1, stroke=1)


def draw_qualifications(c: canvas, person: Person, left: float, bottom: float, side_length: float,
                        padding=5):
    right = left + side_length
    top = bottom + side_length

    top_left = c.beginPath()
    top_left.moveTo(left, top)
    top_left.lineTo(left + side_length / 2, top)
    top_left.lineTo(left + side_length / 2, top - padding)
    top_left.lineTo(left + padding, top - side_length / 2)
    top_left.lineTo(left, top - side_length / 2)
    top_left.close()

    top_right = c.beginPath()
    top_right.moveTo(right, top)
    top_right.lineTo(right - side_length / 2, top)
    top_right.lineTo(right - side_length / 2, top - padding)
    top_right.lineTo(right - padding, top - side_length / 2)
    top_right.lineTo(right, top - side_length / 2)
    top_right.close()

    bottom_left = c.beginPath()
    bottom_left.moveTo(left, bottom)
    bottom_left.lineTo(left + side_length / 2, bottom)
    bottom_left.lineTo(left + side_length / 2, bottom + padding)
    bottom_left.lineTo(left + padding, bottom + side_length / 2)
    bottom_left.lineTo(left, bottom + side_length / 2)
    bottom_left.close()

    bottom_right = c.beginPath()
    bottom_right.moveTo(right, bottom)
    bottom_right.lineTo(right - side_length / 2, bottom)
    bottom_right.lineTo(right - side_length / 2, bottom + padding)
    bottom_right.lineTo(right - padding, bottom + side_length / 2)
    bottom_right.lineTo(right, bottom + side_length / 2)
    bottom_right.close()

    order = {"TH": top_left, "Maschinist": top_right, "Kettensäge": bottom_left, "AGT": bottom_right}

    for key in order.keys():
        if not person.qualifications[key]:
            continue

        color, field = QUALIFICATION_COLORS[key], order[key]
        c.setFillColor(color)
        c.setStrokeColor(colors.black)
        c.drawPath(field, fill=1, stroke=1)

    # reset params
    c.setFillColor(colors.white)
    c.setLineWidth(1)


def draw_single_card(c, person: Person, x_offset: float, y_offset: float):
    """
    Draws a single card on the canvas.

    Args:
        c: The canvas object.
        person: The Person object containing the data for the card.
        x_offset: The x-offset for the card.
        y_offset: The y-offset for the card.
    """

    x_content = x_offset
    y_content = y_offset + (CARD_HEIGHT - VIEW_WINDOW_HEIGHT) / 2

    # Image (if available)
    img = IMG_PATH + "placeholder.png"
    img_path_jpg = IMG_PATH + f"{person.personnel_id}.jpg"
    img_path_jpeg = IMG_PATH + f"{person.personnel_id}.jpeg"
    img_path_png = IMG_PATH + f"{person.personnel_id}.png"

    if os.path.exists(img_path_jpg):
        img = ImageReader(img_path_jpg)
    elif os.path.exists(img_path_jpeg):
        img = ImageReader(img_path_jpeg)
    elif os.path.exists(img_path_png):
        img = ImageReader(img_path_png)

    c.drawImage(img, x_content, y_content + (VIEW_WINDOW_HEIGHT - IMAGE_HEIGHT), width=IMAGE_WIDTH,
                height=IMAGE_HEIGHT, mask="auto", preserveAspectRatio=True)
    c.setStrokeColor(colors.black)
    c.line(x_content + IMAGE_WIDTH, y_content, x_content + IMAGE_WIDTH, y_content + VIEW_WINDOW_HEIGHT)

    # Function
    c.setFillColor(colors.black)
    c.setFont("Helvetica", FontSize.function_text)
    if person.function not in ALL_FUNCTIONS:
        raise ValueError(f"Illegal function '{person.function}' for {person.first_name} {person.last_name}")
    str_width = stringWidth(person.function, "Helvetica", FontSize.function_text)
    c.drawString(x_content + (IMAGE_WIDTH - str_width) / 2,
                 y_content + (VIEW_WINDOW_HEIGHT - IMAGE_HEIGHT - int(FontSize.function_text)) / 2 + 1,
                 person.function)

    # Border
    c.setStrokeColor(colors.black)
    c.rect(x_offset, y_offset, CARD_WIDTH, CARD_HEIGHT, stroke=1, fill=0)  # outer border for upper/lower spacings
    c.rect(x_offset, y_offset + (CARD_HEIGHT - VIEW_WINDOW_HEIGHT) / 2, CARD_WIDTH, VIEW_WINDOW_HEIGHT, stroke=1,
           fill=0)

    # Name
    c.setFont("Helvetica-Bold", FontSize.last_name)
    c.setFillColor(colors.black)
    c.drawString(x_content + IMAGE_WIDTH + MARGIN, y_content + VIEW_WINDOW_HEIGHT - MARGIN - FontSize.last_name,
                 person.last_name)
    c.setFont("Helvetica", FontSize.first_name)
    c.drawString(x_content + IMAGE_WIDTH + MARGIN,
                 y_content + VIEW_WINDOW_HEIGHT - MARGIN - int(FontSize.last_name) - int(FontSize.first_name),
                 person.first_name)

    # Vehicle Qualifications
    y_current = y_content + VIEW_WINDOW_HEIGHT
    rect_height = VIEW_WINDOW_HEIGHT / len(person.instructions)
    longest_name = max([stringWidth(i.vehicle, "Helvetica", rect_height - 2) for i in person.instructions])
    box_margin = 2
    box_left_x = x_content + CARD_WIDTH - VIEW_WINDOW_HEIGHT - longest_name - 2 * box_margin
    for i in person.instructions:
        c.setFillColor(colors.deepskyblue)
        c.rect(box_left_x, y_current - rect_height,
               longest_name + 2 * box_margin, rect_height, fill=i.value)
        y_current -= rect_height
        c.setFont("Helvetica", rect_height - 2)
        c.setFillColor(colors.black)
        c.drawString(box_left_x + box_margin, y_current + box_margin,
                     i.vehicle)

    # Leading Qualifications and TOJ
    mapping = {
        "Verbandsführer": ("VF", 4),
        "Zugführer": ("ZF", 3),
        "Gruppenführer": ("GF", 2),
        "Truppführer": ("TF", 1),
        "Truppmann": ("TM", 0)}

    highest_role = None
    highest_value = 0

    for qualification, (short, value) in mapping.items():
        if person.qualifications[qualification]:
            if value >= highest_value:
                highest_value = value
                highest_role = (short, value)

    role_indicator_height = 12
    if highest_role:
        short, idx = highest_role
        draw_leading_role_indicator(c, idx, short, x_content + IMAGE_WIDTH + MARGIN, y_content + MARGIN,
                                    box_left_x - x_content - IMAGE_WIDTH - 2 * MARGIN, role_indicator_height)
    else:
        c.setFont("Helvetica-Bold", FontSize.first_name)
        c.setFillColor(colors.coral)
        c.drawString(x_content + IMAGE_WIDTH + MARGIN, y_content + MARGIN, "Anwärter")

    # Qualifications
    draw_qualifications_only_squares(c, person, x_content + CARD_WIDTH - VIEW_WINDOW_HEIGHT, y_content,
                                     VIEW_WINDOW_HEIGHT)

    # QR Code with ID above
    if not person.personnel_id:
        return

    c.setFillColor(colors.black)
    str_width = stringWidth(person.personnel_id, "Helvetica-Bold", FontSize.personnel_id)
    c.setFont("Helvetica-Bold", FontSize.personnel_id)
    c.drawString(box_left_x - VIEW_WINDOW_HEIGHT / 2 + (VIEW_WINDOW_HEIGHT / 2 - str_width) / 2,
                 y_content + 2 * MARGIN + role_indicator_height,
                 person.personnel_id)


PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
EDGE_MARGIN = 15
GRID_MARGIN_X = 10
GRID_MARGIN_Y = 0


def create_pdf(data: PdfRequest, filename: str, paper_size: Literal["A4", "Label"]):
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
        x_offset += CARD_WIDTH
        if x_offset + CARD_WIDTH > PAGE_WIDTH - EDGE_MARGIN:
            x_offset = EDGE_MARGIN
            y_offset -= CARD_HEIGHT + GRID_MARGIN_Y  # next line
    c.save()
    return pdf_path


@app.post("/generate-pdf/")
async def generate_pdf(
        data: PdfRequest,
        paper_size: Literal["A4", "Label"] = Query("Label")):
    filename = f"{uuid.uuid4()}.pdf"
    pdf_path = create_pdf(data, filename, paper_size)
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)


if __name__ == '__main__':
    with open('example_datasets/real_examples.json', 'r') as f:
        test_data = json.load(f)

    persons = [Person.from_json(p) for p in test_data]
    request = PdfRequest(title="Namensschilder", persons=persons)

    create_pdf(request, "example_datasets/nameplate_examples.pdf")
