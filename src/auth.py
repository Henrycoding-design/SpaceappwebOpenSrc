import os
import json

from PyQt6.QtWidgets import QMainWindow, QMessageBox, QLineEdit
from PyQt6 import uic

from src.satellitetracker import SatelliteTracker
from path import ui_path, templates_path

os.chdir(os.path.dirname(__file__))
class SignUp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(ui_path, "Signup(new).ui"), self)
        self.userData_path = os.path.join(os.path.dirname(__file__), "Userdata.json")
        self.Terms_file_path = os.path.join(templates_path, "PrivatePolicy.html")
        self.showMaximized()
        style = f"""
            QMainWindow {{
                background-image: url("images/backgroundLogin.jpg");
                background-position: center;
            }}
            """
        self.setStyleSheet(style)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.API_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.showpassword_checkbox.stateChanged.connect(self.toggle_pass)

        self.seeTerms_lb.setText(f'<a style="color:white" href="file:///{self.Terms_file_path}">Terms of Use</a>') # This sets the text of the label to be a clickable link, new way to handle links
        self.seeTerms_lb.setOpenExternalLinks(True)
        self.seeTerms_lb.setToolTip("Click to see Terms of Use")

        self.SignUp_btn.clicked.connect(self.handleSignUp)
        self.LogIn_lb.mousePressEvent = self.handleLogin


    def toggle_pass(self):
        if self.showpassword_checkbox.isChecked():
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.API_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.API_input.setEchoMode(QLineEdit.EchoMode.Password)
    
    def loadUserdata(self):
        with open(self.userData_path, 'r') as file:
            try:
                content = file.read().strip()
                if not content:
                    return []
                return json.loads(content)
            except json.JSONDecodeError:
                return []
            
    def saveUserdata(self, data):
        with open(self.userData_path, 'w') as file:
            json.dump(data, file, indent=4)


    def handleSignUp(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        api_key = self.API_input.text().strip()

        if not username or not password or not api_key:
            QMessageBox.warning(self, "ERROR", "Please Enter ALL Information required!")
            return

        
        if not self.policyCheckbox.isChecked():
            QMessageBox.warning(self, "Privacy Policy Not Accepted", "Please agree with our Terms of Privacy to continue!")
            return
        
        userData = self.loadUserdata()

        for user in userData:
            if user["username"] == username:
                QMessageBox.warning(self, "Username Exists", "Username already exists!")
                return

        encoded_password = self.encode_password(password)
        userData.append({"username": username, "password": encoded_password, "api_key": api_key})
        self.saveUserdata(userData)
        QMessageBox.information(self, "SUCCESS", "Sign Up Success!")
        self.login = Login()
        self.login.show()
        self.close()
        return

    def handleLogin(self, event=None):
        self.login = Login()
        self.login.show()
        self.close()

    def encode_password(self, password):
        """Encodes the password using a simple Caesar cipher with a shift of 3."""
        return ''.join(chr(33 + ((ord(c) - 33 + 10 -5 +4 -6) % 94)) for c in password)
    
    
class Login(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(ui_path, "Login(new).ui"),self)
        self.userData_path = os.path.join(os.path.dirname(__file__), "Userdata.json")
        self.Terms_file_path = os.path.join(os.path.dirname(__file__), "PrivatePolicy.html")
        self.showMaximized()
        style = f"""
            QMainWindow {{
                background-image: url("images/backgroundLogin.jpg");
                background-position: center;
            }}
            """
        self.setStyleSheet(style)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.showpassword_checkbox.stateChanged.connect(self.toggle_password)

        self.Login_btn.clicked.connect(self.handleLogin)

        self.SignUp_lb.mousePressEvent = self.handleSignUp
        self.SignUp_lb.setToolTip("Click to Sign Up")

    def toggle_password(self):
        if self.showpassword_checkbox.isChecked():
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

    def loadUserdata(self):
        with open(self.userData_path, 'r') as file:
            try:
                content = file.read().strip()
                if not content:
                    return []
                return json.loads(content)
            except json.JSONDecodeError:
                return []
            
    def saveUserdata(self, data):
        with open(self.userData_path, 'w') as file:
            json.dump(data, file, indent=4)
    
    def handleLogin(self):
        userData = self.loadUserdata()
        if not userData:
            QMessageBox.warning(self, "No Account Registered", "There is no account registered yet! Please Sign Up to continue.")
            return
        
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "ERROR", "Please Enter ALL Information required!")
            return
        
        for user in userData:
            encoded_input = self.encode_password(password)
            if user["username"] == username and user["password"] == encoded_input:
                self.user_api_key = user.get("api_key", "")
                if not self.user_api_key:
                    QMessageBox.warning(self, "API Key Missing", "API Key is missing for this account. Please check your account again.")
                    return
                QMessageBox.information(self, "SUCCESS", "Login Success!")
                mainwindow = SatelliteTracker(self.user_api_key)
                mainwindow.show()
                self.close()
                return
            
        QMessageBox.warning(self, "ERROR", "Wrong Username or Password")
        return

    def handleSignUp(self, event=None): 
        self.signup = SignUp()
        self.signup.show()
        self.close()
    
    def encode_password(self, password):
        """Encodes the password using a simple Caesar cipher with a shift of 3."""
        return ''.join(chr(33 + ((ord(c) - 33 + 10 -5 +4 -6) % 94)) for c in password)
