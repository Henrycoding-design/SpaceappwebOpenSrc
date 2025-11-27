import os
import json
import math
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread

from PyQt6.QtWidgets import QMainWindow, QMessageBox, QVBoxLayout
from PyQt6.QtCore import QUrl, QTimer, QThread
from PyQt6 import uic
from PyQt6.QtWebEngineWidgets import QWebEngineView

from API.worker import APIWorker
from path import templates_path, ui_path

def try_start_server(directory, ports=[8000, 8080, 5500, 8888]):
    for port in ports:
        try:
            os.chdir(directory)
            httpd = HTTPServer(('127.0.0.1', port), SimpleHTTPRequestHandler)
            thread = Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            return port
        except Exception as e:
            print(f"[!] Port {port} failed: {e}")
    return None

# Main app
class SatelliteTracker(QMainWindow):
    def __init__(self, api_key):
        super().__init__()
        self.kEy = api_key
        uic.loadUi(os.path.join(ui_path, "space(new).ui"), self)
        self.loadSatelliteData()
        self.satellite_descriptions_path = os.path.join(os.path.dirname(__file__), "satellite_descriptions.json")
        self.showMaximized()
        
        # Launch host domain ====
        port = try_start_server(templates_path)
        # =======
        
        self.Search_button.clicked.connect(self.search_satellite)
        self.Special_btn.clicked.connect(lambda: self.search_by_button_mode(self.Special_btn.text()))
        self.Starlink_btn.clicked.connect(lambda: self.search_by_button_mode(self.Starlink_btn.text()))
        self.Science_btn.clicked.connect(lambda: self.search_by_button_mode(self.Science_btn.text()))
        self.GPS_btn.clicked.connect(lambda: self.search_by_button_mode(self.GPS_btn.text()))
        self.Weather_btn.clicked.connect(lambda: self.search_by_button_mode(self.Weather_btn.text()))
        self.API_btn.clicked.connect(self.showAPIKey)
        self.Logout_btn.clicked.connect(self.logout)

        self.Above_btn.clicked.connect(self.find_above_satellites)

        self.sat_list.itemClicked.connect(self.handle_satlist_click)

        self.currentsat = None
        self.satname = None

        self.updateposition = QTimer()
        self.updateposition.timeout.connect(self.updatesatpst)


        # Map part
        self.map_view = QWebEngineView()
        if port:
            print(f"[i] Server started on port {port}")
            self.map_view.load(QUrl(f"http://localhost:{port}/map.html"))
        else:
            QMessageBox.critical(None, "Server Error", "Failed to start local server. Please check your firewall or antivirus settings.")

        map_layout = QVBoxLayout(self.mapWidget)
        map_layout.setContentsMargins(0, 0, 0, 0)
        map_layout.addWidget(self.map_view)

        self.updateposition.start(3000)


    
    def getAPIdata(self, url, on_success, on_error=None):
        self.active_threads = getattr(self, "active_threads", [])
        thread = QThread()
        self.active_threads.append(thread)

        worker = APIWorker(url)
        worker.moveToThread(thread)

        def handle_success(data):
            on_success(data)
            thread.quit()
            thread.wait()
            worker.deleteLater()
            thread.deleteLater()
            if thread in self.active_threads:
                self.active_threads.remove(thread)

        def handle_failure(e):
            if on_error:
                on_error(e)
            QMessageBox.critical(None, "API Error", f"Failed to fetch data:\n{e}")
            thread.quit()
            thread.wait()
            worker.deleteLater()
            thread.deleteLater()
            if thread in self.active_threads:
                self.active_threads.remove(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(handle_success)
        worker.error.connect(handle_failure)
        thread.start()

    def showAPIKey(self):
        QMessageBox.information(None, "API Key", f"Your API Key is: {self.kEy}\n\nPlease keep it safe and do not share it publicly.")
        return
        
    def updatesatpst(self):
        lat = 10.762622
        lng = 106.660172
        alt = 5
        seconds = 1
        norad_id = self.currentsat

        if not norad_id or norad_id == 50463:  # JWST does not orbit Earth
            if norad_id == 50463:
                js_code = """
                    if (typeof satMarker !== 'undefined') {
                        map.removeLayer(satMarker);
                        satMarker = undefined;
                    }
                """
                self.map_view.page().runJavaScript(js_code)
            return
        
        url = f"https://api.n2yo.com/rest/v1/satellite/positions/{norad_id}/{lat}/{lng}/{alt}/{seconds}/&apiKey={self.kEy}"

        def on_success(data):
            pos = data.get("positions", [{}])[0]
            satlat = pos.get('satlatitude', 'N/A')
            satlon = pos.get('satlongitude', 'N/A')
            myicon = "{ icon: myCustomIcon }"
            js_code = f"""
                if (typeof satMarker === 'undefined') {{
                    satMarker = L.marker([{satlat}, {satlon}], {myicon}).addTo(map)
                        .bindPopup("Name: {self.satname} | NORAD ID: {norad_id}").openPopup();
                }} else {{
                    satMarker.setLatLng([{satlat}, {satlon}]).update()
                        .bindPopup("Name: {self.satname} | NORAD ID: {norad_id}").openPopup();
                }}
            """
            self.map_view.page().runJavaScript(js_code)
            position_info = (
                f"🌍 Live Tracking Info:\n"
                f"Latitude: {pos.get('satlatitude', 'N/A'):.4f}°\n"
                f"Longitude: {pos.get('satlongitude', 'N/A'):.4f}°\n"
                f"Altitude: {pos.get('sataltitude', 'N/A')} km\n"
                f"Azimuth: {pos.get('azimuth', 'N/A')}°\n"
                f"Elevation: {pos.get('elevation', 'N/A')}°"
            )
            self.pos_display.setText(position_info)
        
        def on_error(e): #debug only
            print(f"[API_ERROR]: {e}")

        self.getAPIdata(url, on_success, on_error)


    
    def search_satellite(self):
        query = self.Search_bar.text().strip()
        if not query:
            QMessageBox.warning(None, "Input Error", "Please enter a satellite name or NORAD ID.")
            return
        
        if query.isdigit():
            self.currentsat = int(query)
            self.get_satellite_by_norad(int(query))
            return
        
        sat = self.find_satellite(query)
        if sat:
            self.currentsat = sat["norad_id"]
            self.get_satellite_by_norad(sat["norad_id"])
        else:
            QMessageBox.warning(None, "Not Found", "Satellite not found in local database.")
    

    def get_satellite_by_norad(self, norad_id):
        url = f"https://api.n2yo.com/rest/v1/satellite/tle/{norad_id}&apiKey={self.kEy}"
        
        def on_error(e):
            print(f"\n[Error retrieving position info]\n{e}")
            error_msg = "ERROR: API FAILED"
            self.info_display.setText(error_msg)
            self.tle_display.setText(error_msg)
            self.pos_display.setText(error_msg)
            self.speed_display.setText(error_msg)
            self.orbit_display.setText(error_msg)
            self.launchdate_display.setText(error_msg)
            return
        
        def on_success(data):
            satname = data.get("info", {}).get("satname", "Unknown")
            satid = data.get("info", {}).get("satid", "Unknown")
            tle_raw = data.get("tle", "")
            tle_lines = tle_raw.split("\r\n") if tle_raw else ["N/A", "N/A"]

            info = (
                f"Name: {satname}\n"
                f"NORAD ID: {satid}\n \n"
            )

            tle = (
                f"TLE Line 1: {tle_lines[0]}\n" 
                f"TLE Line 2: {tle_lines[1] if len(tle_lines) > 1 else 'N/A'}"
            )
            if norad_id == 50463:
                postition_data = "Note: James Webb Space Telescope (JWST) is located at Lagrange Point 2 and does not orbit the Earth, hence no live position data available. \nSee more here: https://webb.nasa.gov/content/webbLaunch/whereIsWebb.html"
                self.info_display.setText(info)
                self.pos_display.setText(postition_data)
                self.tle_display.clear()
                self.speed_display.clear()
                self.orbit_display.clear()
                self.launchdate_display.clear()
                return
            
            speed = self.speed_calculate(tle_lines[1])
            orbit, launch_data = self.estimate_time_in_space(tle_lines[1], norad_id)
            self.info_display.setText(info)
            self.tle_display.setText(tle)
            self.get_satellite_position(norad_id, lambda pos_info: self.pos_display.setText(pos_info))
            self.speed_display.setText(speed)
            self.orbit_display.setText(orbit)
            self.launchdate_display.setText(launch_data)

            self.satname = satname
        
        self.getAPIdata(url, on_success, on_error)


    def get_satellite_position(self, norad_id, on_success):
        lat = 10.762622
        lng = 106.660172
        alt = 5
        seconds = 1

        url = f"https://api.n2yo.com/rest/v1/satellite/positions/{norad_id}/{lat}/{lng}/{alt}/{seconds}/&apiKey={self.kEy}"


        def on_error(e):
            return f"\n[Error retrieving position info]\n{e}"

        def handler(data):
            pos = data.get("positions", [{}])[0]

            position_info = (
                f"Latitude: {pos.get('satlatitude', 'N/A'):.4f}°\n"
                f"Longitude: {pos.get('satlongitude', 'N/A'):.4f}°\n"
                f"Altitude: {pos.get('sataltitude', 'N/A')} km\n"
                f"Azimuth: {pos.get('azimuth', 'N/A')}°\n"
                f"Elevation: {pos.get('elevation', 'N/A')}°"
            )
            on_success(position_info)
            
        self.getAPIdata(url, handler, on_error)

    def speed_calculate(self, tle2):
        mean_motion_str = tle2[52:63].strip()
        mean_motion = float(mean_motion_str)

        mu = 398600.4418

        period_sec = 86400 / mean_motion

        a = (mu * (period_sec / (2 * math.pi))**2) ** (1/3)

        speed_kms = math.sqrt(mu / a)

        # Convert to other units
        speed_kmh = speed_kms * 3600         # km/h
        speed_mph = speed_kmh * 0.621371     # mi/h
        speed_ms  = speed_kms * 1000         # m/s

        return (
            f"{speed_kmh:,.2f} km/h\n"
            f"{speed_mph:,.2f} mph\n"
            f"{speed_ms:,.2f} m/s"
        )
        
    def estimate_time_in_space(self, tle2, norad_id):
        exception = [20580, 50463, 25544, 48274]
        try:
            mean_motion = float(tle2[52:63].strip()) 
            rev_number = int(tle2[63:68].strip()) 

            days_in_space = rev_number / mean_motion
            now = datetime.now(timezone.utc)
            if norad_id not in exception:
                launch_date = now - timedelta(days=days_in_space)
                launch_date = launch_date.strftime('%Y-%m-%d')
            elif norad_id == 25544:
                launch_date = "1998-11-20"
            elif norad_id == 20580:
                launch_date = "1990-4-24"
            elif norad_id == 48274:
                launch_date = "2021-4-29"
            elif norad_id == 50463:
                launch_date = "2021-12-25"

            orbit_data = (
                f"🕒 Time in Space Estimate Since Last TLE (Recorded Data) Restart:\n"
                f"Orbits: {rev_number:,}\n" + f"Days in Space: {days_in_space:.2f} days\n"
            )
            launch_date_data = (
                f"Estimated Launch Date (UTC): {launch_date}\n\n"
            )
            return orbit_data, launch_date_data

        except Exception as e:
            return f"\n[Error estimating time in space]\n{e}"

    def find_satellite(self,query):
        for _, satellites in self.satellite_data.items():
            for sat in satellites:
                if query.lower() in sat["name"].lower() or str(sat["norad_id"]) == query:
                    return sat
        return None
    
    def search_by_button_mode(self, button_text):
        with open(self.satellite_descriptions_path, 'r', encoding='utf-8') as f:
            satellite_descriptions = json.load(f)
        
        self.sat_list.clear()

        self.typeinfo_display.setText(satellite_descriptions.get(button_text, "Unknown"))

        for satellite in self.satellite_data.get(button_text, []):
            name = satellite.get("name", "Unknown")
            self.sat_list.addItem(name)
    
    def find_above_satellites(self):
        lat = 10.762622
        lng = 106.660172
        alt = 5
        radius = 70  # Degree radius for visible sky
        category_id = 52  # Starlink category

        url = f"https://api.n2yo.com/rest/v1/satellite/above/{lat}/{lng}/{alt}/{radius}/{category_id}/&apiKey={self.kEy}"

        def on_error(e):
            print(f"\n[Error retrieving position info]\n{e}")
            self.sat_list.clear()
            return
        
        def on_success(data):
            with open(self.satellite_descriptions_path, 'r', encoding='utf-8') as f:
                satellite_descriptions = json.load(f)
            if "above" not in data:
                QMessageBox.warning(None, "No Satellites Found", "No satellites found above your location.")
                return
            
            self.sat_list.clear()
            self.typeinfo_display.setText(satellite_descriptions.get("Above", "Unknown"))

            for sat in data["above"]:
                name = sat.get("satname", "Unknown")
                norad_id = sat.get("satid", "Unknown")
                item_text = f"{name}-SATID: {norad_id}"
                self.sat_list.addItem(item_text)

        self.getAPIdata(url, on_success, on_error)


    def handle_satlist_click(self, item):
        sat_name = item.text()
        if 'SATID' in sat_name:
            name = sat_name.split('-SATID: ')[0]
            self.Search_bar.setText(name)
            norad_id = sat_name.split('-SATID: ')[-1]
            self.currentsat = int(norad_id)
            self.get_satellite_by_norad(self.currentsat)
        else:
            self.Search_bar.setText(sat_name)
            self.search_satellite()

    def loadSatelliteData(self):
        satellite_names_json_path = os.path.join(os.path.dirname(__file__), "satellite_names.json")
        with open(satellite_names_json_path) as f:
            self.satellite_data = json.load(f)

    def logout(self):
        from src.auth import Login
        os.chdir(os.path.dirname(__file__))
        window = Login()
        window.show()
        self.close()