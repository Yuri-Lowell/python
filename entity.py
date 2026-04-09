import re
import os
import sys
from pathlib import Path

def convert_csharp_to_java(input_file, output_file=None):
    """
    将C# Entity文件转换为Java Entity文件（使用Lombok @Data）
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除using语句（增强版，确保完全删除）
        content = re.sub(r'^\s*using\s+[\w\.]+\s*;\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*using\s+static\s+[\w\.]+\s*;\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*using\s+\w+\s*=\s*[\w\.]+\s*;\s*$', '', content, flags=re.MULTILINE)
        
        # 移除namespace
        content = re.sub(r'namespace\s+[\w.]+\s*\{', '', content)
        content = re.sub(r'}\s*$', '', content)
        
        # 转换注释
        content = convert_comments(content)
        
        # 添加Lombok @Data注解
        content = add_lombok_data(content)
        
        # 转换属性为字段
        content = convert_properties_to_fields(content)
        
        # 添加import语句
        content = add_imports(content)
        
        # 清理多余空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = content.strip() + '\n}\n'
        
        # 输出文件
        if output_file is None:
            output_file = str(Path(input_file).with_suffix('.java'))
        
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ 转换成功: {input_file} -> {output_file}")
        return True
        
    except Exception as e:
        print(f"✗ 转换失败 {input_file}: {str(e)}")
        return False

def convert_comments(content):
    """转换C# XML注释为Java注释"""
    lines = content.split('\n')
    result = []
    in_summary = False
    indent = ""
    summary_lines = []
    
    for line in lines:
        # 匹配 <summary>
        if re.search(r'///\s*<summary>', line):
            in_summary = True
            indent = re.match(r'(\s*)', line).group(1)
            summary_lines = [f'{indent}/**']
            continue
        
        # 匹配 </summary>
        if in_summary and re.search(r'///\s*</summary>', line):
            if summary_lines and summary_lines[-1] != ' */':
                summary_lines.append(f'{indent} */')
            result.extend(summary_lines)
            in_summary = False
            continue
        
        # 收集summary内容
        if in_summary:
            comment_text = re.sub(r'^\s*///\s*', '', line)
            if comment_text.strip():
                summary_lines.append(f'{indent} * {comment_text}')
            else:
                summary_lines.append(f'{indent} *')
            continue
        
        # 处理普通注释
        if re.match(r'\s*///', line):
            indent = re.match(r'(\s*)', line).group(1)
            comment = re.sub(r'^\s*///\s*', '', line)
            if comment:
                result.append(f'{indent}// {comment}')
            else:
                result.append(f'{indent}//')
            continue
        
        result.append(line)
    
    return '\n'.join(result)

def add_lombok_data(content):
    """只添加@Data注解"""
    lines = content.split('\n')
    result = []
    
    for i, line in enumerate(lines):
        if re.match(r'\s*public\s+class\s+\w+', line):
            indent = re.match(r'(\s*)', line).group(1)
            result.append(f'{indent}@Data')
            result.append(line)
        else:
            result.append(line)
    
    return '\n'.join(result)

def convert_properties_to_fields(content):
    """将C#属性转换为Java字段"""
    lines = content.split('\n')
    result = []
    
    for line in lines:
        # 匹配简单属性: public string Name { get; set; }
        match = re.match(r'(\s*)public\s+(\w+\??)\s+(\w+)\s*\{\s*get;\s*set;\s*\}', line)
        
        if match:
            indent, prop_type, prop_name = match.groups()
            java_type = map_type(prop_type)
            field_name = prop_name[0].lower() + prop_name[1:]
            result.append(f'{indent}private {java_type} {field_name};')
        else:
            result.append(line)
    
    return '\n'.join(result)

def map_type(csharp_type):
    """C#类型转Java类型"""
    is_nullable = csharp_type.endswith('?')
    base_type = csharp_type[:-1] if is_nullable else csharp_type
    
    type_map = {
        'string': 'String',
        'int': 'Integer' if is_nullable else 'int',
        'long': 'Long' if is_nullable else 'long',
        'double': 'Double' if is_nullable else 'double',
        'float': 'Float' if is_nullable else 'float',
        'bool': 'Boolean' if is_nullable else 'boolean',
        'DateTime': 'java.util.Date',
        'decimal': 'java.math.BigDecimal',
        'Guid': 'String',
        'object': 'Object',
    }
    
    return type_map.get(base_type, base_type)

def add_imports(content):
    """添加必要的import语句"""
    imports = ['import lombok.Data;']
    
    if 'java.util.Date' in content:
        imports.append('import java.util.Date;')
    if 'java.math.BigDecimal' in content:
        imports.append('import java.math.BigDecimal;')
    
    # 找到插入位置（package之后，class之前）
    lines = content.split('\n')
    insert_pos = 0
    
    # 跳过package行
    if lines and lines[0].startswith('package'):
        insert_pos = 1
        while insert_pos < len(lines) and not lines[insert_pos].strip():
            insert_pos += 1
    
    # 插入imports
    for imp in reversed(imports):
        lines.insert(insert_pos, imp)
    lines.insert(insert_pos, '')
    
    return '\n'.join(lines)

def process_path(input_path, output_path=None):
    """处理文件或文件夹"""
    input_path = Path(input_path)
    
    if not input_path.exists():
        print(f"错误: {input_path} 不存在")
        return False
    
    if input_path.is_file():
        if input_path.suffix.lower() != '.cs':
            print(f"错误: {input_path} 不是C#文件")
            return False
        
        out = Path(output_path) if output_path else input_path.with_suffix('.java')
        if output_path and Path(output_path).is_dir():
            out = Path(output_path) / input_path.with_suffix('.java').name
        
        return convert_csharp_to_java(str(input_path), str(out))
    
    elif input_path.is_dir():
        cs_files = list(input_path.rglob('*.cs'))
        if not cs_files:
            print(f"警告: 未找到C#文件")
            return False
        
        print(f"找到 {len(cs_files)} 个C#文件")
        success = 0
        
        for cs_file in cs_files:
            if output_path:
                rel = cs_file.relative_to(input_path)
                java_file = Path(output_path) / rel.with_suffix('.java')
            else:
                java_file = cs_file.with_suffix('.java')
            
            if convert_csharp_to_java(str(cs_file), str(java_file)):
                success += 1
        
        print(f"\n完成: {success}/{len(cs_files)} 成功")
        return success > 0
    
    return False

def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("C# Entity → Java Entity (Lombok @Data)")
        print("=" * 60)
        print("\n用法:")
        print("  单文件: python convert.py User.cs")
        print("  单文件: python convert.py User.cs User.java")
        print("  文件夹: python convert.py ./CSharpEntities")
        print("  文件夹: python convert.py ./CSharpEntities ./JavaEntities")
        print("=" * 60)
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = process_path(input_path, output_path)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
