import pytest
import numpy as np
from mesh_reader_cpp import create_mesh_reader, STLReader, NASReader

def test_stl_binary_reader():
    reader = STLReader()
    mesh_data = reader.read("data/test_cube.stl")
    
    assert mesh_data.vertices.shape[1] == 3
    assert mesh_data.faces.shape[1] == 3
    assert mesh_data.normals.shape[1] == 3
    assert len(mesh_data.faces) > 0
    assert len(mesh_data.vertices) > 0

def test_nas_reader():
    reader = NASReader()
    mesh_data = reader.read("data/test_cube.nas")
    
    assert mesh_data.vertices.shape[1] == 3
    assert mesh_data.faces.shape[1] == 3
    assert mesh_data.normals.shape[1] == 3
    assert len(mesh_data.faces) > 0
    assert len(mesh_data.vertices) > 0

def test_create_mesh_reader():
    stl_reader = create_mesh_reader("test.stl")
    assert isinstance(stl_reader, STLReader)
    
    nas_reader = create_mesh_reader("test.nas")
    assert isinstance(nas_reader, NASReader)
    
    with pytest.raises(RuntimeError):
        create_mesh_reader("test.unknown")

def test_mesh_data_consistency():
    reader = STLReader()
    mesh_data = reader.read("data/test_cube.stl")
    
    # Check that face indices are valid
    assert np.all(mesh_data.faces >= 0)
    assert np.all(mesh_data.faces < len(mesh_data.vertices))
    
    # Check that normals are normalized
    norms = np.linalg.norm(mesh_data.normals, axis=1)
    assert np.allclose(norms, 1.0, rtol=1e-5) 