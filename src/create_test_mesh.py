import numpy as np
from icosphere import icosphere
import os

def create_football_mesh(filename, refinement_level=4):
    """
    创建足球样式的网格并保存为NAS文件
    refinement_level: 细分级别，4级大约会生成10242个面
    """
    # 生成球面网格
    vertices, faces = icosphere(refinement_level)
    
    # 调整半径为1
    vertices *= 100.0  # 放大到合适的尺寸
    
    # 写入NAS文件
    with open(filename, 'w') as f:
        # 写入头部
        f.write("$ Generated football-style mesh\n")
        f.write("$ Vertices: {}, Faces: {}\n".format(len(vertices), len(faces)))
        f.write("GRID     1\n")
        
        # 写入顶点
        for i, (x, y, z) in enumerate(vertices, 1):
            f.write(f"GRID*    {i:8d}        0{x:16.8f}{y:16.8f}\n")
            f.write(f"*       {z:16.8f}\n")
        
        # 写入面
        for i, (v1, v2, v3) in enumerate(faces + 1, 1):  # +1 因为NAS文件索引从1开始
            f.write(f"CTRIA3   {i:8d}       1{v1:8d}{v2:8d}{v3:8d}\n")
        
        # 写入材料和属性
        f.write("MAT1     1      2.1+5           0.3\n")
        f.write("PSHELL   1       1      1.\n")
        f.write("ENDDATA\n")

if __name__ == "__main__":
    output_file = "tests/football_mesh.nas"
    os.makedirs("tests", exist_ok=True)
    create_football_mesh(output_file)
    print(f"已生成网格文件: {output_file}") 