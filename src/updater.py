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
        sys.exit(process.returncode)

    except KeyboardInterrupt:
        process.terminate()
        sys.exit(1)

    except Exception as e:
        print(f"[ERROR] Failed to launch updater: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
