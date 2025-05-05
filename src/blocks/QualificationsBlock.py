import os
from dataclasses import dataclass
from enum import Enum
from io import BytesIO

import qrcode

from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

from src.Helper.CanvasHelper import CanvasHelper
from src.blocks.Block import Block


class StringEnum(str, Enum):
    pass


class Positions(StringEnum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


@dataclass
class QualificationsBlock(Block):
    options = {"TH": (Positions.TOP_LEFT, colors.yellow, "th.png"),
               "Maschinist": (Positions.TOP_RIGHT, colors.dodgerblue, "fire_engine.png"),
               "Kettensäge": (Positions.BOTTOM_LEFT, colors.green, "chainsaw.png"),
               "AGT": (Positions.BOTTOM_RIGHT, colors.red, "agt.png")}

    icon_dir = os.path.join(os.path.dirname(__file__), "..", "..", "icons")
    qr_base_url = "of56.vercel.app/personnel/"

    def __post_init__(self):
        if self.dimensions.width != self.dimensions.height:
            raise ValueError(
                f"QualificationsBlock must be a square shape, "
                f"but has dimensions '{self.dimensions.width}x{self.dimensions.height}'")
        self.side_length = self.dimensions.width / 2

    def draw(self):
        self.__draw_qualifications()
        self.__draw_qr() if self.context.person.personnel_id else None

    def __draw_qualifications(self):
        for key, (pos, color, icon_file) in self.options.items():
            self.context.c.setFillColor(color)
            self.context.c.setStrokeColor(colors.black)
            self.context.c.rect(*self.__get_square_coords(pos),
                                self.side_length, self.side_length,
                                fill=self.context.person.qualifications[key],  # fill color if person has qualification
                                stroke=True)
            self.__draw_icon(icon_file, pos) if self.context.person.qualifications[key] else None

    def __draw_icon(self, icon_file, pos, scale=0.6, padding=1):
        if scale > 1:
            raise ValueError("Scale must be less than 1")

        path = os.path.join(self.icon_dir, icon_file)

        x, y = self.__get_square_coords(pos)
        scaled_x, scaled_y = x, y
        match pos:
            case Positions.TOP_LEFT:
                scaled_y = y + self.side_length * (1 - scale) - padding
                scaled_x = x + padding
            case Positions.TOP_RIGHT:
                scaled_x = x + self.side_length * (1 - scale) - padding
                scaled_y = y + self.side_length * (1 - scale) - padding
            case Positions.BOTTOM_LEFT:
                scaled_x += padding
                scaled_y += padding
            case Positions.BOTTOM_RIGHT:
                scaled_x = x + self.side_length * (1 - scale) - padding
                scaled_y += padding

        self.context.c.drawImage(path,
                                 scaled_x, scaled_y,
                                 (self.side_length * scale) - padding, (self.side_length * scale) - padding,
                                 preserveAspectRatio=True,
                                 mask="auto")

    def __draw_qr(self):
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

        qr = generate_qr_code(self.qr_base_url + self.context.person.personnel_id)
        mid = (self.dimensions.x + self.side_length, self.dimensions.y + self.side_length)
        CanvasHelper.draw_rotated_image(self.context.c,
                                        qr,
                                        *mid,
                                        angle=315,
                                        side_length=self.side_length,
                                        scale=1,
                                        padding=3)

    def __get_square_coords(self, pos: Positions) -> (int, int):
        """
        Calculate the coordinates of a square based on the given position within the block
        :param pos: one of the four below
        :return: bottom left corner of the square
        """

        assert self.side_length > 0, "Side length must be greater than 0"

        mid_vertical = self.dimensions.y + self.side_length
        mid_horizontal = self.dimensions.x + self.side_length

        match pos:
            case Positions.TOP_LEFT:
                return [self.dimensions.x, mid_vertical]
            case Positions.TOP_RIGHT:
                return [mid_horizontal, mid_vertical]
            case Positions.BOTTOM_LEFT:
                return [self.dimensions.x, self.dimensions.y]
            case Positions.BOTTOM_RIGHT:
                return [mid_horizontal, self.dimensions.y]
