# ping_monitor.py
import os, sys, re, time, json, subprocess, ctypes, smtplib, threading
from email.mime.text import MIMEText

# ----------------- single-instance + base paths -----------------
_mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "Global\\PingMonitorSingleInstance")
if ctypes.GetLastError() == 183:  # already running
    # Show info only if we have a desktop; otherwise just exit quietly
    try:
        ctypes.windll.user32.MessageBoxW(
            0,
            "Ping Monitor is already running in the background.\n\n"
            "Use Task Scheduler to stop/start it if needed.",
            "Ping Monitor",
            0x40
        )
    except Exception:
        pass
    sys.exit(0)

def BASE_DIR():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = BASE_DIR()
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
ICON_PATH = os.path.join(APP_DIR, "icon.ico")
LOG_PATH  = os.path.join(APP_DIR, "ping_monitor.log")

# --------------------------- logging ----------------------------
# simple line-buffered log; safe to remove if you don’t want a file
def log_open():
    try:
        return open(LOG_PATH, "a", buffering=1, encoding="utf-8")
    except Exception:
        return None

_log = log_open()
def log_print(*a):
    s = " ".join(str(x) for x in a)
    if _log:
        import datetime
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _log.write(ts + " " + s + "\n")

def msg_error(text, title="Ping Monitor"):
    try:
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)
    except Exception:
        # no desktop (e.g., SYSTEM session) – just log
        log_print("ERROR:", text)

# --------------------------- load config ------------------------
if not os.path.exists(CONFIG_PATH):
    msg_error(f"config.json not found.\nExpected here:\n{CONFIG_PATH}")
    sys.exit(1)

try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
except Exception as e:
    msg_error(f"Could not read config.json:\n{e}")
    sys.exit(1)

TO = cfg["ToAddresses"]                       # list of recipients
FROM = cfg["FromAddress"]["Email"]
APP_PASSWORD = cfg["FromAddress"]["Password"]

MAX_TIMEOUT_MS = int(cfg["MaxTimeoutMs"])
FAILS_BEFORE_ALERT = int(cfg["MaxFailuresBeforeAlert"])
INTERVAL_SECONDS = float(cfg["PingFrequencyMs"]) / 1000.0
SEND_RECOVERY = bool(cfg.get("SendRecoveryEmail", False))

SMTP_SERVER = cfg["SmtpServer"]
SMTP_PORT = int(cfg["SmtpPort"])
USE_STARTTLS = bool(cfg.get("UseStartTls", True))

DEVICES = cfg["Devices"]  # [{ "Name": "...", "IP": "..." }, ...]

# -------------------------- helpers -----------------------------
latency_re = re.compile(r"time[=<]([0-9]+)ms")
fail_counts = {d["IP"]: 0 for d in DEVICES}
alerted      = {d["IP"]: False for d in DEVICES}

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = FROM
    msg["To"]   = ", ".join(TO)
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        if USE_STARTTLS:
            s.starttls()
        s.login(FROM, APP_PASSWORD)
        s.sendmail(FROM, TO, msg.as_string())

CREATE_NO_WINDOW = 0x08000000  # hide ping.exe windows

def ping_once(ip, timeout_ms):
    r = subprocess.run(
        ["ping", "-n", "1", "-w", str(timeout_ms + 1000), ip],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW
    )
    out = r.stdout or ""
    m = latency_re.search(out)
    latency = int(m.group(1)) if m else None
    is_fail = (latency is None) or (latency > timeout_ms)
    return latency, is_fail

log_print(
    f"START: {len(DEVICES)} device(s), every {INTERVAL_SECONDS:.1f}s; "
    f"alert after {FAILS_BEFORE_ALERT} fails (> {MAX_TIMEOUT_MS}ms or no reply)."
)

# -------------------------- main worker -------------------------
stop_event = threading.Event()

def worker_loop():
    while not stop_event.is_set():
        for d in DEVICES:
            if stop_event.is_set():
                break
            name, ip = d["Name"], d["IP"]
            latency, is_fail = ping_once(ip, MAX_TIMEOUT_MS)

            if is_fail:
                status = "timeout" if latency is None else f"{latency} ms (slow)"
                log_print(f"{name}: FAIL ({status}) count={fail_counts[ip]+1}")
            else:
                log_print(f"{name}: OK ({latency} ms)")

            if is_fail:
                fail_counts[ip] += 1
                if not alerted[ip] and fail_counts[ip] >= FAILS_BEFORE_ALERT:
                    lat_text = f"{latency} ms" if latency is not None else "no reply"
                    subject = f"[ALERT] {name} – {lat_text}"
                    body = (
                        "Ping Test Alert\n\n"
                        f"Device Name: {name}\n"
                        f"IP Address: {ip}\n"
                        f"Status: {lat_text}\n"
                        f"Consecutive failures: {fail_counts[ip]}\n"
                        "Please investigate the device or network connection."
                    )
                    try:
                        send_email(subject, body)
                        log_print(f"{name}: ALERT email sent.")
                        alerted[ip] = True
                    except Exception as e:
                        log_print(f"{name}: Email failed: {e}")
            else:
                if fail_counts[ip] > 0 or alerted[ip]:
                    log_print(f"{name}: RECOVERED ({latency} ms)")
                    if SEND_RECOVERY and alerted[ip]:
                        subject = f"[RECOVERY] {name} – {latency} ms"
                        body = (
                            "Ping Recovery Notification\n\n"
                            f"Device Name: {name}\n"
                            f"IP Address: {ip}\n"
                            f"Status: OK ({latency} ms)\n"
                            "The device has recovered."
                        )
                        try:
                            send_email(subject, body)
                            log_print(f"{name}: Recovery email sent.")
                        except Exception as e:
                            log_print(f"{name}: Recovery email failed: {e}")
                fail_counts[ip] = 0
                alerted[ip] = False

        stop_event.wait(INTERVAL_SECONDS)

# --------------------------- tray icon --------------------------
def has_interactive_desktop() -> bool:
    # In SYSTEM session (session 0) this raises or returns 0 → no tray
    try:
        return ctypes.windll.user32.GetDesktopWindow() != 0
    except Exception:
        return False

def start_tray_icon():
    # Only show tray if we’re in a user desktop session
    if not has_interactive_desktop():
        return

    try:
        import pystray
        from PIL import Image
    except Exception as e:
        log_print("Tray not available (missing pystray/Pillow):", e)
        return

    # build icon image (from icon.ico if present; else blank)
    try:
        if os.path.exists(ICON_PATH):
            image = Image.open(ICON_PATH)
        else:
            image = Image.new("RGBA", (16,16), (0,0,0,0))
    except Exception:
        image = Image.new("RGBA", (16,16), (0,0,0,0))

    def on_open_log(icon, item):
        os.startfile(LOG_PATH)

    def on_exit(icon, item):
        stop_event.set()
        icon.visible = False
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Open log", on_open_log, default=False),
        pystray.MenuItem("Exit", on_exit)
    )
    icon = pystray.Icon("PingMonitor", image, "Ping Monitor", menu)
    icon.run()  # blocks until Exit

# ----------------------------- run ------------------------------
t = threading.Thread(target=worker_loop, daemon=True)
t.start()

# tray (non-blocking in SYSTEM/no-desktop; blocking with user tray)
start_tray_icon()

# If no tray (SYSTEM), keep the worker alive until stop_event set externally
if not has_interactive_desktop():
    try:
        while not stop_event.is_set():
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass

# graceful shutdown
stop_event.set()
t.join(timeout=5)
log_print("STOP")
if _log:
    _log.close()
