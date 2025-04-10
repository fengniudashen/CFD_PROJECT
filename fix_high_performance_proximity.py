#!/usr/bin/env python
"""
This script will identify and fix indentation issues in high_performance_proximity.py
"""

def fix_indentation_errors():
    """Fix indentation errors in high_performance_proximity.py."""
    try:
        # Read the entire file
        with open('src/high_performance_proximity.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Fix specific known issues
        for i in range(len(lines)):
            if "if num_processes is None:" in lines[i] and not lines[i].startswith(" " * 8):
                # Fix the indentation of the if statement
                current_indent = len(lines[i]) - len(lines[i].lstrip())
                lines[i] = " " * 8 + lines[i].lstrip()
                
                # Check next line to ensure it's properly indented
                if i + 1 < len(lines) and "num_processes = max" in lines[i + 1]:
                    lines[i + 1] = " " * 12 + lines[i + 1].lstrip()
        
        # Write the corrected file back
        with open('src/high_performance_proximity.py', 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print("Fixed indentation issues in high_performance_proximity.py")
        return True
    except Exception as e:
        print(f"Error fixing high_performance_proximity.py: {e}")
        return False

if __name__ == "__main__":
    fix_indentation_errors() 