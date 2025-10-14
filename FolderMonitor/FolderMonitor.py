import os
import sys
import json
import time
import smtplib
import logging
import zipfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from email import encoders
from email.mime.text import MIMEText

# ---------- helpers ----------
def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def setup_logger(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler()
        ],
    )

def bytes_to_mb(b: int) -> float:
    return round(b / (1024 * 1024), 2)

def get_base_dir() -> Path:
    """Folder where the .py/.exe lives (PyInstaller-safe)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def resolve_relative_to_base(raw_path: str, base: Path) -> Path:
    """If raw_path is absolute, return as-is; if relative, resolve under base."""
    p = Path(raw_path)
    return p if p.is_absolute() else (base / p).resolve()

def list_new_files(watch: Path, state: dict, include_ext, exclude_ext, min_age_s: int):
    now = time.time()
    last_run_iso = state.get("last_run_utc", "1970-01-01T00:00:00Z")
    try:
        last_run = datetime.fromisoformat(last_run_iso.replace("Z", "+00:00"))
    except Exception:
        last_run = datetime(1970, 1, 1, tzinfo=timezone.utc)

    processed = set(state.get("processed_files", []))
    candidates = []

    for p in watch.glob("*"):
        if not p.is_file():
            continue
        ext = p.suffix.lower()

        if include_ext and ext not in include_ext:
            continue
        if exclude_ext and ext in exclude_ext:
            continue

        # skip files that might still be writing
        if (now - p.stat().st_mtime) < min_age_s:
            continue

        created_utc = datetime.fromtimestamp(p.stat().st_ctime, tz=timezone.utc)
        is_new_by_time = created_utc > last_run
        is_new_by_state = str(p) not in processed

        if is_new_by_time or is_new_by_state:
            candidates.append(p)

    return candidates

def make_zip_of_files(files, tmp_dir: Path) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    zip_path = tmp_dir / f"payload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    staging = tmp_dir / f"staging_{int(time.time())}"
    staging.mkdir()
    try:
        for f in files:
            shutil.copy2(f, staging / f.name)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in staging.iterdir():
                zf.write(f, arcname=f.name)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return zip_path

def attach_file(msg: MIMEMultipart, path: Path):
    part = MIMEBase("application", "octet-stream")
    with open(path, "rb") as f:
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{path.name}"')
    msg.attach(part)

def send_mail(smtp_cfg: dict, subject: str, body: str, attachments: list[Path]):
    msg = MIMEMultipart()
    msg["From"] = smtp_cfg["from_addr"]
    msg["To"] = ", ".join(smtp_cfg["to_addrs"])
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    for a in attachments:
        attach_file(msg, a)

    with smtplib.SMTP(smtp_cfg["host"], smtp_cfg["port"]) as server:
        if smtp_cfg.get("use_starttls", True):
            server.starttls()
        if smtp_cfg.get("username"):
            server.login(smtp_cfg["username"], smtp_cfg["password"])
        server.send_message(msg)

# ---------- main ----------
def main():
    base = get_base_dir()

    # load config.json from the app folder
    cfg_path = base / "config.json"
    cfg = load_json(cfg_path)

    # folders from config (can be absolute or relative)
    watch = Path(cfg["watch_folder"])
    backup = Path(cfg["backup_folder"])

    # state/log now resolve relative to the app folder unless absolute
    state_path = resolve_relative_to_base(cfg["state_file"], base)
    log_path   = resolve_relative_to_base(cfg["log_file"], base)

    include_ext = [e.lower() for e in cfg.get("include_extensions", [])]
    exclude_ext = [e.lower() for e in cfg.get("exclude_extensions", [])]
    min_age = int(cfg.get("min_file_age_seconds", 5))
    zip_before = bool(cfg.get("zip_before_email", False))
    max_mb = float(cfg.get("max_total_attachment_mb", 18))

    # set up logging
    setup_logger(log_path)
    logging.info("Starting Folder Monitor")

    # quick pause switch
    pause_flag = state_path.parent / "PAUSE"
    if pause_flag.exists():
        logging.info("PAUSE file detected; skipping this run.")
        return

    # ensure dirs
    for d in (watch, backup, state_path.parent):
        d.mkdir(parents=True, exist_ok=True)

    # load state
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    else:
        state = {}

    state.setdefault("last_run_utc", "1970-01-01T00:00:00Z")
    state.setdefault("processed_files", [])

    # find new files
    new_files = list_new_files(watch, state, include_ext, exclude_ext, min_age)
    if not new_files:
        logging.info("No new files found.")
        state["last_run_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(state, state_path)
        return

    total_bytes = sum(p.stat().st_size for p in new_files)
    total_mb = bytes_to_mb(total_bytes)
    logging.info(f"Found {len(new_files)} new file(s), total {total_mb} MB")

    # decide attachments
    attachments = []
    temp_to_cleanup = []

    if zip_before or (max_mb > 0 and total_mb > max_mb):
        tmp_dir = Path(os.getenv("TEMP", str(state_path.parent)))
        zip_path = make_zip_of_files(new_files, tmp_dir)
        attachments = [zip_path]
        temp_to_cleanup.append(zip_path)
        logging.info(f"Created ZIP: {zip_path} ({bytes_to_mb(zip_path.stat().st_size)} MB)")
        body_list = "\n".join(f" - {p.name}" for p in new_files)
    else:
        attachments = new_files
        body_list = "\n".join(f" - {p.name} ({bytes_to_mb(p.stat().st_size)} MB)" for p in new_files)

    subject = f'{cfg["smtp"].get("subject_prefix","[Folder Monitor]")} {len(new_files)} new file(s)'
    body = (
        f"The following files were detected in '{watch}':\n\n"
        f"{body_list}\n\n"
        f"Total size: {total_mb} MB\n"
        "This email was generated automatically."
    )

    # send email
    try:
        send_mail(cfg["smtp"], subject, body, attachments)
        logging.info("Email sent successfully.")
    except Exception as e:
        logging.error(f"Email send failed: {e}")
        return
    finally:
        for t in temp_to_cleanup:
            try:
                t.unlink(missing_ok=True)
            except Exception:
                pass

    # move files to backup
    for f in new_files:
        dest = backup / f.name
        if dest.exists():
            stem = dest.stem
            suff = dest.suffix
            dest = backup / f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suff}"
        shutil.move(str(f), str(dest))
        logging.info(f"Moved: {f} -> {dest}")
        if str(f) not in state["processed_files"]:
            state["processed_files"].append(str(f))

    # save state
    state["last_run_utc"] = datetime.now(timezone.utc).isoformat()
    save_json(state, state_path)
    logging.info("Done.")

if __name__ == "__main__":
    print("FolderMonitor is running... checking for new files.")
    main()
    print("FolderMonitor finished. You can close this window.")
