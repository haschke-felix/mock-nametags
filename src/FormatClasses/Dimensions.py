class Dimensions:
    def __init__(self, x: float = None, y: float = None, width: float = None, height: float = None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def get_dimensions(self):
        return self.x, self.y, self.width, self.height
