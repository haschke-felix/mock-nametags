from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth

from dataclasses import dataclass

from src.blocks.Block import Block


@dataclass
class VehicleInstructionsBlock(Block):
    box_padding = 2

    def __post_init__(self):
        self.box_height = self.dimensions.height / len(self.context.person.instructions)
        self.font_size = self.box_height - self.box_padding
        self.dimensions.width = self.calculate_width()

    def calculate_width(self):
        longest_vehicle_name = max(
            [stringWidth(i.vehicle, self.font, self.font_size) for i in self.context.person.instructions])
        return longest_vehicle_name + 2 * self.box_padding

    def get_width(self):
        return self.dimensions.width

    def draw(self):
        y_curr = self.dimensions.y + self.dimensions.height - self.box_height  # draw starting from top

        for i in self.context.person.instructions:
            # draw (colored) box
            self.context.c.setFillColor(colors.deepskyblue)
            self.context.c.rect(self.dimensions.x,
                                y_curr,
                                self.dimensions.width,
                                self.box_height,
                                fill=i.value)  # fill only if person has the instruction

            # write vehicle name
            self.context.c.setFont(self.font, self.font_size)
            self.context.c.setFillColor(colors.black)
            self.context.c.drawString(self.dimensions.x + self.box_padding,
                                      y_curr + self.box_padding,
                                      i.vehicle)

            y_curr -= self.box_height
