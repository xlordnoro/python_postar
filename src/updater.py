import subprocess
import sys
import platform
from pathlib import Path

def main():
    base_dir = Path.cwd()
    system = platform.system().lower()

    py_script = base_dir / "python_postar.py"
    exe_win = base_dir / "python_postar.exe"
    bin_linux = base_dir / "python_postar"
    app_macos = base_dir / "python_postar.app"

    cmd = None

    # ---------------- Windows ----------------
    if system == "windows":
        if py_script.exists():
            print("[INFO] Running: python python_postar.py -u\n")
            cmd = ["python", str(py_script), "-u"]
        elif exe_win.exists():
            print("[INFO] Running: python_postar.exe -u\n")
            cmd = [str(exe_win), "-u"]

    # ---------------- Linux ----------------
    elif system == "linux":
        if py_script.exists():
            print("[INFO] Running: python3 python_postar.py -u\n")
            cmd = ["python3", str(py_script), "-u"]
        elif bin_linux.exists():
            print("[INFO] Running: ./python_postar -u\n")
            cmd = [str(bin_linux), "-u"]

    # ---------------- macOS ----------------
    elif system == "darwin":
        if py_script.exists():
            print("[INFO] Running: python3 python_postar.py -u\n")
            cmd = ["python3", str(py_script), "-u"]
        elif app_macos.exists():
            print("[INFO] Running: python_postar.app -u\n")
            cmd = ["open", "-a", str(app_macos), "--args", "-u"]
        elif bin_linux.exists():
            print("[INFO] Running: ./python_postar -u\n")
            cmd = [str(bin_linux), "-u"]

    # ---------------- Validation ----------------
    if not cmd:
        print("[ERROR] Could not detect installation type.")
        print("Expected python_postar.py or platform binary in:")
        print(base_dir)
        pause_before_exit()
        sys.exit(1)

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=base_dir,
            text=True,
            bufsize=1
        )

        for line in process.stdout:
            print(line, end="")

        process.wait()

        if process.returncode != 0:
            print(f"[ERROR] Updater exited with code {process.returncode}")
            pause_before_exit()

        sys.exit(process.returncode)

    except KeyboardInterrupt:
        process.terminate()
        pause_before_exit()
        sys.exit(1)

    except Exception as e:
        print(f"[ERROR] Failed to launch updater: {e}")
        pause_before_exit()
        sys.exit(1)


def pause_before_exit():
    """Pause the console safely only if stdin is available."""
    if sys.stdin and sys.stdin.isatty():
        try:
            input("\nPress ENTER to exit...")
        except (EOFError, RuntimeError):
            # In case stdin disappears unexpectedly
            print("[INFO] No console input available. Exiting...")
    else:
        # No terminal attached (GUI, service, double-clicked exe, etc.)
        print("[INFO] No console attached. Exiting...")


if __name__ == "__main__":
    main()
