#!/usr/bin/env python
"""
This script fixes all indentation issues with self.update_display() calls in mesh_viewer_qt.py.
It handles both standalone calls and those within functions, methods, and blocks.
"""

def fix_indentation():
    """Fix indentation of self.update_display() calls."""
    with open('src/mesh_viewer_qt.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    modified = False
    
    for i in range(len(lines)):
        if 'self.update_display()' in lines[i]:
            line = lines[i]
            # Get current indentation level
            current_indent = len(line) - len(line.lstrip())
            
            # Determine correct indentation based on context
            correct_indent = 8  # Default for method body
            
            # Check previous non-empty line for context
            j = i - 1
            while j >= 0:
                prev_line = lines[j].strip()
                if prev_line and not prev_line.startswith('#'):
                    # Get indentation of previous line
                    prev_indent = len(lines[j]) - len(lines[j].lstrip())
                    
                    # Check if previous line ends with ':' (indicating a block)
                    if prev_line.endswith(':'):
                        # Inside a new block, indent is prev + 4
                        correct_indent = prev_indent + 4
                    else:
                        # Same level as previous line
                        correct_indent = prev_indent
                    break
                j -= 1
            
            # If current indent is wrong, fix it
            if current_indent != correct_indent:
                lines[i] = ' ' * correct_indent + 'self.update_display()\n'
                modified = True
    
    # Only write back if changes were made
    if modified:
        with open('src/mesh_viewer_qt.py', 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    return False

if __name__ == "__main__":
    if fix_indentation():
        print("Fixed indentation issues in mesh_viewer_qt.py")
    else:
        print("No indentation issues found or fixed") 