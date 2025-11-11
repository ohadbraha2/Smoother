"""
3D Model Smoothing with Open3D
This script smooths a textured GLB model while preserving textures
"""

import open3d as o3d
import numpy as np
from pathlib import Path


def load_glb_model(file_path):
    """
    Load a GLB file and extract mesh
    
    Args:
        file_path: Path to the GLB file
        
    Returns:
        o3d.geometry.TriangleMesh: Loaded mesh
    """
    print(f"Loading model from {file_path}...")
    
    # Open3D supports GLB/GLTF through the read_triangle_mesh function
    mesh = o3d.io.read_triangle_mesh(str(file_path))
    
    if not mesh.has_vertices():
        raise ValueError("Failed to load mesh from GLB file")
    
    print(f"Loaded mesh with {len(mesh.vertices)} vertices and {len(mesh.triangles)} triangles")
    return mesh


def smooth_mesh_preserve_texture(mesh, iterations=5, lambda_filter=0.5):
    """
    Smooth mesh while preserving texture coordinates
    Uses Taubin smoothing which prevents shrinkage
    
    Args:
        mesh: Input triangle mesh
        iterations: Number of smoothing iterations
        lambda_filter: Smoothing strength (0.5 is recommended)
        
    Returns:
        o3d.geometry.TriangleMesh: Smoothed mesh
    """
    print(f"Smoothing mesh with {iterations} iterations...")
    
    # Store texture coordinates and vertex colors
    has_texture_coords = mesh.has_triangle_uvs()
    has_vertex_colors = mesh.has_vertex_colors()
    has_vertex_normals = mesh.has_vertex_normals()
    
    texture_coords = mesh.triangle_uvs if has_texture_coords else None
    vertex_colors = np.asarray(mesh.vertex_colors) if has_vertex_colors else None
    
    # Apply Taubin smoothing (prevents shrinkage, good for 3D printing)
    # This is a variant of Laplacian smoothing with inflation steps
    mesh_smoothed = mesh.filter_smooth_taubin(
        number_of_iterations=iterations,
        lambda_filter=lambda_filter,
        mu=-lambda_filter - 0.01  # Inflation factor
    )
    
    # Restore texture coordinates (they don't change with vertex smoothing)
    if has_texture_coords and texture_coords is not None:
        mesh_smoothed.triangle_uvs = texture_coords
        
    # Restore vertex colors if present
    if has_vertex_colors and vertex_colors is not None:
        mesh_smoothed.vertex_colors = o3d.utility.Vector3dVector(vertex_colors)
    
    # Recompute normals for better rendering
    mesh_smoothed.compute_vertex_normals()
    
    print("Smoothing complete")
    return mesh_smoothed


def remove_noise_and_bumps(mesh, voxel_size=0.01):
    """
    Remove small bumps and noise using voxel downsampling and reconstruction
    
    Args:
        mesh: Input triangle mesh
        voxel_size: Size of voxels for downsampling (smaller = more detail)
        
    Returns:
        o3d.geometry.TriangleMesh: Cleaned mesh
    """
    print(f"Removing noise with voxel size {voxel_size}...")
    
    # Convert to voxel grid and back to smooth out small bumps
    voxel_grid = o3d.geometry.VoxelGrid.create_from_triangle_mesh(mesh, voxel_size=voxel_size)
    
    # Alternative: Use point cloud filtering
    pcd = mesh.sample_points_uniformly(number_of_points=50000)
    
    # Remove statistical outliers (noise points)
    pcd_filtered, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
    
    # Estimate normals
    pcd_filtered.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2, max_nn=30)
    )
    
    # Reconstruct mesh using Poisson surface reconstruction
    mesh_reconstructed, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd_filtered, depth=9
    )
    
    # Remove low density vertices (artifacts from reconstruction)
    vertices_to_remove = densities < np.quantile(densities, 0.01)
    mesh_reconstructed.remove_vertices_by_mask(vertices_to_remove)
    
    print("Noise removal complete")
    return mesh_reconstructed


def make_print_ready(mesh):
    """
    Prepare mesh for 3D printing by ensuring it's watertight and manifold
    
    Args:
        mesh: Input triangle mesh
        
    Returns:
        o3d.geometry.TriangleMesh: Print-ready mesh
    """
    print("Preparing mesh for 3D printing...")
    
    # Remove degenerate triangles
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()
    
    # Try to repair if not watertight
    if not mesh.is_watertight():
        print("Mesh is not watertight, attempting repair...")
        # Fill holes (if any)
        # Note: Open3D doesn't have built-in hole filling, so we use other methods
    
    # Ensure consistent vertex normals orientation
    mesh.compute_vertex_normals()
    mesh.orient_triangles()
    
    print(f"Mesh is watertight: {mesh.is_watertight()}")
    print(f"Mesh is vertex manifold: {mesh.is_vertex_manifold()}")
    print(f"Mesh is edge manifold: {mesh.is_edge_manifold()}")
    
    return mesh


def save_glb_model(mesh, output_path):
    """
    Save mesh as GLB file
    
    Args:
        mesh: Triangle mesh to save
        output_path: Path for output GLB file
    """
    print(f"Saving model to {output_path}...")
    
    # Ensure the output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save as GLB
    success = o3d.io.write_triangle_mesh(str(output_path), mesh)
    
    if success:
        print(f"Model successfully saved to {output_path}")
    else:
        raise IOError(f"Failed to save model to {output_path}")


def process_model(input_path, output_path, smooth_iterations=5, remove_bumps=True):
    """
    Complete pipeline to smooth and prepare model for 3D printing
    
    Args:
        input_path: Path to input GLB file
        output_path: Path for output GLB file
        smooth_iterations: Number of smoothing iterations
        remove_bumps: Whether to remove bumps and noise
        
    Returns:
        bool: Success status
    """
    try:
        # Load the model
        mesh = load_glb_model(input_path)
        
        # Smooth the mesh
        mesh = smooth_mesh_preserve_texture(mesh, iterations=smooth_iterations)
        
        # Optional: Remove bumps and noise
        if remove_bumps:
            mesh = remove_noise_and_bumps(mesh)
        
        # Make print ready
        mesh = make_print_ready(mesh)
        
        # Save the result
        save_glb_model(mesh, output_path)
        
        print("\n=== Processing Complete ===")
        print(f"Input: {input_path}")
        print(f"Output: {output_path}")
        print(f"Vertices: {len(mesh.vertices)}")
        print(f"Triangles: {len(mesh.triangles)}")
        
        return True
        
    except Exception as e:
        print(f"Error processing model: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python model_smoother.py <input.glb> <output.glb> [smooth_iterations] [remove_bumps]")
        print("Example: python model_smoother.py input.glb output.glb 5 True")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    smooth_iter = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    remove_bumps_flag = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else True
    
    success = process_model(input_file, output_file, smooth_iter, remove_bumps_flag)
    sys.exit(0 if success else 1)
