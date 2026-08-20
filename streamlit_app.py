# Root-level Streamlit entrypoint for Streamlit Community Cloud deployment.
# Streamlit Cloud requires the main app file to be at the repo root.
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# Re-export the full app
exec(open(os.path.join(os.path.dirname(__file__), "layer7_frontend", "app.py")).read())
