#!/usr/bin/env python
"""
生成高精度汽车网格并保存为NAS文件，不显示任何GUI界面
"""
from create_car_mesh import create_parametric_car, save_to_nas
import os
import argparse
import numpy as np

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='生成高精度汽车网格并保存为NAS文件')
    parser.add_argument('--output', '-o', default='data/car_highres.nas', 
                        help='输出文件路径')
    parser.add_argument('--length', '-l', type=float, default=4.5, 
                        help='车身长度（米）')
    parser.add_argument('--width', '-w', type=float, default=1.8, 
                        help='车身宽度（米）')
    parser.add_argument('--height', '-ht', type=float, default=1.5, 
                        help='车身高度（米）')
    parser.add_argument('--resolution', '-r', type=int, default=200, 
                        help='网格分辨率，越高网格越密')
    
    args = parser.parse_args()
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # 生成汽车网格
    print(f"正在生成汽车网格...")
    vertices, faces = create_parametric_car(
        length=args.length, 
        width=args.width, 
        height=args.height, 
        res=args.resolution
    )
    
    # 保存为NAS文件
    print(f"正在保存网格到 {args.output}...")
    save_to_nas(args.output, vertices, faces)
    
    # 打印网格信息
    print(f"已生成汽车网格：{args.output}")
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

if __name__ == "__main__":
    main() 