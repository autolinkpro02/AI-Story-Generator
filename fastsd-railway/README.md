# FastSD Stable Diffusion API

Standalone Stable Diffusion image generation service for Railway deployment.

## Capabilities

### ✅ What it CAN do:
- Generate **high-quality 2D static images** from text prompts
- Support multiple Stable Diffusion models (v1.5, v2.1, SDXL)
- Custom resolution, guidance scale, inference steps
- Seed control for reproducibility
- Batch processing via API

### ❌ What it CANNOT do natively:
- **3D image generation** - would need specialized 3D-GS or TripoSR models
- **Moving/animated images** - would need Video Diffusion or frame interpolation
- **Real-time video** - requires separate video generation pipeline

## Workarounds for Advanced Features

### For 3D Images:
```python
# Option 1: Use Stable Diffusion 3D (if released)
# Option 2: Post-process with TripoSR (image-to-3D)
# Option 3: Use separate 3D model like Point-E
```

### For Animated Images:
```python
# Option 1: Use Stable Video Diffusion (text-to-video)
# Option 2: Frame interpolation with RIFE
# Option 3: Latent consistency models for multi-frame
```

## Deployment on Railway

1. Create a new Railway service
2. Connect this repository/folder
3. Deploy with this Dockerfile
4. Set environment variables:
   - `SD_MODEL_ID`: Model to use (default: runwayml/stable-diffusion-v1-5)
   - `SD_CACHE_DIR`: Cache directory for models

## API Endpoints

### Health Check
```bash
GET /health
```

### Generate Image
```bash
POST /generate
Content-Type: application/json

{
  "prompt": "a beautiful golden fox in a magical glowing forest",
  "negative_prompt": "blurry, low quality",
  "width": 768,
  "height": 1344,
  "num_inference_steps": 20,
  "guidance_scale": 7.5,
  "seed": 42
}
```

### List Models
```bash
GET /models
```

## Configuration in Main App

Update `config.py`:
```python
FASTSDCPU_API_URL = os.getenv("FASTSD_API_URL", "https://your-fastsd-railway.up.railway.app/generate")
```

Update `modules/image_generator.py` to call the API instead of Pollinations.ai.

## Performance Notes

- **CPU-only**: ~30-60 seconds per image (depends on model)
- **Memory**: ~4-6GB RAM required
- **Startup**: Model download on first run (~2-4GB)
- **Cost**: Railway CPU hours scale with generation time

## Model Options

| Model | Size | Quality | Speed |
|-------|------|---------|-------|
| SD v1.5 | ~4GB | Good | Fast |
| SD v2.1 | ~5GB | Better | Medium |
| SDXL | ~7GB | Excellent | Slow |

## Next Steps

1. Deploy this folder as separate Railway service
2. Update main app to use `FASTSD_API_URL`
3. Remove Pollinations.ai dependency
4. For 3D/animation: Consider additional specialized services
