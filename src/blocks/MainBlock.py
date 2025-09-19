from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth

from src.FontSize import FontSize
from src.blocks.Block import Block


class MainBlock(Block):
    padding = 5

    bar_max_height = 12
    bar_font_padding = 2  # padding between border of the bars and the text -> fontsize calculated with max_height

    roles = ["TM", "TF", "GF", "ZF", "VF"]
    roles_map = {"TM": "Truppmann",
                 "TF": "Truppführer",
                 "GF": "Gruppenführer",
                 "ZF": "Zugführer",
                 "VF": "Verbandsführer"}
    highest_role_idx = None

    def draw(self):
        self.__set_highest_role_idx()
        self.__write_name()
        self.__draw_leading_qualification_indicator()
        self.__write_personnel_nr() if self.context.person.personnel_nr else None

    def __write_name(self):
        self.context.c.setFillColor(colors.black)

        # write last name
        self.context.c.setFont(f"{self.font}-Bold", FontSize.last_name)
        last_name_pos = self.dimensions.y + self.dimensions.height - self.padding - int(FontSize.last_name)
        self.context.c.drawString(self.dimensions.x + self.padding,
                                  last_name_pos,
                                  self.context.person.last_name)

        # write first name
        self.context.c.setFont(self.font, FontSize.first_name)
        self.context.c.drawString(self.dimensions.x + self.padding,
                                  last_name_pos - int(FontSize.first_name),
                                  self.context.person.first_name)

    def __draw_leading_qualification_indicator(self):
        self.context.c.setStrokeColor(colors.darkgrey)
        self.context.c.setLineWidth(1)

        if self.highest_role_idx is not None:
            self.__draw_qualification_bars()
        else:
            self.__draw_trainee_label()

    def __write_personnel_nr(self):
        txt_right_pos = self.dimensions.x + self.dimensions.width - self.padding
        txt_bottom_pos = self.dimensions.y + self.bar_max_height + 2 * self.padding

        str_width = stringWidth(self.context.person.personnel_nr, self.font, FontSize.personnel_nr)
        self.context.c.setFont(self.font, FontSize.personnel_nr)
        self.context.c.drawString(txt_right_pos - str_width,
                                  txt_bottom_pos,
                                  self.context.person.personnel_nr)

    def __set_highest_role_idx(self):
        roles_with_person_qualifications = [i for i, role in enumerate(self.roles_map.values()) if
                                            self.context.person.qualifications.get(role)]
        self.highest_role_idx = max(roles_with_person_qualifications) if roles_with_person_qualifications else None

    def __draw_qualification_bars(self):
        bar_x = self.dimensions.x + self.padding
        bar_y = self.dimensions.y + self.padding
        beam_width = (self.dimensions.width - 2 * self.padding) / (len(self.roles) - 1)  # do not count "TM"

        for i in range(1, len(self.roles)):  # starting 1 -> 'TM' is not shown in bars
            has_role = True if self.highest_role_idx >= i else False

            # draw bars
            self.context.c.setFillColor(colors.green if has_role else colors.lightgrey)
            self.context.c.roundRect(bar_x + (i - 1) * beam_width, bar_y, beam_width, self.bar_max_height,
                                     radius=5, fill=1)

            # write qualification label
            self.context.c.setFillColor(colors.white if has_role else colors.black)
            font = f"{self.font}-Bold"
            font_size = self.bar_max_height - 2 * self.bar_font_padding
            str_width = stringWidth(self.roles[i], font, font_size)
            self.context.c.setFont(font, font_size)
            self.context.c.drawString(bar_x + (i - 1) * beam_width + (beam_width - str_width) / 2,
                                      bar_y + (self.bar_max_height - font_size) / 2 + 1,
                                      self.roles[i])

    def __draw_trainee_label(self):
        self.context.c.setFont(f"{self.font}-Bold", FontSize.first_name)
        self.context.c.setFillColor(colors.coral)
        self.context.c.drawString(self.dimensions.x + self.padding, self.dimensions.y + self.padding, "Anwärter")
