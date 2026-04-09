#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C# Interface to Java Interface Converter
支持将C#接口文件转换为Java接口文件，保留所有注释
支持单个文件或整个文件夹的转换
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional

class CSharpToJavaConverter:
    """C#接口到Java接口的转换器"""
    
    def __init__(self):
        # C#类型到Java类型的映射
        self.type_mappings = {
            # 基本类型
            'string': 'String',
            'int': 'int',
            'long': 'long',
            'double': 'double',
            'float': 'float',
            'bool': 'boolean',
            'byte': 'byte',
            'char': 'char',
            'short': 'short',
            'object': 'Object',
            'void': 'void',
            
            # 常用类型
            'DateTime': 'LocalDateTime',
            'decimal': 'BigDecimal',
            'Guid': 'UUID',
            'TimeSpan': 'Duration',
            
            # 集合类型
            'IEnumerable': 'Iterable',
            'IList': 'List',
            'ICollection': 'Collection',
            'IDictionary': 'Map',
            'ISet': 'Set',
            'IReadOnlyList': 'List',
            'IReadOnlyCollection': 'Collection',
            'IReadOnlyDictionary': 'Map',
            
            # 异步类型
            'Task': 'CompletableFuture',
            'Task<T>': 'CompletableFuture',
            'ValueTask': 'CompletableFuture',
            
            # 可空类型
            'Nullable': 'Optional',
        }
        
        # 转换统计
        self.stats = {
            'files_processed': 0,
            'files_converted': 0,
            'files_failed': 0
        }

    def remove_i_prefix(self, class_name: str) -> str:
        """
        去掉类名的I前缀
        例如: IUserRepository -> UserRepository, IUser -> User
        """
        if class_name.startswith('I') and len(class_name) > 1 and class_name[1].isupper():
            return class_name[1:]
        return class_name

    def convert_type(self, type_name: str) -> str:
        """
        转换类型名称：
        1. 先检查类型映射（如string -> String）
        2. 然后去掉I前缀（如IUser -> User）
        """
        # 先处理类型映射
        if type_name in self.type_mappings:
            return self.type_mappings[type_name]
        
        # 去掉I前缀（包括Entity类型）
        return self.remove_i_prefix(type_name)

    def get_java_interface_name(self, cs_filename: str) -> str:
        """根据C#文件名生成Java接口文件名"""
        base_name = Path(cs_filename).stem
        
        # 去掉I前缀
        base_name = self.remove_i_prefix(base_name)
        
        # 添加Service后缀
        java_name = base_name + 'Service'
        
        return java_name + '.java'

    def convert_file(self, input_path: str, output_path: str = None) -> bool:
        """转换单个C#接口文件为Java接口文件"""
        try:
            # 读取输入文件
            with open(input_path, 'r', encoding='utf-8') as file:
                csharp_code = file.read()
            
            # 转换代码
            java_code = self.convert_interface(csharp_code)
            
            # 确定输出路径
            if output_path is None:
                input_file = Path(input_path)
                java_filename = self.get_java_interface_name(input_file.name)
                output_path = input_file.parent / java_filename
            else:
                output_path = Path(output_path)
            
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入转换后的代码
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(java_code)
            
            print(f"✓ 转换成功: {input_path} -> {output_path}")
            self.stats['files_converted'] += 1
            return True
            
        except Exception as e:
            print(f"✗ 转换失败 {input_path}: {str(e)}")
            self.stats['files_failed'] += 1
            return False

    def convert_folder(self, folder_path: str, output_folder: str = None,
                      pattern: str = "*.cs", recursive: bool = True) -> None:
        """转换文件夹中的所有C#接口文件"""
        folder = Path(folder_path)
        if not folder.exists():
            print(f"错误：文件夹不存在 - {folder_path}")
            return
        
        # 查找所有.cs文件
        if recursive:
            cs_files = list(folder.rglob(pattern))
        else:
            cs_files = list(folder.glob(pattern))
        
        # 过滤只包含接口的文件
        cs_files = [f for f in cs_files if self._is_interface_file(f)]
        
        if not cs_files:
            print(f"在 {folder_path} 中未找到C#接口文件")
            return
        
        print(f"找到 {len(cs_files)} 个C#接口文件待转换")
        print("-" * 60)
        
        self.stats['files_processed'] = len(cs_files)
        
        # 创建输出文件夹
        if output_folder:
            Path(output_folder).mkdir(parents=True, exist_ok=True)
        
        # 转换每个文件
        for cs_file in cs_files:
            if output_folder:
                java_filename = self.get_java_interface_name(cs_file.name)
                output_path = Path(output_folder) / java_filename
                self.convert_file(str(cs_file), str(output_path))
            else:
                self.convert_file(str(cs_file))
        
        # 打印统计信息
        self._print_stats()

    def _is_interface_file(self, file_path: Path) -> bool:
        """判断文件是否包含接口定义"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                return bool(re.search(r'\binterface\s+\w+', content))
        except:
            return True

    def convert_interface(self, csharp_code: str) -> str:
        """将C#接口代码转换为Java接口代码"""
        lines = csharp_code.split('\n')
        converted_lines = []
        
        i = 0
        in_interface = False
        interface_start_line = -1
        brace_count = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 跳过using语句
            if line.strip().startswith('using '):
                i += 1
                continue
            
            # 跳过namespace行
            if line.strip().startswith('namespace '):
                i += 1
                continue
            
            # 处理接口外部的注释
            if not in_interface and (line.strip().startswith('///') or line.strip().startswith('//')):
                comment_lines = []
                while i < len(lines) and (lines[i].strip().startswith('///') or lines[i].strip().startswith('//')):
                    comment_lines.append(lines[i])
                    i += 1
                converted_comment = self._convert_comment_block(comment_lines)
                if converted_comment:
                    converted_lines.append(converted_comment)
                continue
            
            # 检测接口开始
            if not in_interface and re.search(r'\binterface\s+\w+', line):
                in_interface = True
                interface_start_line = i
                # 转换接口声明行
                converted_line = self._convert_interface_line(line)
                converted_lines.append(converted_line)
                i += 1
                continue
            
            # 在接口内部
            if in_interface:
                # 跟踪大括号
                brace_count += line.count('{') - line.count('}')
                
                # 处理接口内的注释
                if line.strip().startswith('///') or line.strip().startswith('//'):
                    comment_lines = [line]
                    j = i + 1
                    while j < len(lines) and (lines[j].strip().startswith('///') or lines[j].strip().startswith('//')):
                        comment_lines.append(lines[j])
                        j += 1
                    
                    converted_comment = self._convert_comment_block(comment_lines)
                    if converted_comment:
                        converted_lines.append(converted_comment)
                    i = j
                    continue
                
                # 转换方法声明
                if re.search(r'\w+\s+\w+\s*\([^)]*\)', line) and '{' not in line and not line.strip().startswith('//'):
                    converted_line = self._convert_method_line(line)
                    converted_lines.append(converted_line)
                # 转换属性
                elif re.search(r'\w+\s+\w+\s*\{\s*get;\s*set;\s*\}', line, re.IGNORECASE):
                    converted_line = self._convert_property_line(line)
                    converted_lines.append(converted_line)
                # 转换事件
                elif re.search(r'\bevent\s+\w+\s+\w+', line):
                    converted_line = self._convert_event_line(line)
                    converted_lines.append(converted_line)
                else:
                    # 其他行：转换类型引用
                    stripped = line.strip()
                    if stripped and stripped != '{' and stripped != '}':
                        converted_line = self._convert_types_in_line(line)
                        converted_lines.append(converted_line)
                    elif stripped == '}':
                        converted_lines.append(line)
                
                # 检查接口结束
                if brace_count == 0 and i > interface_start_line:
                    in_interface = False
                
                i += 1
                continue
            
            # 其他行跳过
            i += 1
        
        # 清理多余的空行
        result = '\n'.join(converted_lines)
        result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)
        
        return result.strip()

    def _convert_comment_block(self, comment_lines: List[str]) -> str:
        """转换注释块"""
        if not comment_lines:
            return ""
        
        # 检查是否都是XML注释（///）
        is_xml = all(line.strip().startswith('///') for line in comment_lines)
        
        if is_xml:
            return self._convert_xml_comment(comment_lines)
        else:
            # 普通注释，直接保留
            result = []
            for line in comment_lines:
                if line.strip().startswith('//'):
                    content = line.strip()[2:].strip()
                    if content:
                        result.append(f'    // {content}')
                    else:
                        result.append('    //')
                else:
                    result.append(line)
            return '\n'.join(result)

    def _convert_xml_comment(self, xml_lines: List[str]) -> str:
        """转换XML注释为JavaDoc格式"""
        if not xml_lines:
            return ""
        
        # 提取所有注释内容
        comment_content = []
        for line in xml_lines:
            content = line.strip()[3:].strip()
            if content:
                comment_content.append(content)
        
        if not comment_content:
            return ""
        
        # 检查是否是单个简单注释
        if len(comment_content) == 1 and not any(tag in comment_content[0] for tag in ['<summary>', '<param>', '<returns>']):
            return f'    /**\n     * {comment_content[0]}\n     */'
        
        # 解析各个部分
        summary = ""
        params = []
        returns = ""
        
        full_text = ' '.join(comment_content)
        
        # 提取summary
        summary_match = re.search(r'<summary>(.*?)</summary>', full_text, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
            summary = re.sub(r'\s+', ' ', summary)
        
        # 提取所有param
        param_matches = re.finditer(r'<param\s+name="([^"]+)"\s*>(.*?)</param>', full_text, re.DOTALL)
        for match in param_matches:
            param_name = match.group(1)
            param_desc = match.group(2).strip()
            param_desc = re.sub(r'\s+', ' ', param_desc)
            params.append((param_name, param_desc))
        
        # 提取returns
        returns_match = re.search(r'<returns>(.*?)</returns>', full_text, re.DOTALL)
        if returns_match:
            returns = returns_match.group(1).strip()
            returns = re.sub(r'\s+', ' ', returns)
        
        # 如果没有找到任何标签，就把整个内容当作描述
        if not summary and not params and not returns:
            summary = ' '.join(comment_content)
            summary = re.sub(r'\s+', ' ', summary)
        
        # 构建JavaDoc
        javadoc_lines = ['    /**']
        
        if summary:
            javadoc_lines.append(f'     * {summary}')
            if params or returns:
                javadoc_lines.append('     *')
        
        for param_name, param_desc in params:
            javadoc_lines.append(f'     * @param {param_name} {param_desc}')
        
        if returns:
            if params:
                javadoc_lines.append('     *')
            javadoc_lines.append(f'     * @return {returns}')
        
        javadoc_lines.append('     */')
        
        return '\n'.join(javadoc_lines)

    def _convert_interface_line(self, line: str) -> str:
        """转换接口声明行"""
        # 提取接口名
        match = re.search(r'\binterface\s+(\w+)', line)
        if not match:
            return line
        
        old_name = match.group(1)
        
        # 去掉I前缀并添加Service后缀
        new_name = self.remove_i_prefix(old_name) + 'Service'
        
        # 替换接口名
        line = line.replace(old_name, new_name)
        
        # 处理泛型
        line = re.sub(r'<([^<>]+)>', r'<\1>', line)
        
        # 转换访问修饰符
        line = re.sub(r'\bpublic\s+', 'public ', line)
        line = re.sub(r'\binternal\s+', '', line)
        line = re.sub(r'\bprivate\s+', '', line)
        
        # 处理继承（去掉继承接口的I前缀）
        def replace_extends(match):
            extends_name = match.group(1)
            # 去掉I前缀
            new_extends_name = self.remove_i_prefix(extends_name)
            return f'extends {new_extends_name}'
        
        line = re.sub(r'extends\s+(\w+)', replace_extends, line)
        
        # 移除partial关键字
        line = re.sub(r'\bpartial\s+', '', line)
        
        # 确保以{结尾
        if not line.strip().endswith('{'):
            line = line.rstrip() + ' {'
        
        return line.rstrip()

    def _convert_method_line(self, line: str) -> str:
        """转换方法声明行"""
        # 转换返回类型（包括Entity类型）
        for cs_type, java_type in self.type_mappings.items():
            line = re.sub(rf'\b{cs_type}\b(?=\s+\w+\s*\()', java_type, line)
        
        # 转换返回类型中的Entity类型（去掉I前缀）
        def replace_return_type(match):
            return_type = match.group(1)
            # 去掉I前缀
            new_return_type = self.convert_type(return_type)
            return f'{new_return_type} {match.group(2)}'
        
        # 匹配返回类型和方法名： Type MethodName(
        line = re.sub(r'\b(\w+)\s+(\w+)\s*\(', replace_return_type, line)
        
        # 转换参数中的类型
        line = self._convert_parameter_types(line)
        
        # 移除body
        line = re.sub(r'\s*\{.*$', ';', line)
        
        # 确保以分号结尾
        if not line.strip().endswith(';'):
            line = line.rstrip() + ';'
        
        # 移除C#特定关键字
        line = re.sub(r'\basync\s+', '', line)
        line = re.sub(r'\boverride\s+', '', line)
        line = re.sub(r'\bvirtual\s+', '', line)
        line = re.sub(r'\bwhere\s+\w+\s*:.*$', '', line)
        
        # 添加缩进
        if not line.startswith('    '):
            line = '    ' + line.lstrip()
        
        return line.rstrip()

    def _convert_property_line(self, line: str) -> str:
        """转换属性为getter/setter方法"""
        # 匹配属性模式：Type PropertyName { get; set; }
        match = re.search(r'(\w+)\s+(\w+)\s*\{\s*get;\s*set;\s*\}', line)
        if match:
            prop_type, prop_name = match.groups()
            # 转换类型（去掉I前缀）
            java_type = self.convert_type(prop_type)
            
            # 生成getter和setter方法声明
            getter = f'    {java_type} get{prop_name.capitalize()}();'
            setter = f'    void set{prop_name.capitalize()}({java_type} {prop_name});'
            return f'{getter}\n    {setter}'
        
        # 只读属性：Type PropertyName { get; }
        match = re.search(r'(\w+)\s+(\w+)\s*\{\s*get;\s*\}', line)
        if match:
            prop_type, prop_name = match.groups()
            java_type = self.convert_type(prop_type)
            return f'    {java_type} get{prop_name.capitalize()}();'
        
        return line

    def _convert_event_line(self, line: str) -> str:
        """转换事件为观察者模式方法"""
        match = re.search(r'event\s+(\w+)\s+(\w+)', line)
        if match:
            event_type, event_name = match.groups()
            # 转换事件类型（去掉I前缀）
            java_type = self.convert_type(event_type)
            return (f'    void add{event_name.capitalize()}Listener({java_type} listener);\n'
                    f'    void remove{event_name.capitalize()}Listener({java_type} listener);')
        return line

    def _convert_parameter_types(self, line: str) -> str:
        """转换参数中的类型"""
        def replace_param_type(match):
            params = match.group(1)
            if not params.strip():
                return '()'
            
            # 分割多个参数
            param_parts = params.split(',')
            converted_params = []
            
            for part in param_parts:
                part = part.strip()
                if part:
                    # 匹配类型和参数名
                    type_match = re.match(r'(\w+)\s+(\w+)', part)
                    if type_match:
                        param_type, param_name = type_match.groups()
                        # 转换类型（去掉I前缀）
                        new_type = self.convert_type(param_type)
                        converted_params.append(f'{new_type} {param_name}')
                    else:
                        converted_params.append(part)
            
            return f'({", ".join(converted_params)})'
        
        return re.sub(r'\(([^)]*)\)', replace_param_type, line)

    def _convert_types_in_line(self, line: str) -> str:
        """转换行中的类型引用"""
        # 转换所有类型（包括Entity类型）
        def replace_type(match):
            type_name = match.group(1)
            # 转换类型（去掉I前缀）
            return self.convert_type(type_name)
        
        # 匹配独立的类型名称（作为返回类型、变量类型等）
        # 注意：避免匹配到方法名
        line = re.sub(r'\b([A-Z][a-zA-Z0-9]+)\b(?=\s+\w+|\s*[\[<]|\s*$)', replace_type, line)
        
        # 转换基本类型
        for cs_type, java_type in self.type_mappings.items():
            line = re.sub(rf'\b{cs_type}\b', java_type, line)
        
        # 处理可空类型
        line = re.sub(r'(\w+)\?', lambda m: f'Optional<{self.convert_type(m.group(1))}>', line)
        
        # 处理泛型
        line = re.sub(r'List<([^>]+)>', lambda m: f'List<{self.convert_type(m.group(1))}>', line)
        line = re.sub(r'Dictionary<([^,]+),\s*([^>]+)>', lambda m: f'Map<{self.convert_type(m.group(1))}, {self.convert_type(m.group(2))}>', line)
        
        return line

    def _print_stats(self):
        """打印转换统计信息"""
        print("-" * 60)
        print(f"转换完成统计:")
        print(f"  - 处理文件数: {self.stats['files_processed']}")
        print(f"  - 成功转换: {self.stats['files_converted']}")
        print(f"  - 转换失败: {self.stats['files_failed']}")
        print("-" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='C#接口转Java接口工具 - 自动删除所有类型的I前缀',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
转换规则:
  1. 接口名: IUserRepository -> UserRepositoryService
  2. Entity类型: IUser -> User, IOrder -> Order
  3. 返回类型: Task<IUser> -> CompletableFuture<User>
  4. 参数类型: void Save(IUser user) -> void save(User user)
  5. string类型: string -> String

使用示例:
  # 转换单个文件
  python cs_to_java_interface.py -i IUserRepository.cs
  
  # 转换整个文件夹
  python cs_to_java_interface.py -i ./CSharpInterfaces -o ./JavaInterfaces
  
  # 递归转换所有子文件夹
  python cs_to_java_interface.py -i ./Project -o ./JavaProject --recursive
        """
    )
    
    parser.add_argument('-i', '--input', required=True,
                       help='输入文件或文件夹路径')
    parser.add_argument('-o', '--output',
                       help='输出文件或文件夹路径（可选）')
    parser.add_argument('-r', '--recursive', action='store_true',
                       help='递归处理子文件夹')
    parser.add_argument('--pattern', default='*.cs',
                       help='文件匹配模式（默认：*.cs）')
    
    args = parser.parse_args()
    
    converter = CSharpToJavaConverter()
    input_path = Path(args.input)
    
    if input_path.is_file():
        print(f"开始转换单个文件: {args.input}")
        print("-" * 60)
        converter.convert_file(args.input, args.output)
    elif input_path.is_dir():
        print(f"开始转换文件夹: {args.input}")
        print("-" * 60)
        converter.convert_folder(args.input, args.output, 
                                 args.pattern, args.recursive)
    else:
        print(f"错误：输入路径不存在 - {args.input}")
        sys.exit(1)


if __name__ == "__main__":
    main()
