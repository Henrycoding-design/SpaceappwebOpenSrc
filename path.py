import os
import sys

base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
templates_path = os.path.join(base_path, "templates")
ui_path = os.path.join(base_path, "ui")
