from PyQt5.QtWidgets import QApplication, QWidget, QLineEdit, QVBoxLayout, QLabel
from PyQt5.QtGui import QDoubleValidator, QIntValidator

class FloatValidator(QDoubleValidator):
    def __init__(self, bottom, top, decimals, parent=None):
        super().__init__(bottom, top, decimals, parent)

    def validate(self, input_str, pos):
        if not input_str:
            return (self.Intermediate, input_str, pos)

        if input_str in ['-', '.', '-.', '0']:
            return (self.Intermediate, input_str, pos)

        try:
            value = float(input_str)
        except ValueError:
            return (self.Invalid, input_str, pos)

        if self.bottom() <= value <= self.top():
            return (self.Acceptable, input_str, pos)
        else:
            return (self.Invalid, input_str, pos)