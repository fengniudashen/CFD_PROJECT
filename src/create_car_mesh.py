import numpy as np
import os
from typing import Tuple, List

def create_parametric_car(length: float = 4.5, width: float = 1.8, 
                         height: float = 1.5, res: int = 100) -> Tuple[np.ndarray, np.ndarray]:
    """
    创建参数化的汽车模型
    
    Args:
        length: 车身长度（米）
        width: 车身宽度（米）
        height: 车身高度（米）
        res: 分辨率（越高，网格越密）
    
    Returns:
        vertices: 顶点坐标数组
        faces: 面片索引数组
    """
    # 提高分辨率，确保网格超过10万个面
    x_res = res
    y_res = max(res // 2, 20)
    z_res = max(res // 3, 15)
    
    # 创建顶点和面的列表
    vertices = []
    faces = []
    vertex_index = 0
    
    # 1. 车身主体（类似于长方体，但有弧度）
    body_length = length * 0.8
    body_width = width
    body_height = height * 0.6
    
    # 车身的参数方程
    def body_profile(u, v):
        # u从前到后，v从左到右
        x = (u - 0.5) * body_length
        # 在x方向上对y值进行调整，使中间更宽
        y_scale = 1.0 - 0.2 * abs((u - 0.5) * 2)**2
        y = (v - 0.5) * body_width * y_scale
        # 车顶的弧度
        z_scale = 1.0 - 0.5 * (abs(v - 0.5) * 2)**1.5
        z = body_height * 0.5 * z_scale
        return x, y, z
    
    # 生成车身的网格
    body_vertices_start = vertex_index
    for i in range(x_res + 1):
        for j in range(y_res + 1):
            u = i / x_res
            v = j / y_res
            x, y, z = body_profile(u, v)
            vertices.append([x, y, z])
            vertex_index += 1
    
    # 添加车身的面
    for i in range(x_res):
        for j in range(y_res):
            v1 = body_vertices_start + i * (y_res + 1) + j
            v2 = body_vertices_start + i * (y_res + 1) + (j + 1)
            v3 = body_vertices_start + (i + 1) * (y_res + 1) + (j + 1)
            v4 = body_vertices_start + (i + 1) * (y_res + 1) + j
            # 添加两个三角形组成一个四边形
            faces.append([v1, v2, v3])
            faces.append([v1, v3, v4])
    
    # 2. 车底部
    bottom_vertices_start = vertex_index
    bottom_height = -body_height * 0.2
    for i in range(x_res + 1):
        for j in range(y_res + 1):
            u = i / x_res
            v = j / y_res
            x = (u - 0.5) * body_length
            y_scale = 1.0 - 0.2 * abs((u - 0.5) * 2)**2
            y = (v - 0.5) * body_width * y_scale
            z = bottom_height
            vertices.append([x, y, z])
            vertex_index += 1
    
    # 添加车底部的面
    for i in range(x_res):
        for j in range(y_res):
            v1 = bottom_vertices_start + i * (y_res + 1) + j
            v2 = bottom_vertices_start + i * (y_res + 1) + (j + 1)
            v3 = bottom_vertices_start + (i + 1) * (y_res + 1) + (j + 1)
            v4 = bottom_vertices_start + (i + 1) * (y_res + 1) + j
            # 添加两个三角形，注意这里的顶点顺序与车身相反
            faces.append([v1, v3, v2])
            faces.append([v1, v4, v3])
    
    # 3. 侧面连接
    for i in range(x_res):
        # 前面
        v1 = body_vertices_start + i * (y_res + 1)
        v2 = body_vertices_start + (i + 1) * (y_res + 1)
        v3 = bottom_vertices_start + (i + 1) * (y_res + 1)
        v4 = bottom_vertices_start + i * (y_res + 1)
        faces.append([v1, v2, v3])
        faces.append([v1, v3, v4])
        
        # 后面
        v1 = body_vertices_start + i * (y_res + 1) + y_res
        v2 = body_vertices_start + (i + 1) * (y_res + 1) + y_res
        v3 = bottom_vertices_start + (i + 1) * (y_res + 1) + y_res
        v4 = bottom_vertices_start + i * (y_res + 1) + y_res
        faces.append([v1, v3, v2])
        faces.append([v1, v4, v3])
    
    # 4. 前后连接
    for j in range(y_res):
        # 前面
        v1 = body_vertices_start + j
        v2 = body_vertices_start + (j + 1)
        v3 = bottom_vertices_start + (j + 1)
        v4 = bottom_vertices_start + j
        faces.append([v1, v3, v2])
        faces.append([v1, v4, v3])
        
        # 后面
        v1 = body_vertices_start + x_res * (y_res + 1) + j
        v2 = body_vertices_start + x_res * (y_res + 1) + (j + 1)
        v3 = bottom_vertices_start + x_res * (y_res + 1) + (j + 1)
        v4 = bottom_vertices_start + x_res * (y_res + 1) + j
        faces.append([v1, v2, v3])
        faces.append([v1, v3, v4])
    
    # 5. 轮子（简化为圆柱体）
    wheel_radius = height * 0.2
    wheel_width = width * 0.1
    wheel_centers = [
        [-length * 0.35, width * 0.5 + wheel_width * 0.5, wheel_radius],  # 左前轮
        [-length * 0.35, -width * 0.5 - wheel_width * 0.5, wheel_radius],  # 右前轮
        [length * 0.35, width * 0.5 + wheel_width * 0.5, wheel_radius],   # 左后轮
        [length * 0.35, -width * 0.5 - wheel_width * 0.5, wheel_radius]   # 右后轮
    ]
    
    wheel_segments = 32  # 轮子的分段数
    
    for wheel_center in wheel_centers:
        wheel_vertices_start = vertex_index
        cx, cy, cz = wheel_center
        
        # 创建轮子的两个圆面
        for side in [-1, 1]:
            for segment in range(wheel_segments):
                angle = 2 * np.pi * segment / wheel_segments
                x = cx
                y = cy + side * wheel_width * 0.5
                z = cz + wheel_radius * np.sin(angle)
                vertices.append([x, y, z])
                vertex_index += 1
        
        # 添加轮子的面
        for segment in range(wheel_segments):
            next_segment = (segment + 1) % wheel_segments
            v1 = wheel_vertices_start + segment
            v2 = wheel_vertices_start + next_segment
            v3 = wheel_vertices_start + wheel_segments + next_segment
            v4 = wheel_vertices_start + wheel_segments + segment
            faces.append([v1, v2, v3])
            faces.append([v1, v3, v4])
    
    # 6. 前挡风玻璃
    windshield_vertices_start = vertex_index
    for j in range(y_res + 1):
        for i in range(z_res + 1):
            v = j / y_res
            w = i / z_res
            x = -length * 0.1 + w * length * 0.2
            y_scale = 1.0 - 0.2 * abs((w - 0.5) * 2)**2
            y = (v - 0.5) * body_width * y_scale
            z = body_height * 0.5 + w * body_height * 0.3
            vertices.append([x, y, z])
            vertex_index += 1
    
    # 添加前挡风玻璃的面
    for j in range(y_res):
        for i in range(z_res):
            v1 = windshield_vertices_start + j * (z_res + 1) + i
            v2 = windshield_vertices_start + j * (z_res + 1) + (i + 1)
            v3 = windshield_vertices_start + (j + 1) * (z_res + 1) + (i + 1)
            v4 = windshield_vertices_start + (j + 1) * (z_res + 1) + i
            faces.append([v1, v2, v3])
            faces.append([v1, v3, v4])
    
    # 7. 后挡风玻璃
    rear_windshield_vertices_start = vertex_index
    for j in range(y_res + 1):
        for i in range(z_res + 1):
            v = j / y_res
            w = i / z_res
            x = length * 0.1 - w * length * 0.2
            y_scale = 1.0 - 0.2 * abs((w - 0.5) * 2)**2
            y = (v - 0.5) * body_width * y_scale
            z = body_height * 0.5 + (1-w) * body_height * 0.3
            vertices.append([x, y, z])
            vertex_index += 1
    
    # 添加后挡风玻璃的面
    for j in range(y_res):
        for i in range(z_res):
            v1 = rear_windshield_vertices_start + j * (z_res + 1) + i
            v2 = rear_windshield_vertices_start + j * (z_res + 1) + (i + 1)
            v3 = rear_windshield_vertices_start + (j + 1) * (z_res + 1) + (i + 1)
            v4 = rear_windshield_vertices_start + (j + 1) * (z_res + 1) + i
            faces.append([v1, v3, v2])
            faces.append([v1, v4, v3])
            
    return np.array(vertices), np.array(faces)

def save_to_nas(filename: str, vertices: np.ndarray, faces: np.ndarray):
    """将网格保存为NAS文件
    
    Args:
        filename: 输出文件名
        vertices: 顶点坐标数组，形状为(n, 3)
        faces: 面片索引数组，形状为(m, 3)
    """
    # 创建输出目录
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        # 写入头部
        f.write("$ Generated car mesh with high element count\n")
        f.write(f"$ Vertices: {len(vertices)}, Faces: {len(faces)}\n")
        
        # 写入顶点
        for i, (x, y, z) in enumerate(vertices, 1):
            f.write(f"GRID*    {i:8d}        0{x:16.8f}{y:16.8f}\n")
            f.write(f"*       {z:16.8f}\n")
        
        # 写入面
        for i, (v1, v2, v3) in enumerate(faces, 1):
            # NAS文件索引从1开始，所以要加1
            f.write(f"CTRIA3   {i:8d}       1{v1+1:8d}{v2+1:8d}{v3+1:8d}\n")
        
        # 写入材料和属性
        f.write("MAT1     1      2.1+5           0.3\n")
        f.write("PSHELL   1       1      1.\n")
        f.write("ENDDATA\n")

if __name__ == "__main__":
    # 确保输出目录存在
    os.makedirs("data", exist_ok=True)
    
    # 生成汽车网格，使用较高的分辨率确保有超过10万个面
    output_file = "data/car_highres.nas"
    vertices, faces = create_parametric_car(length=4.5, width=1.8, height=1.5, res=150)
    
    # 保存为NAS文件
    save_to_nas(output_file, vertices, faces)
    
    # 打印网格信息
    print(f"已生成汽车网格：{output_file}")
    print(f"网格信息：")
    print(f"- 顶点数量：{len(vertices)}")
    print(f"- 面片数量：{len(faces)}")
    
    # 验证网格是否达到要求的面数
    if len(faces) >= 100000:
        print(f"✓ 网格面数满足要求：{len(faces)} >= 100,000")
    else:
        print(f"✗ 网格面数不足：{len(faces)} < 100,000，请增加分辨率参数") 