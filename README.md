# 🖥️ PingMonitor

**PingMonitor** is a lightweight **network availability and uptime checker** designed to continuously monitor multiple hosts, log their responses, and send email alerts when repeated failures occur.  
Built for **Windows environments**, it runs quietly in the background or as a startup service.

---

## 📘 Overview
PingMonitor is ideal for IT admins or DevOps engineers who need to:
- Detect network outages across multiple endpoints.
- Receive instant alerts when critical systems stop responding.
- Maintain uptime logs for troubleshooting and reporting.

It can run both **interactively** or as a **startup tray service**, making it perfect for remote monitoring stations or kiosk setups.

---

## ✨ Features
- 🔁 **Multi-endpoint pinging** — monitor multiple IPs or hostnames concurrently  
- 🕓 **Configurable intervals** — set custom ping frequency and timeout  
- 📊 **Auto-logging** — creates timestamped logs for response results  
- 📧 **Email notifications** — get alerts after a defined number of failed pings  
- ⚙️ **Customizable JSON config** — define targets, SMTP details, and retry behavior  
- 🪟 **Simple Windows deployment** — one-click batch installer for startup integration

---

## 🚀 Quick Start

### 1️⃣ Edit your configuration
Open `config.json` and update the values according to your preferred ping frequency, alert limits, and email settings.  
> 💡 The included configuration uses *example* values — replace them before running.

---

### 2️⃣ Run the tool
Run the `.exe` file:  
ping_monitor.exe  

The tool will begin monitoring all devices defined in your `config.json` file and log the results in real time.

---

### 3️⃣ Optional: Run automatically on startup
Use the included batch file:  
install_ping_monitor_usertray.bat  

To uninstall:  
uninstall_ping_monitor.bat  

---

## 🧩 Folder Structure
| File / Folder | Description |
|----------------|--------------|
| `ping_monitor.exe` | Compiled executable for Windows |
| `ping_monitor.py` | Main application script |
| `config.json` | Example configuration file |
| `icon.ico` | Tray icon asset |
| `install_ping_monitor_usertray.bat` | Adds PingMonitor to Windows startup |
| `uninstall_ping_monitor.bat` | Removes PingMonitor from startup |
| `PingMonitor_Guide.pdf` | Optional user guide (if included) |

---

## 📸 Example Screenshots


<p align="left">
  <img src="https://github.com/user-attachments/assets/0f7be37f-aac2-48a6-a132-b5574a9b1b43" width="320" alt="Email Alert Example">
</p>


---

## 🧠 Notes
Example configuration only — replace with your own credentials before deployment.

---

## 🧑‍💻 Author
Developed by **Christos Paraskevopoulos**  
📧 [christos1129@gmail.com](mailto:christos1129@gmail.com)

© 2025 — Part of the [DevOps Automation Portfolio](../README.md)
