from dataclasses import dataclass
from typing import Optional


@dataclass
class Block:
    x_pos: Optional[int] = None
    width: Optional[float] = None

    def right_edge(self):
        """
        Calculates the right edge of the given block. Can be used as the next x-coordinate of the following block.
        :return: sum of pos and width
        """
        if self.x_pos is None or self.width is None:
            return None
        return self.x_pos + self.width


class BlockHelper:
    @staticmethod
    def set_x(blocks: dict[str, Block], block_name: str, x: int):
        blocks[block_name].x_pos = x
        i = list(blocks.keys()).index(block_name)
        BlockHelper.update_prev_block(blocks, i)

    @staticmethod
    def update_prev_block(blocks: dict[str, Block], curr_i: int):
        block_list = list(blocks.values())
        curr_block = block_list[curr_i]
        if curr_i >= len(block_list):
            raise IndexError(f"Index out of range. Max. index is {len(block_list) - 1} for given blocks.")

        if curr_block.x_pos is None or curr_i <= 0:
            return

        prev_block = block_list[curr_i - 1]
        prev_block.width = curr_block.x_pos - prev_block.x_pos
        print(f"Block updated: '{list(blocks.keys())[curr_i - 1]}'")
        BlockHelper.update_prev_block(blocks, curr_i - 1)  # update blocks recursively if prev block has an x-value
