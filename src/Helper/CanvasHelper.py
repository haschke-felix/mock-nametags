from reportlab.lib import colors
from reportlab.pdfgen import canvas


class CanvasHelper:
    @staticmethod
    def create_path(c: canvas, coords: list[(int, int)]):
        """
        :param c: canvas
        :param coords: list of (x, y) coordinates
        :return: drawn path
        """
        path = c.beginPath()
        path.moveTo(coords[0])
        for coord in coords[1:]:
            path.lineTo(coord)
        path.close()
        return path

    @staticmethod
    def create_square_path(c: canvas, x, y, side_length):
        corners = [(x, y),
                   (x + side_length, y),
                   (x + side_length, y + side_length),
                   (x, y + side_length)]
        return CanvasHelper.create_path(c, corners)

    @staticmethod
    def draw_rotated_image(c: canvas, image, x, y, angle, side_length, scale=1, padding=0):
        c.saveState()
        c.translate(x, y)
        c.rotate(angle)
        c.scale(scale, scale)

        if padding > 0:
            c.setFillColor(colors.white)
            c.rect(-side_length / 2 - padding, -side_length / 2 - padding,
                   side_length + 2 * padding,
                   side_length + 2 * padding, fill=1)

        c.drawImage(image,
                    -side_length / 2,
                    -side_length / 2,
                    width=side_length,
                    height=side_length)
        c.restoreState()
