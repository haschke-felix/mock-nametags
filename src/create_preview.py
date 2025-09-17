from pdf2image import convert_from_path
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from PIL import Image
import os

from src.FormatClasses import Person
from src.card.Card import Card


CARD_WIDTH = 100  # mm
CARD_HEIGHT = 22.45  # mm
TOP_BOTTOM_PADDING = 1.725  # mm

class JpgRequest(BaseModel):
    title: str
    person: Person

def create_preview(data: JpgRequest, filename=str):
    pdf_path = f"./{filename}.pdf"

    # Generate PDF first
    c = canvas.Canvas(pdf_path, pagesize=(CARD_WIDTH * 2.834, CARD_HEIGHT * 2.834))
    
    card = Card(c, data.person, 0, 0, CARD_WIDTH, CARD_HEIGHT, TOP_BOTTOM_PADDING)
    card.draw()
    c.showPage()
    c.save()

    # Convert PDF to PNG using pdf2image
    png_path = f"./{filename}.png"
    images = convert_from_path(pdf_path)
    images[0].save(png_path, "PNG")  # Save the first page as a PNG

    # Clean up the intermediate PDF file
    os.remove(pdf_path)

    return png_path
