from reportlab.pdfgen import canvas

from src.FormatClasses import Person


class CardContext:
    def __init__(self, canvas: canvas, person: Person):
        self.c = canvas
        self.person = person
