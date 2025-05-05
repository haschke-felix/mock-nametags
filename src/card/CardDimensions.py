from src.FormatClasses import Dimensions


class CardDimensions:
    def __init__(self, x, y, card_width, card_height,
                 top_bottom_padding):
        self.x = x
        self.y = y
        self.content_y = self.y + top_bottom_padding * 2.834
        self.width = card_width * 2.834  # mm to pt
        self.height = card_height * 2.834
        self.content_height = (card_height - 2 * top_bottom_padding) * 2.834

    def get_content_dimensions(self):
        return Dimensions(self.x, self.content_y, self.width, self.content_height)
