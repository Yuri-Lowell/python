import re
import os
import sys
from pathlib import Path

def convert_csharp_to_java(input_file, output_file=None):
    """
    将C# Entity文件转换为Java Entity文件（使用Lombok）
    
    Args:
        input_file: 输入的C#文件路径
        output_file: 输出的Java文件路径（可选，默认自动生成）
    
    Returns:
        bool: 转换是否成功
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取类名
        class_match = re.search(r'public\s+class\s+(\w+)', content)
        class_name = class_match.group(1) if class_match else Path(input_file).stem
        
        # 添加package声明
        package_name = infer_package_name(input_file)
        if package_name:
            content = f"package {package_name};\n\n" + content
        
        # 移除using语句
        content = re.sub(r'^using\s+.*?;\s*$', '', content, flags=re.MULTILINE)
        
        # 移除namespace
        content = re.sub(r'namespace\s+[\w.]+\s*\{', '', content)
        
        # 移除最后的闭合大括号
        content = re.sub(r'\}\s*$', '', content)
        
        # 转换注释
        content = convert_comments(content)
        
        # 添加Lombok注解
        content = add_lombok_annotations(content)
        
        # 转换属性为字段
        content = convert_to_fields(content)
        
        # 添加必要的imports
        content = add_necessary_imports(content)
        
        # 清理多余的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = content.strip() + '\n}\n'
        
        # 确定输出文件路径
        if output_file is None:
            output_file = str(Path(input_file).with_suffix('.java'))
        
        # 确保输出目录存在
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        # 写入Java文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ 转换成功: {input_file} -> {output_file}")
        return True
        
    except Exception as e:
        print(f"✗ 转换失败 {input_file}: {str(e)}")
        return False

def infer_package_name(file_path):
    """根据文件路径推断包名"""
    path = Path(file_path)
    parts = path.parts
    try:
        if 'main' in parts and 'java' in parts:
            java_index = parts.index('java')
            package_parts = parts[java_index + 1:-1]
            return '.'.join(package_parts)
        elif 'src' in parts:
            src_index = parts.index('src')
            package_parts = parts[src_index + 1:-1]
            return '.'.join(package_parts)
    except ValueError:
        pass
    return None

def convert_comments(content):
    """转换C#注释为Java注释"""
    lines = content.split('\n')
    new_lines = []
    in_xml_comment = False
    xml_comment_lines = []
    
    for line in lines:
        # 检测XML注释开始
        if re.match(r'\s*///\s*<summary>', line):
            in_xml_comment = True
            indent = re.match(r'(\s*)', line).group(1)
            xml_comment_lines = [f'{indent}/**']
            continue
        
        # 收集XML注释内容
        if in_xml_comment:
            cleaned_line = re.sub(r'^\s*///\s*', '', line)
            
            # 检测注释结束
            if re.match(r'\s*///\s*</summary>', line):
                if xml_comment_lines and xml_comment_lines[-1] != ' */':
                    xml_comment_lines.append(' */')
                new_lines.extend(xml_comment_lines)
                xml_comment_lines = []
                in_xml_comment = False
                continue
            
            # 添加注释行
            if cleaned_line.strip():
                indent = re.match(r'(\s*)', line).group(1)
                xml_comment_lines.append(f'{indent} * {cleaned_line}')
            else:
                indent = re.match(r'(\s*)', line).group(1)
                xml_comment_lines.append(f'{indent} *')
            continue
        
        # 处理单行注释
        if re.match(r'\s*///', line):
            indent = re.match(r'(\s*)', line).group(1)
            comment = re.sub(r'^\s*///\s*', '', line)
            if comment:
                new_lines.append(f'{indent}// {comment}')
            else:
                new_lines.append(f'{indent}//')
            continue
        
        new_lines.append(line)
    
    return '\n'.join(new_lines)

def add_lombok_annotations(content):
    """添加Lombok注解"""
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        # 在类定义前添加Lombok注解
        if re.match(r'\s*public\s+class\s+\w+', line):
            indent = re.match(r'(\s*)', line).group(1)
            # 在类定义前插入@Data注解
            new_lines.append(f'{indent}@Data')
            new_lines.append(f'{indent}@Builder')
            new_lines.append(f'{indent}@NoArgsConstructor')
            new_lines.append(f'{indent}@AllArgsConstructor')
            new_lines.append(line)
        else:
            new_lines.append(line)
    
    return '\n'.join(new_lines)

