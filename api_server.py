from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import logging
from model_smoother import process_model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GLB Model Processor API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "service": "GLB Model Processor API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/process")
async def process_glb(
    file: UploadFile = File(...),
    smooth_iterations: int = 5,
    remove_bumps: bool = True
):
    """
    Process a GLB file with smoothing and print-ready preparation.
    
    Args:
        file: The GLB file to process
        smooth_iterations: Number of smoothing iterations (default: 5)
        remove_bumps: Whether to remove bumps and noise (default: True)
    
    Returns:
        Processed GLB file
    """
    logger.info(f"Received file: {file.filename}, size: {file.size if hasattr(file, 'size') else 'unknown'}")
    
    if not file.filename.endswith('.glb'):
        raise HTTPException(status_code=400, detail="Only GLB files are supported")
    
    input_path = None
    output_path = None
    
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.glb') as tmp_input:
            content = await file.read()
            tmp_input.write(content)
            input_path = tmp_input.name
            logger.info(f"Saved input file to: {input_path}")
        
        # Create output path
        output_path = input_path.replace('.glb', '_processed.glb')
        
        # Process the model
        logger.info(f"Starting processing with {smooth_iterations} iterations, remove_bumps={remove_bumps}")
        success = process_model(
            input_path, 
            output_path, 
            smooth_iterations=smooth_iterations, 
            remove_bumps=remove_bumps
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Model processing failed")
        
        logger.info(f"Processing complete, output saved to: {output_path}")
        
        # Return the processed file
        return FileResponse(
            output_path,
            media_type="model/gltf-binary",
            filename="smoothed-model.glb",
            headers={
                "Content-Disposition": "attachment; filename=smoothed-model.glb"
            }
        )
    
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    finally:
        # Clean up temporary files
        if input_path and os.path.exists(input_path):
            try:
                os.unlink(input_path)
                logger.info(f"Cleaned up input file: {input_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up input file: {e}")
        
        # Note: output_path is returned as FileResponse, so it will be cleaned up by FastAPI

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
