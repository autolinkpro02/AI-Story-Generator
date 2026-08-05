Deployment guide for Railway

1. Create a GitHub repo for this project and push the code.

2. In Railway, create a new Project -> "Provision from GitHub" and connect the repo.

3. Set Environment Variables in Railway (from your local .env):
   - HUGGINGFACE_API_TOKEN
   - HUGGINGFACE_IMAGE_MODEL (optional)
   - FORCE_PLACEHOLDERS (True/False)
   - OLLAMA_URL, OLLAMA_MODEL (if used)

4. Set the Start Command (default Procfile will be used):
   - `python web_app.py`

5. Railway exposes a `PORT` environment variable. `web_app.py` reads `PORT` and binds to 0.0.0.0.

6. Deploy. Monitor logs; image-generation calls require internet access to Hugging Face or Pollinations.

Notes & Recommendations
- For production, consider switching to a proper WSGI framework (Flask/FastAPI) and `gunicorn`.
- SDXL via Hugging Face Inference will be slower; for speed and consistency use a hosted image API or a GPU-backed service.
- Keep secrets in Railway Environment Variables — do NOT commit `.env` to the repo.
