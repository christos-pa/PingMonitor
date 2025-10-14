# PingMonitor

Lightweight network availability checker that pings multiple endpoints and logs results.

## Features
- Ping several hosts at once
- Log response success/failure
- Email alert on repeated failures
- Simple to install on Windows

## How to Use
1. Edit `config.json` with your own addresses and settings.
2. Run:
   ```bash
   python ping_monitor.py
   ```
3. (Optional) Use `install_ping_monitor_usertray.bat` to run on startup.

## Note
The included `config.json` contains only **example** values.  
Replace them with your own when deploying.

---

© 2025 Christos Paraskevopoulos
