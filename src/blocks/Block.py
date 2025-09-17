from abc import ABC, abstractmethod
from typing import Optional

from dataclasses import dataclass

from src.card import CardContext
from src.FormatClasses import Dimensions


@dataclass
class Block(ABC):
    context: CardContext
    dimensions: Dimensions
    font: str = "Helvetica"

    @property
    def right_edge(self) -> Optional[float]:
        return self.dimensions.x + self.dimensions.width \
            if self.dimensions.x is not None and self.dimensions.width is not None \
            else None

    def get_width(self):
        return self.dimensions.width

    def set_x(self, new_x):
        self.dimensions.x = new_x

    @abstractmethod
    def draw(self):
        """ Must be implemented in child classes"""
        raise NotImplementedError(
            "Draw-function must be implemented in child classes and can not be used in super-class")
