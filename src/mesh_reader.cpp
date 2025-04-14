#include "mesh_reader.hpp"
#include <fstream>
#include <sstream>
#include <unordered_map>
#include <stdexcept>
#include <algorithm>
#include <cctype>

namespace cfd {

bool STLReader::is_binary(const std::vector<char>& header) {
    return std::any_of(header.begin(), header.end(),
                      [](char c) { return !std::isprint(c) && !std::isspace(c); });
}

MeshData STLReader::read_binary(const std::string& file_path) {
    std::ifstream file(file_path, std::ios::binary);
    if (!file) {
        throw std::runtime_error("Cannot open file: " + file_path);
    }

    // Skip header
    file.seekg(80);

    // Read number of triangles
    uint32_t triangle_count;
    file.read(reinterpret_cast<char*>(&triangle_count), sizeof(uint32_t));

    // Pre-allocate matrices
    Eigen::MatrixXf vertices(triangle_count * 3, 3);
    Eigen::MatrixXi faces(triangle_count, 3);
    Eigen::MatrixXf normals(triangle_count, 3);

    // Read triangles
    for (uint32_t i = 0; i < triangle_count; ++i) {
        float normal[3];
        float v1[3], v2[3], v3[3];
        uint16_t attribute_byte_count;

        // Read normal
        file.read(reinterpret_cast<char*>(normal), sizeof(float) * 3);
        normals.row(i) << normal[0], normal[1], normal[2];

        // Read vertices
        file.read(reinterpret_cast<char*>(v1), sizeof(float) * 3);
        file.read(reinterpret_cast<char*>(v2), sizeof(float) * 3);
        file.read(reinterpret_cast<char*>(v3), sizeof(float) * 3);

        // Store vertices
        int base_idx = i * 3;
        vertices.row(base_idx) << v1[0], v1[1], v1[2];
        vertices.row(base_idx + 1) << v2[0], v2[1], v2[2];
        vertices.row(base_idx + 2) << v3[0], v3[1], v3[2];

        // Store face indices
        faces.row(i) << base_idx, base_idx + 1, base_idx + 2;

        // Skip attribute byte count
        file.read(reinterpret_cast<char*>(&attribute_byte_count), sizeof(uint16_t));
    }

    return MeshData{vertices, faces, normals};
}

MeshData STLReader::read_ascii(const std::string& file_path) {
    std::ifstream file(file_path);
    if (!file) {
        throw std::runtime_error("Cannot open file: " + file_path);
    }

    std::vector<Eigen::Vector3f> vertices_vec;
    std::vector<Eigen::Vector3i> faces_vec;
    std::vector<Eigen::Vector3f> normals_vec;

    std::string line;
    while (std::getline(file, line)) {
        std::istringstream iss(line);
        std::string token;
        iss >> token;

        if (token == "facet" && iss >> token && token == "normal") {
            Eigen::Vector3f normal;
            iss >> normal.x() >> normal.y() >> normal.z();
            normals_vec.push_back(normal);

            // Skip "outer loop"
            std::getline(file, line);

            // Read three vertices
            Eigen::Vector3i face;
            for (int i = 0; i < 3; ++i) {
                std::getline(file, line);
                iss.clear();
                iss.str(line);
                iss >> token; // Skip "vertex"
                
                Eigen::Vector3f vertex;
                iss >> vertex.x() >> vertex.y() >> vertex.z();
                vertices_vec.push_back(vertex);
                face[i] = vertices_vec.size() - 1;
            }
            faces_vec.push_back(face);

            // Skip "endloop" and "endfacet"
            std::getline(file, line);
            std::getline(file, line);
        }
    }

    // Convert vectors to matrices
    Eigen::MatrixXf vertices(vertices_vec.size(), 3);
    Eigen::MatrixXi faces(faces_vec.size(), 3);
    Eigen::MatrixXf normals(normals_vec.size(), 3);

    for (size_t i = 0; i < vertices_vec.size(); ++i) {
        vertices.row(i) = vertices_vec[i];
    }
    for (size_t i = 0; i < faces_vec.size(); ++i) {
        faces.row(i) = faces_vec[i];
    }
    for (size_t i = 0; i < normals_vec.size(); ++i) {
        normals.row(i) = normals_vec[i];
    }

    return MeshData{vertices, faces, normals};
}

MeshData STLReader::read(const std::string& file_path) {
    std::ifstream file(file_path, std::ios::binary);
    if (!file) {
        throw std::runtime_error("Cannot open file: " + file_path);
    }

    std::vector<char> header(80);
    file.read(header.data(), 80);

    file.close();

    if (is_binary(header)) {
        return read_binary(file_path);
    } else {
        return read_ascii(file_path);
    }
}

MeshData NASReader::read(const std::string& file_path) {
    size_t vertex_count = 0;
    size_t face_count = 0;

    // --- First Pass: Count vertices and faces ---
    {
        std::ifstream counter_file(file_path);
        if (!counter_file) {
            throw std::runtime_error("Cannot open file for counting: " + file_path);
        }
        std::string line;
        while (std::getline(counter_file, line)) {
            if (line.rfind("GRID*", 0) == 0) { // Check prefix efficiently
                vertex_count++;
                // Skip the next line for GRID*
                std::getline(counter_file, line);
            } else if (line.rfind("CTRIA3", 0) == 0) {
                face_count++;
            }
            // Add counting for other supported types if necessary
        }
    }

    if (vertex_count == 0) {
         return MeshData{Eigen::MatrixXf(), Eigen::MatrixXi(), Eigen::MatrixXf()};
    }

    // --- Pre-allocate Eigen Matrices ---
    Eigen::MatrixXf vertices(vertex_count, 3);
    Eigen::MatrixXi faces(face_count, 3);
    std::unordered_map<int, int> node_map;
    node_map.reserve(vertex_count);
    size_t current_vertex_index = 0;
    size_t current_face_index = 0;


    // --- Second Pass: Read data and fill matrices ---
    std::ifstream file(file_path);
    if (!file) {
        throw std::runtime_error("Cannot open file for reading: " + file_path);
    }

    std::string line;
    int line_num = 0;
    while (std::getline(file, line)) {
        line_num++;
        std::istringstream iss(line);
        std::string token;
        iss >> token;

        if (token == "GRID*") {
            int node_id;
            float x, y;
            iss >> node_id >> token >> x >> y;

            if (!std::getline(file, line)) break;
            line_num++;
            iss.clear();
            iss.str(line);
            float z;
            iss >> token >> z;

            if (current_vertex_index < vertex_count) {
                node_map[node_id] = current_vertex_index;
                vertices.row(current_vertex_index) << x, y, z;
                current_vertex_index++;
            }
        }
        else if (token == "CTRIA3") {
            int elem_id;
            int v1, v2, v3;
            iss >> elem_id >> token >> v1 >> v2 >> v3;

            if (current_face_index < face_count) {
                try {
                     faces.row(current_face_index) << node_map.at(v1), node_map.at(v2), node_map.at(v3);
                     current_face_index++;
                } catch (const std::out_of_range& oor) {
                     // Node ID referenced before it was defined - skip face
                     // Optionally add logging here
                }
            }
        }
    }

     if (current_face_index < face_count) {
         faces.conservativeResize(current_face_index, 3);
     }


    return MeshData{vertices, faces, Eigen::MatrixXf()};
}

std::unique_ptr<MeshReader> create_mesh_reader(const std::string& file_path) {
    std::string ext = file_path.substr(file_path.find_last_of(".") + 1);
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);

    if (ext == "nas") {
        return std::make_unique<NASReader>();
    }
    else if (ext == "stl") {
        return std::make_unique<STLReader>();
    }
    else {
        throw std::runtime_error("Unsupported file format: " + ext);
    }
}

MeshData read_nas_file(const std::string& file_path) {
    NASReader reader;
    return reader.read(file_path);
}

} // namespace cfd 