def convert_to_fields(content):
    """将C#属性转换为Java字段（保留注释）"""
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 检查是否是注释行（可能属于下一个属性）
        is_comment = re.match(r'\s*/\*\*', line) or re.match(r'\s*//', line)
        
        # 检查是否是属性定义
        prop_match = re.match(r'(\s*)public\s+(\w+\??)\s+(\w+)\s*\{\s*get;\s*set;\s*\}', line)
        prop_with_default = re.match(r'(\s*)public\s+(\w+\??)\s+(\w+)\s*\{\s*get;\s*set;\s*\}\s*=\s*(.+?);?$', line)
        
        if prop_with_default:
            indent, prop_type, prop_name, default_value = prop_with_default.groups()
            prop_type = map_type(prop_type)
            field_name = prop_name[0].lower() + prop_name[1:]
            default_value = default_value.strip()
            
            # 添加字段（带默认值）
            new_lines.append(f'{indent}private {prop_type} {field_name} = {default_value};')
            
        elif prop_match:
            indent, prop_type, prop_name = prop_match.groups()
            prop_type = map_type(prop_type)
            field_name = prop_name[0].lower() + prop_name[1:]
            
            # 添加字段
            new_lines.append(f'{indent}private {prop_type} {field_name};')
            
        else:
            new_lines.append(line)
        
        i += 1
    
    return '\n'.join(new_lines)

def map_type(csharp_type):
    """映射C#类型到Java类型"""
    # 处理可空类型
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
        'byte[]': 'byte[]',
        'object': 'Object',
        'short': 'Short' if is_nullable else 'short',
        'char': 'Character' if is_nullable else 'char',
    }
    
    return type_map.get(base_type, base_type)

def add_necessary_imports(content):
    """添加必要的import语句"""
    imports = set()
    
    # Lombok imports
    imports.add('import lombok.Data;')
    imports.add('import lombok.Builder;')
    imports.add('import lombok.NoArgsConstructor;')
    imports.add('import lombok.AllArgsConstructor;')
    
    # 检查是否需要Date
    if 'java.util.Date' in content:
        imports.add('import java.util.Date;')
    
    # 检查是否需要BigDecimal
    if 'java.math.BigDecimal' in content:
        imports.add('import java.math.BigDecimal;')
    
    # 检查是否需要List/ArrayList
    if re.search(r'(List|ArrayList|IList|<[^>]*>)', content):
        imports.add('import java.util.List;')
        imports.add('import java.util.ArrayList;')
    
    # 检查是否需要Map/HashMap
    if re.search(r'(Map|HashMap|IDictionary)', content):
        imports.add('import java.util.Map;')
        imports.add('import java.util.HashMap;')
    
    # 添加Serializable（如果类实现的话）
    if 'implements Serializable' in content:
        imports.add('import java.io.Serializable;')
    
    if imports:
        # 找到package声明后的位置
        if content.startswith('package'):
            lines = content.split('\n')
            insert_pos = 1
            while insert_pos < len(lines) and not lines[insert_pos].strip():
                insert_pos += 1
            lines.insert(insert_pos, '')
            for imp in sorted(imports):
                lines.insert(insert_pos + 1, imp)
            content = '\n'.join(lines)
        else:
            content = '\n'.join(sorted(imports)) + '\n\n' + content
    
    return content

def process_path(input_path, output_path=None):
    """处理文件或目录"""
    input_path = Path(input_path)
    
    if not input_path.exists():
        print(f"错误: {input_path} 不存在")
        return False
    
    if input_path.is_file():
        # 处理单个文件
        if input_path.suffix.lower() != '.cs':
            print(f"错误: {input_path} 不是C#文件")
            return False
        
        if output_path:
            output_path = Path(output_path)
            if output_path.is_dir():
                output_path = output_path / input_path.with_suffix('.java').name
        else:
            output_path = input_path.with_suffix('.java')
        
        return convert_csharp_to_java(str(input_path), str(output_path))
    
    elif input_path.is_dir():
        # 处理目录
        cs_files = list(input_path.rglob('*.cs'))
        if not cs_files:
            print(f"警告: {input_path} 中没有找到C#文件")
            return False
        
        print(f"找到 {len(cs_files)} 个C#文件")
        success_count = 0
        
        for cs_file in cs_files:
            if output_path:
                # 保持相对目录结构
                rel_path = cs_file.relative_to(input_path)
                java_file = Path(output_path) / rel_path.with_suffix('.java')
            else:
                java_file = cs_file.with_suffix('.java')
            
            if convert_csharp_to_java(str(cs_file), str(java_file)):
                success_count += 1
        
        print(f"\n转换完成: {success_count}/{len(cs_files)} 成功")
        return success_count > 0
    
    return False

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("=" * 60)
        print("C# Entity 转 Java Entity 转换工具 (Lombok版本)")
        print("=" * 60)
        print("\n使用方法:")
        print("  单文件转换: python convert.py <input_file.cs> [output_file.java]")
        print("  目录转换:   python convert.py <input_directory> [output_directory]")
        print("\n示例:")
        print("  python convert.py UserEntity.cs")
        print("  python convert.py UserEntity.cs User.java")
        print("  python convert.py ./CSharpEntities")
        print("  python convert.py ./CSharpEntities ./JavaEntities")
        print("\n生成的Java实体将使用Lombok注解:")
        print("  @Data, @Builder, @NoArgsConstructor, @AllArgsConstructor")
        print("=" * 60)
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = process_path(input_path, output_path)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
