import os
import sys
import time
import subprocess

def run_servers():
    venv_python = os.path.join(".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        venv_python = sys.executable  # fallback to active python if venv not configured yet

    print(f"Using Python interpreter: {venv_python}")
    print("[Qualix] Launching FastAPI Backend on http://127.0.0.1:8000...")
    
    # Start FastAPI in background
    backend_proc = subprocess.Popen(
        [venv_python, "-m", "uvicorn", "backend.main:app", "--port", "8000", "--host", "127.0.0.1", "--reload"]
    )

    
    # Wait for backend to start up
    time.sleep(3)
    
    print("[Qualix] Launching Streamlit Frontend on http://localhost:8080...")
    # Start Streamlit in foreground
    frontend_proc = subprocess.Popen(
        [venv_python, "-m", "streamlit", "run", "frontend/app.py", "--server.port", "8080", "--server.headless", "true"]
    )
    
    try:
        # Keep launcher alive and monitor processes
        while True:
            # Simple check to see if backend crashed
            ret_b = backend_proc.poll()
            ret_f = frontend_proc.poll()
            
            if ret_b is not None:
                print(f"FastAPI Backend exited with code {ret_b}")
                break
            if ret_f is not None:
                print(f"Streamlit Frontend exited with code {ret_f}")
                break
                
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[Qualix] Stopping Qualix AI processes...")
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait()
        frontend_proc.wait()
        print("Qualix AI servers stopped cleanly.")

if __name__ == "__main__":
    run_servers()
