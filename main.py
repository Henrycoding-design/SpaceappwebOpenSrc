# main.py
# This is the main entry point for the application.
"""Flow:
1. User opens the application -> main.py
2. main.py initializes the QApplication and shows the Login window from auth.py
3. User logs in or signs up
4. Upon successful login, the SatelliteTracker window from satellite_tracker.py is shown
5. API works are handled in another module (worker.py in API folder)"""

import sys
from PyQt6.QtWidgets import QApplication
from src.auth import Login

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Login() # Start with the Login window
    window.show()
    sys.exit(app.exec()) # Start the event loop, booting the application

