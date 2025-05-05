from reportlab.lib import colors
from reportlab.pdfgen import canvas

from src.FormatClasses import *
from src.blocks import *
from src.card.CardContext import CardContext
from src.card.CardDimensions import CardDimensions


class Card:
    """
    One card contains the following four blocks:
        +-------------------------------------------------------+
        | Image | Last Name    |                |               |
        |       | First Name   | Vehicle        | Other Quali. &|
        |------ |              | Qualifications | QR Code       |
        | Role  | Leading Role |                |               |
        +-------------------------------------------------------+
          IMAGE   MAIN CONTENT   VEHICLE QUALI    OTHER QUALI
    """

    def __init__(self, canvas: canvas, person: Person, card_x, card_y, card_width, card_height, top_bottom_padding=0.0,
                 font="Helvetica"):
        """
        :param person: JSON data for a single person
        :param card_width: total width (in mm)
        :param card_height: total height (in mm)
        :param top_bottom_padding: top and bottom bars for old cardholder (in mm)
        """

        self.context = CardContext(canvas, person)
        self.dimensions = CardDimensions(card_x, card_y, card_width, card_height,
                                         top_bottom_padding)
        self.content_dimensions = self.dimensions.get_content_dimensions()

        self.font = font
        self.blocks = {
            "image":
                ImageBlock(self.context,
                           Dimensions(self.content_dimensions.x,
                                      self.content_dimensions.y,
                                      None,
                                      self.content_dimensions.height)),
            "main_content":
                MainBlock(self.context,
                          Dimensions(None,
                                     self.content_dimensions.y,
                                     None,
                                     self.content_dimensions.height)),
            "vehicle_instructions":
                VehicleInstructionsBlock(self.context,
                                         Dimensions(None,
                                                    self.content_dimensions.y,
                                                    None,
                                                    self.content_dimensions.height)),
            "other_qualifications":
                QualificationsBlock(self.context,
                                    Dimensions(
                                        self.content_dimensions.x + self.dimensions.width - self.content_dimensions.height,
                                        self.content_dimensions.y,
                                        self.content_dimensions.height,
                                        self.content_dimensions.height))
        }

    def draw(self):
        # calculate remaining block dimension parameters
        current_width = sum([block.get_width() for block in self.blocks.values() if block.get_width()])
        blocks_without_width = [key for key, block in self.blocks.items() if block.get_width() is None]

        # spread remaining card space equally across blocks without width
        remaining_space = self.content_dimensions.width - current_width
        for key in blocks_without_width:
            self.blocks[key].dimensions.width = remaining_space / len(blocks_without_width)

        assert all([block.get_width() for block in
                    self.blocks.values()]), "Something went wrong, not all blocks do have a width!"

        # set new x for every block
        blocks = list(self.blocks.values())
        for i in range(len(blocks) - 1):
            blocks[i + 1].set_x(blocks[i].right_edge)

        for block in self.blocks.values():
            block.draw()

        self.__draw_main_borders()

    def __draw_main_borders(self):
        c = self.context.c
        c.setStrokeColor(colors.black)
        c.rect(self.dimensions.x, self.dimensions.y, self.dimensions.width, self.dimensions.height,
               stroke=1,
               fill=0)  # outer border for upper/lower spacing
        c.rect(self.content_dimensions.x, self.content_dimensions.y, self.content_dimensions.width,
               self.content_dimensions.height, stroke=1, fill=0)
