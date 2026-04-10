import re
import os
import glob

def convert_csharp_to_java(csharp_code, class_name):
    """
    将C#代码转换为Java代码
    
    Args:
        csharp_code: C#代码字符串
        class_name: 类名
    
    Returns:
        Java代码字符串
    """
    java_code = csharp_code
    
    # 1. 删除using语句
    java_code = re.sub(r'^using\s+[\w\.]+\s*;\s*\n', '', java_code, flags=re.MULTILINE)
    
    # 2. 删除namespace声明和对应的花括号
    # 匹配 namespace xxx { ... }
    java_code = re.sub(r'namespace\s+[\w\.]+\s*\{(.*?)(?=^[^\s])', '', java_code, flags=re.DOTALL | re.MULTILINE)
    # 删除可能遗留的单独花括号
    java_code = re.sub(r'^\{\s*\n', '', java_code, flags=re.MULTILINE)
    java_code = re.sub(r'\}\s*$', '', java_code, flags=re.MULTILINE)
    
    # 3. 转换注释
    # 3.1 将C#的/// XML注释转换为Java的/** */注释
    def convert_xml_comment(match):
        comment_content = match.group(1)
        # 去除开头的///和空格
        lines = comment_content.split('\n')
        converted_lines = ['/**']
        for line in lines:
            # 去除///前缀和空格
            cleaned = re.sub(r'^\s*///\s?', '', line)
            if cleaned.strip():
                converted_lines.append(f' * {cleaned}')
            else:
                converted_lines.append(' *')
        converted_lines.append(' */')
        return '\n'.join(converted_lines)
    
    java_code = re.sub(r'///\s?(.*?)(?=\n[^/]|\n\n)', convert_xml_comment, java_code, flags=re.DOTALL)
    
    # 3.2 将C#的单行注释 // 转换为Java的 //
    # 但保留已经转换的XML注释
    lines = java_code.split('\n')
    for i, line in enumerate(lines):
        if '///' in line:
            continue
        # 转换普通注释
        if '//' in line and not line.strip().startswith('*'):
            lines[i] = re.sub(r'//(.*)$', r'//\1', line)
    java_code = '\n'.join(lines)
    
    # 4. 删除#region和#endregion
    java_code = re.sub(r'#region.*$\s*', '', java_code, flags=re.MULTILINE)
    java_code = re.sub(r'#endregion.*$\s*', '', java_code, flags=re.MULTILINE)
    
    # 5. 转换方法名：首字母小写（驼峰格式）
    def convert_method_name(match):
        modifier = match.group(1)  # public/private/protected/internal
        return_type = match.group(2)
        method_name = match.group(3)
        parameters = match.group(4)
        rest = match.group(5)
        
        # 将方法名首字母小写
        if method_name and len(method_name) > 0:
            java_method_name = method_name[0].lower() + method_name[1:]
            return f'{modifier} {return_type} {java_method_name}{parameters}{rest}'
        return match.group(0)
    
    # 匹配方法定义（简化版，可根据需要调整）
    pattern = r'(public|private|protected|internal)\s+([\w<>\[\]]+)\s+([A-Z]\w*)\s*\(([^)]*)\)(\s*\{)'
    java_code = re.sub(pattern, convert_method_name, java_code)
    
    # 6. 转换属性为Java的getter/setter
    # 这里简单处理：将自动属性转换为字段
    # 匹配 public Type PropertyName { get; set; }
    def convert_property(match):
        visibility = match.group(1)
        prop_type = match.group(2)
        prop_name = match.group(3)
        field_name = prop_name[0].lower() + prop_name[1:]
        
        getter = f'    {visibility} {prop_type} get{prop_name}() {{\n        return {field_name};\n    }}\n'
        setter = f'    {visibility} void set{prop_name}({prop_type} {field_name}) {{\n        this.{field_name} = {field_name};\n    }}\n'
        
        return f'    private {prop_type} {field_name};\n\n{getter}\n{setter}'
    
    pattern = r'(public|private|protected|internal)\s+([\w<>\[\]]+)\s+([A-Z]\w*)\s*\{\s*get;\s*set;\s*\}'
    java_code = re.sub(pattern, convert_property, java_code)
    
    # 7. 转换类型引用
    # string -> String
    java_code = re.sub(r'\bstring\b', 'String', java_code)
    # int -> int (保持不变)
    # bool -> boolean
    java_code = re.sub(r'\bbool\b', 'boolean', java_code)
    # object -> Object
    java_code = re.sub(r'\bobject\b', 'Object', java_code)
    
    # 8. 添加Java类声明
    # 如果类没有extends或implements，添加默认的
    if ' class ' in java_code:
        # 找到类声明行
        class_pattern = r'(public|private|protected)?\s*(partial)?\s*class\s+(\w+)'
        java_code = re.sub(class_pattern, lambda m: f'public class {m.group(3)}', java_code)
    else:
        # 如果没有类声明，添加一个
        java_code = f'public class {class_name} {{\n{java_code}\n}}'
    
    # 9. 添加必要的import语句（根据代码中的类型推断）
    imports = set()
    
    # 检测常用的Java集合类型
    if 'List<' in java_code:
        imports.add('import java.util.List;')
        imports.add('import java.util.ArrayList;')
    if 'Dictionary<' in java_code or 'Map<' in java_code:
        imports.add('import java.util.Map;')
        imports.add('import java.util.HashMap;')
    if 'DateTime' in java_code:
        imports.add('import java.time.LocalDateTime;')
        imports.add('import java.time.format.DateTimeFormatter;')
    if 'Task<' in java_code:
        imports.add('import java.util.concurrent.CompletableFuture;')
    if 'IEnumerable<' in java_code:
        imports.add('import java.util.Iterable;')
    
    # 构建完整的Java文件
    final_java_code = ''
    if imports:
        final_java_code += '\n'.join(sorted(imports)) + '\n\n'
    
    final_java_code += java_code
    
    # 10. 清理多余的空白行
    final_java_code = re.sub(r'\n\s*\n\s*\n', '\n\n', final_java_code)
    
    return final_java_code


