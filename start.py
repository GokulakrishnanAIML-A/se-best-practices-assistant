"""Entrypoint script that reads PORT from environment and starts uvicorn."""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("layer6_api.main:app", host="0.0.0.0", port=port)
