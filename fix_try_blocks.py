#!/usr/bin/env python
"""
This script fixes the try-except blocks with misplaced self.update_display() calls
in mesh_viewer_qt.py.
"""

def find_try_blocks(lines):
    """Find try blocks and their indentation levels."""
    try_blocks = []
    current_try = None
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == 'try:':
            indent = len(line) - len(line.lstrip())
            current_try = {'start': i, 'indent': indent, 'except_lines': []}
            try_blocks.append(current_try)
        elif stripped.startswith('except') and current_try is not None:
            current_try['except_lines'].append(i)
        elif stripped == 'finally:' and current_try is not None:
            current_try['finally'] = i
    
    return try_blocks

def fix_misplaced_update_display(lines):
    """Fix misplaced self.update_display() calls in try blocks."""
    try_blocks = find_try_blocks(lines)
    
    for block in try_blocks:
        # Determine the range of the try block
        start_line = block['start']
        end_line = block.get('finally', -1)
        if end_line == -1:
            # If no finally block, use the last except block
            if block['except_lines']:
                end_line = block['except_lines'][-1]
            else:
                # Skip if we can't determine the end of the try block
                continue
        
        # Check for misplaced self.update_display() calls
        for i in range(start_line, end_line):
            if 'self.update_display()' in lines[i]:
                indent_level = len(lines[i]) - len(lines[i].lstrip())
                expected_indent = block['indent'] + 4  # Expected indentation inside try block
                
                if indent_level != expected_indent:
                    # Fix the indentation
                    lines[i] = ' ' * expected_indent + 'self.update_display()\n'
    
    return lines

def fix_file():
    """Read file, fix issues, and write back."""
    with open('src/mesh_viewer_qt.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix misplaced self.update_display() calls in try blocks
    lines = fix_misplaced_update_display(lines)
    
    # Write the fixed content back
    with open('src/mesh_viewer_qt.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)

if __name__ == "__main__":
    fix_file()
    print("Fixed try-except blocks in mesh_viewer_qt.py") 