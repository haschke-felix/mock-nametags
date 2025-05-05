import os

from reportlab.lib.utils import ImageReader

from src.FontSize import FontSize
from src.blocks.Block import Block

from dataclasses import dataclass

from io import BytesIO
import requests

from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth


@dataclass
class ImageBlock(Block):
    role_label_height: float = None
    role_label_padding: int = 1

    img_url: str = None
    img_height: float = None
    img_width: float = None
    img_aspect_ratio: float = 550 / 732  # pxl dimensions from FeuerOn

    img = None

    placeholder_path: str = "pictures/placeholder.png"

    def __post_init__(self):
        self.role_label_height = 2 * self.role_label_padding + FontSize.function_label

        if self.dimensions.height is not None:
            self.img_height = self.dimensions.height - self.role_label_height  # adapt img height to role label height
            self.img_width = self.img_height * self.img_aspect_ratio
            self.dimensions.width = self.img_width
        if img_url := self.context.person.image_url:
            self.img_url = img_url

        # get image (placeholder or actual image)
        self.img = self.__get_image()

    def draw(self):
        self.__draw_image()
        self.__write_role()
        self.__draw_border()

    def get_width(self):
        return self.img_width

    def __draw_image(self):
        assert self.img_height is not None

        self.context.c.drawImage(self.img,
                                 self.dimensions.x,
                                 self.dimensions.y + (self.dimensions.height - self.img_height),
                                 width=self.img_width,
                                 height=self.img_height,
                                 mask="auto",
                                 preserveAspectRatio=True if self.img_url else False)

    def __write_role(self):
        self.context.c.setFillColor(colors.black)
        self.context.c.setFont(self.font, FontSize.function_label)
        str_width = stringWidth(self.context.person.function, self.font, FontSize.function_label)
        self.context.c.drawString(self.dimensions.x + (self.img_width - str_width) / 2,
                                  self.dimensions.y + (
                                          self.dimensions.height - self.img_height - int(FontSize.function_label) + 1) / 2,
                                  self.context.person.function)

    def __draw_border(self):
        self.context.c.line(self.right_edge, self.dimensions.y, self.right_edge,
                            self.dimensions.y + self.dimensions.height)
        self.context.c.line(self.dimensions.x, self.dimensions.y + (self.dimensions.height - self.img_height),
                            self.right_edge, self.dimensions.y + (self.dimensions.height - self.img_height))

    def __get_image(self):
        if self.img_url:
            return self.__get_image_from_url()

        if not os.path.exists(self.placeholder_path):
            raise ValueError("Path for placeholder image not found")
        return ImageReader(self.placeholder_path)

    def __get_image_from_url(self):
        assert self.context.person.personnel_id is not None, "Function can only be called if person has an personnel id!"

        response = requests.get(self.img_url)
        response.raise_for_status()

        img_stream = BytesIO(response.content)
        img_stream.seek(0)

        return ImageReader(img_stream)
