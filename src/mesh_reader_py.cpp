#include <pybind11/pybind11.h>
#include <pybind11/eigen.h>
#include <pybind11/stl.h>
#include "mesh_reader.hpp"

namespace py = pybind11;

PYBIND11_MODULE(mesh_reader_cpp, m) {
    m.doc() = "C++ implementation of mesh reader for improved performance";

    py::class_<cfd::MeshData>(m, "MeshData")
        .def(py::init<>())
        .def_readwrite("vertices", &cfd::MeshData::vertices)
        .def_readwrite("faces", &cfd::MeshData::faces)
        .def_readwrite("normals", &cfd::MeshData::normals);

    py::class_<cfd::MeshReader, std::unique_ptr<cfd::MeshReader>>(m, "MeshReader")
        .def("read", &cfd::MeshReader::read);

    py::class_<cfd::STLReader, cfd::MeshReader>(m, "STLReader")
        .def(py::init<>());

    py::class_<cfd::NASReader, cfd::MeshReader>(m, "NASReader")
        .def(py::init<>());

    m.def("create_mesh_reader", &cfd::create_mesh_reader,
          "Create appropriate mesh reader based on file extension");
    
    m.def("read_nas_file", &cfd::read_nas_file,
          "Convenience function to read NAS files");
} 