def process_folder(input_folder, output_folder=None):
    """
    处理文件夹中的所有C#文件
    
    Args:
        input_folder: 输入文件夹路径
        output_folder: 输出文件夹路径（如果不指定，则在原文件夹下创建java_output目录）
    """
    
    # 设置输出文件夹
    if output_folder is None:
        output_folder = os.path.join(input_folder, 'java_output')
    
    # 创建输出文件夹
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"创建输出目录: {output_folder}")
    
    # 查找所有.cs文件
    cs_files = glob.glob(os.path.join(input_folder, '*.cs'))
    
    if not cs_files:
        print(f"在 {input_folder} 中没有找到.cs文件")
        return
    
    print(f"找到 {len(cs_files)} 个C#文件")
    
    for cs_file in cs_files:
        try:
            # 读取C#文件
            with open(cs_file, 'r', encoding='utf-8') as f:
                csharp_code = f.read()
            
            # 提取类名（从文件名或代码中）
            base_name = os.path.basename(cs_file)
            class_name = base_name.replace('.cs', '')
            
            # 转换为Java
            java_code = convert_csharp_to_java(csharp_code, class_name)
            
            # 生成Java文件名
            java_file_name = f'{class_name}Impl.java'
            java_file_path = os.path.join(output_folder, java_file_name)
            
            # 写入Java文件
            with open(java_file_path, 'w', encoding='utf-8') as f:
                f.write(java_code)
            
            print(f"✓ 转换成功: {base_name} -> {java_file_name}")
            
        except Exception as e:
            print(f"✗ 转换失败: {cs_file}")
            print(f"  错误: {str(e)}")
    
    print(f"\n转换完成！输出目录: {output_folder}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='将C#服务实现类转换为Java实现类')
    parser.add_argument('input_folder', help='输入的C#文件夹路径')
    parser.add_argument('-o', '--output', help='输出的Java文件夹路径（可选）', default=None)
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_folder):
        print(f"错误: 输入文件夹不存在: {args.input_folder}")
        return
    
    if not os.path.isdir(args.input_folder):
        print(f"错误: 输入路径不是文件夹: {args.input_folder}")
        return
    
    process_folder(args.input_folder, args.output)


if __name__ == '__main__':
    # 如果没有命令行参数，使用交互式输入
    import sys
    
    if len(sys.argv) == 1:
        input_folder = input("请输入C#文件所在的文件夹路径: ").strip()
        output_folder = input("请输入Java输出文件夹路径（直接回车使用默认）: ").strip()
        
        if not output_folder:
            output_folder = None
        
        if os.path.exists(input_folder) and os.path.isdir(input_folder):
            process_folder(input_folder, output_folder)
        else:
            print(f"错误: 文件夹不存在: {input_folder}")
    else:
        main()
