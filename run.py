import sys
import uvicorn
from pathlib import Path

if __name__ == "__main__":
    # Ensure current directory is in Python path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    
    print("======================================================")
    print("  💎 Credence — Secure Achievement & Credential Platform")
    print("  🌐 Server running at: http://127.0.0.1:8000")
    print("  📬 Dev Mailbox at: http://127.0.0.1:8000/mailbox")
    print("  🛡️ Security: Bcrypt, Dual-Token JWT, 2FA, Magic-Bytes")
    print("======================================================")
    
    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
