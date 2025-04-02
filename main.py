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

from PIL import Image, ImageOps

app = FastAPI()

ALL_QUALIFICATIONS = ["TH", "AGT", "Sprechfunk", "Maschinist", "Kettensäge", "Klasse C", "Truppführer",
                      "Gruppenführer",
                      "Zugführer",
                      "Verbandsführer", "Sanitäter", "Truppmann"]
ALL_FUNCTIONS = ["Mannschaft", "Kraftfahrer", "Führung"]

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


def draw_leading_role_indicator(c, idx, short, x, y, max_width, max_height):
    c.setStrokeColor(colors.darkgrey)
    c.setFillColor(colors.lightgrey)  # set default background
    c.setLineWidth(1)

    beam_width = max_width / 3

    roles = ["TF", "GF", "VF" if short == "VF" else "ZF"]

    for i in range(3, 0, -1):
        c.setFillColor(colors.green if idx >= i else colors.lightgrey)
        c.roundRect(x + (i - 1) * beam_width, y, max_width / 3, max_height, radius=5, fill=1)
        c.setFillColor(colors.white if idx >= i else colors.black)
        str_width = stringWidth(roles[i - 1], "Helvetica-Bold", FontSize.function_bar)
        c.setFont("Helvetica-Bold", FontSize.function_bar + 2)
        c.drawString(x + (i - 1) * beam_width + (beam_width - str_width) / 2,
                     y + (max_height - FontSize.function_bar) / 2,
                     roles[i - 1])


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
        "Zugführer": ("ZF", 3),
        "Verbandsführer": ("VF", 3),
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
    icon_fields_colored = (False, False)  # (th, chainsaw)

    # paths for diagonal fields
    driver = c.beginPath()
    driver.moveTo(rect_left_x, y_content + VIEW_WINDOW_HEIGHT)  # top left
    driver.lineTo(rect_left_x + VIEW_WINDOW_HEIGHT, y_content + VIEW_WINDOW_HEIGHT)  # top right
    driver.lineTo(rect_left_x, y_content)  # bottom left
    driver.close()

    maschi = c.beginPath()
    maschi.moveTo(rect_left_x + 3, y_content + VIEW_WINDOW_HEIGHT - 3)  # top left
    maschi.lineTo(rect_left_x + VIEW_WINDOW_HEIGHT - 7, y_content + VIEW_WINDOW_HEIGHT - 3)  # top right
    maschi.lineTo(rect_left_x + 3, y_content + 7)  # bottom left
    maschi.close()

    agt = c.beginPath()
    agt.moveTo(rect_left_x + VIEW_WINDOW_HEIGHT, y_content + VIEW_WINDOW_HEIGHT)  # top right
    agt.lineTo(rect_left_x + VIEW_WINDOW_HEIGHT, y_content)  # bottom right
    agt.lineTo(rect_left_x, y_content)  # bottom left
    agt.close()

    if person.qualifications["AGT"] and person.qualifications["Klasse C"]:
        icon_fields_colored = (True, True)
        c.setFillColor(colors.dodgerblue)
        c.drawPath(driver, fill=1, stroke=0)

        c.setFillColor(colors.red)
        c.drawPath(agt, fill=1, stroke=0)

    elif person.qualifications["AGT"] and person.qualifications["Maschinist"]:
        icon_fields_colored = (False, True)
        c.setLineWidth(6)
        c.setStrokeColor(colors.dodgerblue)
        c.drawPath(maschi, fill=0, stroke=1)

        c.setFillColor(colors.red)
        c.drawPath(agt, fill=1, stroke=0)

    elif person.qualifications["Klasse C"]:
        icon_fields_colored = (True, True)
        c.setFillColor(colors.dodgerblue)
        c.rect(rect_left_x, y_content, VIEW_WINDOW_HEIGHT, VIEW_WINDOW_HEIGHT, fill=1)

    elif person.qualifications["Maschinist"]:
        icon_fields_colored = (False, False)
        c.setLineWidth(6)
        c.setStrokeColor(colors.dodgerblue)
        c.rect(rect_left_x + 3, y_content + 3, VIEW_WINDOW_HEIGHT - 6, VIEW_WINDOW_HEIGHT - 6, fill=0, stroke=1)

    elif person.qualifications["AGT"]:
        icon_fields_colored = (True, True)
        c.setFillColor(colors.red)
        c.rect(rect_left_x, y_content, VIEW_WINDOW_HEIGHT, VIEW_WINDOW_HEIGHT, fill=1)

    else:
        # non of the above qualifications -> modify icon color
        box_colored = False

    # reset line width and color, add border
    c.setLineWidth(1)
    c.setStrokeColor(colors.black)
    c.rect(rect_left_x, y_content, VIEW_WINDOW_HEIGHT, VIEW_WINDOW_HEIGHT, fill=0)

    # other qualifications
    if person.qualifications["TH"]:
        c.drawImage(get_icon("./icons/th.png", icon_fields_colored[0]),
                    x_content + CARD_WIDTH - VIEW_WINDOW_HEIGHT + ICON_PADDING + 3,
                    y_content + VIEW_WINDOW_HEIGHT / 2 + ICON_PADDING - 3,
                    VIEW_WINDOW_HEIGHT / 2 - 2 * ICON_PADDING,
                    VIEW_WINDOW_HEIGHT / 2 - 2 * ICON_PADDING, mask="auto")

    if person.qualifications["Kettensäge"]:
        c.drawImage(get_icon("./icons/chainsaw.png", icon_fields_colored[1]),
                    x_content + CARD_WIDTH - VIEW_WINDOW_HEIGHT / 2 + ICON_PADDING - 3,
                    y_content + ICON_PADDING + 3,
                    VIEW_WINDOW_HEIGHT / 2 - 2 * ICON_PADDING,
                    VIEW_WINDOW_HEIGHT / 2 - 2 * ICON_PADDING, mask="auto")

    # QR Code with ID above
    if not person.personnel_id:
        return

    c.setFillColor(colors.grey)
    c.rect(box_left_x - VIEW_WINDOW_HEIGHT / 2, y_content + VIEW_WINDOW_HEIGHT / 6, VIEW_WINDOW_HEIGHT / 2,
           VIEW_WINDOW_HEIGHT / 2, fill=0)
    c.drawImage(generate_qr_code(person.personnel_id),
                box_left_x - VIEW_WINDOW_HEIGHT / 2,
                y_content + VIEW_WINDOW_HEIGHT / 6,
                VIEW_WINDOW_HEIGHT / 2,
                VIEW_WINDOW_HEIGHT / 2)
    c.setFillColor(colors.black)
    str_width = stringWidth(person.personnel_id, "Helvetica-Bold", FontSize.personnel_id)
    c.setFont("Helvetica-Bold", FontSize.personnel_id)
    c.drawString(box_left_x - VIEW_WINDOW_HEIGHT / 2 + (VIEW_WINDOW_HEIGHT / 2 - str_width) / 2,
                 y_content + 1.5,
                 person.personnel_id)


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
        x_offset += CARD_WIDTH
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
    with open('./real_examples.json', 'r') as f:
        test_data = json.load(f)

    persons = [Person.from_json(p) for p in test_data]
    request = PdfRequest(title="Namensschilder", persons=persons)

    create_pdf(request, "./nameplate_examples.pdf")
