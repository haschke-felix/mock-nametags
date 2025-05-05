from reportlab.lib import colors


class Params:
    all_technical_qualifications = ["TH", "AGT", "Maschinist", "Kettensäge", "Klasse C"]
    all_leading_qualifications = ["Truppmann", "Truppführer", "Gruppenführer", "Zugführer", "Verbandsführer"]
    all_functions = ["Mannschaft", "Kraftfahrer", "Führung"]

    technical_qualifications_color_map = {"TH": colors.yellow,
                                          "AGT": colors.red,
                                          "Maschinist": colors.dodgerblue,
                                          "Kettensäge": colors.green}
