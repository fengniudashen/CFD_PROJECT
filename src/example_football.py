from create_football_mesh import create_football_mesh, save_to_stl
from mesh_viewer_qt import MeshViewerQt
from PyQt5.QtWidgets import QApplication
import sys

# 生成足球网格
vertices, faces, normals = create_football_mesh(radius=100.0, subdivisions=3)

# 保存为STL文件
output_file = 'data/football.stl'
save_to_stl(output_file, vertices, faces, normals)

# 打印网格信息
print(f'已生成足球网格：{output_file}')
print(f'网格信息：')
print(f'- 顶点数量：{len(vertices)}')
print(f'- 面片数量：{len(faces)}')

# 验证网格数据
print('\n网格数据验证:')
print('顶点坐标范围:')
print(f'X: [{vertices[:, 0].min():.2f}, {vertices[:, 0].max():.2f}]')
print(f'Y: [{vertices[:, 1].min():.2f}, {vertices[:, 1].max():.2f}]')
print(f'Z: [{vertices[:, 2].min():.2f}, {vertices[:, 2].max():.2f}]')

# 显示网格
app = QApplication(sys.argv)
viewer = MeshViewerQt({
    'vertices': vertices,
    'faces': faces,
    'normals': normals
})
viewer.show()
sys.exit(app.exec_())