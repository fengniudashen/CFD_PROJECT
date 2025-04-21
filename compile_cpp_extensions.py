#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
编译所有C++扩展模块
这个脚本会编译所有的C++扩展模块，提高模型处理性能
"""

import os
import subprocess
import sys
import platform

def print_status(message):
    """打印带有分隔线的状态消息"""
    print("\n" + "=" * 80)
    print(message)
    print("=" * 80 + "\n")

def run_setup_script(script_name):
    """运行setup脚本编译C++扩展"""
    if not os.path.exists(script_name):
        print(f"错误: 未找到 {script_name}！")
        return False
    
    try:
        print_status(f"开始编译 {script_name}...")
        
        # 构建命令
        cmd = [sys.executable, script_name, "build_ext", "--inplace"]
        
        # 在Windows上，我们需要确保使用正确的编译器
        if platform.system() == "Windows":
            cmd.append("--compiler=msvc")
        
        # 执行编译
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # 输出编译结果
        print(result.stdout)
        if result.stderr:
            print("警告或错误:")
            print(result.stderr)
        
        print_status(f"{script_name} 编译完成!")
        return True
    
    except subprocess.CalledProcessError as e:
        print_status(f"编译 {script_name} 失败!")
        print("错误输出:")
        print(e.stdout)
        print(e.stderr)
        return False

def check_imports():
    """检查是否可以导入编译好的扩展模块"""
    modules_to_check = [
        ("self_intersection_cpp", "相邻面检测"),
        ("non_manifold_vertices_cpp", "重叠点检测"),
        ("face_quality_cpp", "面片质量检测")
    ]
    
    print_status("检查编译后的模块...")
    
    for module_name, description in modules_to_check:
        try:
            module = __import__(module_name)
            print(f"✓ {module_name} ({description}) 已成功加载!")
        except ImportError as e:
            print(f"✗ {module_name} ({description}) 加载失败: {str(e)}")

def main():
    """主函数"""
    print_status("开始编译所有C++扩展模块")
    
    # 检查必要的依赖
    try:
        import pybind11
        print("✓ 已安装 pybind11")
    except ImportError:
        print("✗ 未找到 pybind11，正在安装...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pybind11"], check=True)
            print("✓ pybind11 安装成功")
        except subprocess.CalledProcessError:
            print("✗ pybind11 安装失败，请手动安装: pip install pybind11")
            return

    # 编译各个模块
    setup_scripts = [
        "setup_self_intersection.py",
        # 添加其他扩展模块的setup脚本
    ]
    
    success_count = 0
    for script in setup_scripts:
        if run_setup_script(script):
            success_count += 1
    
    # 检查编译结果
    if success_count == len(setup_scripts):
        print_status("所有C++扩展模块编译成功!")
    else:
        print_status(f"部分模块编译成功 ({success_count}/{len(setup_scripts)})")
    
    # 检查模块导入
    check_imports()
    
    print_status("编译过程完成")
    print("提示: 如果编译成功，您现在可以启动程序并享受C++加速的性能提升！")

if __name__ == "__main__":
    main() 