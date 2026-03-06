import os
import shutil
from main import chat
from logger import LOG_FILE

def test_logging():
    # Clear log file if exists
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    
    print("=== Testing Chat Logging (Failures Only) ===")
    
    user_id = "test_logger_verify"
    
    # 1. SUCCESSFUL QUERY -> Should NOT log
    print("\nSending (Success): 'berapa tarif pajak restoran?'")
    chat(user_id, "berapa tarif pajak restoran?")
    
    # 2. FAILED QUERY -> Should LOG
    print("\nSending (Fail): 'resep nasi goreng'")
    chat(user_id, "resep nasi goreng") # Likely NO_INTENT
    
    # 3. SUCCESSFUL FLOW -> Should NOT log
    print("\nSending (Success): 'bayar pajak restoran'")
    chat(user_id, "bayar pajak restoran")
    
    # Check log content
    if not os.path.exists(LOG_FILE):
        print("\n[WARN] Log file not created yet (might vary depending on impl)")
        
    if os.path.exists(LOG_FILE):
        print(f"\nLog File Content ({LOG_FILE}):")
        with open(LOG_FILE, "r") as f:
            content = f.read()
            print(content)
            
        # Assertion logic
        if "pajak_restoran" in content:
            print("\n[FAIL] Successful intent 'pajak_restoran' was logged (Should be filtered out)!")
        else:
            print("\n[PASS] Successful intent was NOT logged.")
            
        if "resep nasi goreng" in content:
            print("[PASS] Failed query was logged.")
        else:
            print("[FAIL] Failed query was NOT logged!")
    else:
        # If no failures occured (unlikely given 'resep nasi goreng'), file might not be created if empty.
        # But 'resep nasi goreng' should trigger create.
        print("\n[FAIL] Log file missing, expected entries.")

if __name__ == "__main__":
    test_logging()
