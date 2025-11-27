import requests
from PyQt6.QtCore import QObject, pyqtSignal
# Main class for API calling
class APIWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            data = response.json()
            self.finished.emit(data)
        except requests.RequestException as e:
            self.error.emit(str(e))