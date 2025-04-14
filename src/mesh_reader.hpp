#ifndef MESH_READER_HPP
#define MESH_READER_HPP

#include <string>
#include <vector>
#include <memory>
#include <Eigen/Dense>

namespace cfd {

struct MeshData {
    Eigen::MatrixXf vertices;  // Nx3 matrix for vertices
    Eigen::MatrixXi faces;     // Mx3 matrix for faces
    Eigen::MatrixXf normals;   // Mx3 matrix for face normals
};

class MeshReader {
public:
    virtual ~MeshReader() = default;
    virtual MeshData read(const std::string& file_path) = 0;
};

class STLReader : public MeshReader {
public:
    MeshData read(const std::string& file_path) override;

private:
    bool is_binary(const std::vector<char>& header);
    MeshData read_binary(const std::string& file_path);
    MeshData read_ascii(const std::string& file_path);
};

class NASReader : public MeshReader {
public:
    MeshData read(const std::string& file_path) override;
};

std::unique_ptr<MeshReader> create_mesh_reader(const std::string& file_path);
MeshData read_nas_file(const std::string& file_path);

} // namespace cfd

#endif // MESH_READER_HPP 