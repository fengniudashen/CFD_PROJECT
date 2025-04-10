#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
这个脚本用于修复mesh_viewer_qt.py中的缩进错误
"""

import re

def fix_mesh_viewer_qt_indentation():
    # 读取mesh_viewer_qt.py文件
    with open('src/mesh_viewer_qt.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复analyze_face_quality方法中的缩进错误
    # 寻找有问题的行，并添加正确的缩进
    pattern1 = r"([ \t]+if progress\.wasCanceled\(\):\s*\n)[ \t]*return False"
    replacement1 = r"\1\1    return False"
    
    # 修复 QMessageBox.information(self, '面片质量分析', quality_info) 前的缩进
    pattern2 = r"([ \t]+quality_info = generate_quality_report\(results\['stats'\]\)\s*\n)[ \t]*QMessageBox\.information"
    replacement2 = r"\1            QMessageBox.information"
    
    # 应用修复
    fixed_content = re.sub(pattern1, replacement1, content)
    fixed_content = re.sub(pattern2, replacement2, fixed_content)
    
    # 写回到文件
    with open('src/mesh_viewer_qt.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("缩进修复完成")

if __name__ == "__main__":
    fix_mesh_viewer_qt_indentation() 