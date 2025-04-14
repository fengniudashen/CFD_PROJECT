from create_car_mesh import create_parametric_car, save_to_nas
from mesh_viewer_qt import MeshViewerQt
from PyQt5.QtWidgets import QApplication
import sys
import os

# 确保输出目录存在
os.makedirs("data", exist_ok=True)

# 生成汽车网格，使用较高的分辨率确保有超过10万个面
# 将分辨率提高到200以确保超过10万个面
output_file = "data/car_highres.nas"
vertices, faces = create_parametric_car(length=4.5, width=1.8, height=1.5, res=200)

# 保存为NAS文件
save_to_nas(output_file, vertices, faces)

# 打印网格信息
print(f"已生成汽车网格：{output_file}")
print(f"网格信息：")
print(f"- 顶点数量：{len(vertices)}")
print(f"- 面片数量：{len(faces)}")

# 验证网格数据
print('\n网格数据验证:')
print('顶点坐标范围:')
print(f'X: [{vertices[:, 0].min():.2f}, {vertices[:, 0].max():.2f}]')
print(f'Y: [{vertices[:, 1].min():.2f}, {vertices[:, 1].max():.2f}]')
print(f'Z: [{vertices[:, 2].min():.2f}, {vertices[:, 2].max():.2f}]')

# 验证网格是否达到要求的面数
if len(faces) >= 100000:
    print(f"✓ 网格面数满足要求：{len(faces)} >= 100,000")
else:
    print(f"✗ 网格面数不足：{len(faces)} < 100,000，请增加分辨率参数")

# 计算顶点法向量（简化计算，使用面法向量的平均值）
import numpy as np
normals = np.zeros_like(vertices)
face_normals = np.zeros((len(faces), 3))

# 计算每个面的法向量
for i, face in enumerate(faces):
    v1, v2, v3 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
    # 计算面的法向量
    normal = np.cross(v2 - v1, v3 - v1)
    norm = np.linalg.norm(normal)
    if norm > 0:
        face_normals[i] = normal / norm
    else:
        face_normals[i] = np.array([0, 0, 1])  # 默认值

# 将面法向量分配给顶点
for i, face in enumerate(faces):
    for vertex_idx in face:
        normals[vertex_idx] += face_normals[i]

# 归一化顶点法向量
for i in range(len(normals)):
    norm = np.linalg.norm(normals[i])
    if norm > 0:
        normals[i] /= norm
    else:
        normals[i] = np.array([0, 0, 1])  # 默认值

# 显示网格
app = QApplication(sys.argv)
viewer = MeshViewerQt({
    'vertices': vertices,
    'faces': faces,
    'normals': normals
})
viewer.show()
sys.exit(app.exec_()) 