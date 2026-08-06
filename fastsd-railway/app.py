"""FastSD API Server for Stable Diffusion image generation."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from diffusers import StableDiffusionPipeline
import torch
from PIL import Image
from io import BytesIO
import base64
import os
from pathlib import Path

app = FastAPI(title="FastSD Stable Diffusion API")

# Configuration
MODEL_ID = os.getenv("SD_MODEL_ID", "runwayml/stable-diffusion-v1-5")
DEVICE = "cpu"  # Always CPU for Railway
CACHE_DIR = os.getenv("SD_CACHE_DIR", "/tmp/sd_models")

# Global pipeline (loaded once)
pipeline = None

def load_pipeline():
    """Load the Stable Diffusion pipeline."""
    global pipeline
    if pipeline is None:
        print(f"Loading model: {MODEL_ID}")
        pipeline = StableDiffusionPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float32,
            cache_dir=CACHE_DIR,
        )
        pipeline = pipeline.to(DEVICE)
        print("Model loaded successfully!")
    return pipeline

class ImageRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    width: int = 768
    height: int = 1344
    num_inference_steps: int = 20
    guidance_scale: float = 7.5
    seed: int = 42

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "device": DEVICE}

@app.post("/generate")
async def generate_image(request: ImageRequest):
    """Generate an image from a text prompt."""
    try:
        pipeline = load_pipeline()
        
        # Generate image
        image = pipeline(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            height=request.height,
            width=request.width,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            generator=torch.Generator(DEVICE).manual_seed(request.seed),
        ).images[0]
        
        # Convert to bytes
        img_bytes = BytesIO()
        image.save(img_bytes, format="PNG")
        img_base64 = base64.b64encode(img_bytes.getvalue()).decode()
        
        return {
            "status": "success",
            "image": img_base64,
            "format": "png",
            "prompt": request.prompt,
            "width": request.width,
            "height": request.height,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models():
    """List available model configurations."""
    return {
        "available_models": [
            "runwayml/stable-diffusion-v1-5",
            "stabilityai/stable-diffusion-2-1",
            "stabilityai/stable-diffusion-xl-base-1.0",
        ],
        "current_model": MODEL_ID,
        "device": DEVICE,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
