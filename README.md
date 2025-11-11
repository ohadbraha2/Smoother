# 3D Model Smoothing with Open3D

This directory contains Python scripts for smoothing and optimizing GLB models for 3D printing using Open3D.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Command Line

```bash
python model_smoother.py input.glb output.glb [smooth_iterations] [remove_bumps]
```

**Arguments:**
- `input.glb`: Path to the input GLB file
- `output.glb`: Path for the output smoothed GLB file
- `smooth_iterations` (optional): Number of smoothing iterations (default: 5)
- `remove_bumps` (optional): Whether to remove bumps (True/False, default: True)

**Example:**
```bash
python model_smoother.py my_model.glb smoothed_model.glb 10 True
```

### Python API

```python
from model_smoother import process_model

# Process a model
success = process_model(
    input_path="input.glb",
    output_path="output.glb",
    smooth_iterations=5,
    remove_bumps=True
)
```

## Features

### Taubin Smoothing
- Preserves model volume (no shrinkage)
- Smooths out surface irregularities
- Maintains texture coordinates
- Ideal for 3D printing preparation

### Noise and Bump Removal
- Statistical outlier removal
- Poisson surface reconstruction
- Removes small surface imperfections
- Voxel-based filtering

### Print-Ready Preparation
- Removes degenerate triangles
- Ensures manifold geometry
- Checks for watertight mesh
- Orients triangles consistently

## Integration with Edge Functions

To integrate with Supabase Edge Functions:

1. **Create an Edge Function** that accepts file uploads
2. **Save the uploaded GLB** to temporary storage
3. **Call the Python script** using Deno's subprocess
4. **Return the processed GLB** to the client

Example Edge Function structure:

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

serve(async (req) => {
  // 1. Receive GLB file from request
  const formData = await req.formData();
  const file = formData.get("file") as File;
  
  // 2. Save to temporary location
  const inputPath = `/tmp/input_${Date.now()}.glb`;
  const outputPath = `/tmp/output_${Date.now()}.glb`;
  await Deno.writeFile(inputPath, new Uint8Array(await file.arrayBuffer()));
  
  // 3. Run Python script
  const process = Deno.run({
    cmd: ["python3", "model_smoother.py", inputPath, outputPath, "5", "True"],
    stdout: "piped",
    stderr: "piped",
  });
  
  await process.status();
  
  // 4. Read processed file
  const processedFile = await Deno.readFile(outputPath);
  
  // 5. Clean up
  await Deno.remove(inputPath);
  await Deno.remove(outputPath);
  
  // 6. Return processed GLB
  return new Response(processedFile, {
    headers: {
      "Content-Type": "model/gltf-binary",
      "Content-Disposition": "attachment; filename=smoothed.glb"
    }
  });
});
```

## Algorithm Details

### Smoothing Algorithm
Uses **Taubin smoothing** which alternates between:
1. **Shrinking step** (λ filter): Smooths the surface
2. **Inflation step** (μ filter): Prevents volume loss

This maintains the overall shape while removing high-frequency details.

### Bump Removal
1. Converts mesh to point cloud
2. Removes statistical outliers
3. Reconstructs surface using Poisson reconstruction
4. Filters low-density artifacts

### Manifold Checking
Ensures the mesh is:
- **Vertex manifold**: Each vertex is part of a single connected fan of triangles
- **Edge manifold**: Each edge is shared by at most two triangles
- **Watertight**: No holes in the surface

## Performance Tips

- **Smooth iterations**: Start with 5, increase for more smoothing
- **Voxel size**: Smaller = more detail, but slower processing
- **Large models**: Consider decimating before smoothing
- **Texture preservation**: UVs are preserved during smoothing

## Limitations

- Very large models (>1M triangles) may be slow
- Complex texture blending not supported
- Some GLB features may not be preserved (animations, multiple meshes)

## Troubleshooting

**Error: "Failed to load mesh"**
- Ensure the GLB file is valid
- Check that Open3D is properly installed

**Mesh becomes too smooth**
- Reduce smooth_iterations parameter
- Use smaller lambda_filter value

**Processing is slow**
- Reduce voxel_size for bump removal
- Decimate mesh before processing
- Disable bump removal for faster processing

## License

This code is provided as-is for use with the 3D Model Smoother application.
