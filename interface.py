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
        
        # Java关键字（用于转义）
        self.java_keywords = {
            'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch',
            'char', 'class', 'const', 'continue', 'default', 'do', 'double',
            'else', 'enum', 'extends', 'final', 'finally', 'float', 'for',
            'goto', 'if', 'implements', 'import', 'instanceof', 'int', 'interface',
            'long', 'native', 'new', 'package', 'private', 'protected', 'public',
            'return', 'short', 'static', 'strictfp', 'super', 'switch',
            'synchronized', 'this', 'throw', 'throws', 'transient', 'try',
            'void', 'volatile', 'while'
        }
        
        # 转换统计
        self.stats = {
            'files_processed': 0,
            'files_converted': 0,
            'files_failed': 0
        }

    def convert_file(self, input_path: str, output_path: str = None, 
                     package_name: str = None) -> bool:
        """
        转换单个C#接口文件为Java接口文件
        
        Args:
            input_path: 输入的C#文件路径
            output_path: 输出的Java文件路径（可选）
            package_name: 自定义包名（可选）
        
        Returns:
            bool: 转换是否成功
        """
        try:
            # 读取输入文件
            with open(input_path, 'r', encoding='utf-8') as file:
                csharp_code = file.read()
            
            # 转换代码
            java_code = self.convert_interface(csharp_code, package_name)
            
            # 确定输出路径
            if output_path is None:
                output_path = input_path.replace('.cs', '.java')
            
            # 确保输出目录存在
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
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
                      pattern: str = "*.cs", recursive: bool = True,
                      package_name: str = None) -> None:
        """
        转换文件夹中的所有C#接口文件
        
        Args:
            folder_path: 输入文件夹路径
            output_folder: 输出文件夹路径（可选）
            pattern: 文件匹配模式
            recursive: 是否递归处理子文件夹
            package_name: 自定义包名（可选）
        """
        folder = Path(folder_path)
        if not folder.exists():
            print(f"错误：文件夹不存在 - {folder_path}")
            return
        
        # 查找所有.cs文件
        if recursive:
            cs_files = list(folder.rglob(pattern))
        else:
            cs_files = list(folder.glob(pattern))
        
        # 过滤只包含接口的文件（可选）
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
                # 保持相对路径结构
                rel_path = cs_file.relative_to(folder)
                output_path = Path(output_folder) / rel_path.with_suffix('.java')
                self.convert_file(str(cs_file), str(output_path), package_name)
            else:
                self.convert_file(str(cs_file), package_name=package_name)
        
        # 打印统计信息
        self._print_stats()

    def _is_interface_file(self, file_path: Path) -> bool:
        """判断文件是否包含接口定义"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                # 检查是否包含interface关键字
                return bool(re.search(r'\binterface\s+\w+', content))
        except:
            return True  # 如果无法读取，默认尝试转换

    def convert_interface(self, csharp_code: str, package_name: str = None) -> str:
        """
        将C#接口代码转换为Java接口代码，保留所有注释
        
        Args:
            csharp_code: C#接口代码
            package_name: 自定义包名（如果提供，将覆盖原有的namespace）
        
        Returns:
            str: 转换后的Java接口代码
        """
        lines = csharp_code.split('\n')
        converted_lines = []
        
        i = 0
        in_interface = False
        interface_start_line = -1
        brace_count = 0
        current_interface_name = None
        
        while i < len(lines):
            line = lines[i]
            
            # 处理注释（先处理，因为需要在转换前转换注释格式）
            if self._is_comment_line(line):
                converted_line = self._convert_comment_format(line)
                converted_lines.append(converted_line)
                i += 1
                continue
            
            # 检测接口开始
            if not in_interface and re.search(r'\binterface\s+\w+', line):
                in_interface = True
                interface_start_line = i
                # 转换接口声明行（包括改名）
                converted_line, current_interface_name = self._convert_interface_line(line)
                converted_lines.append(converted_line)
                i += 1
                continue
            
            # 在接口内部
            if in_interface:
                # 跟踪大括号
                brace_count += line.count('{') - line.count('}')
                
                # 转换方法声明
                if re.search(r'\w+\s+\w+\s*\([^)]*\)', line) and '{' not in line:
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
                    converted_line = self._convert_types_in_line(line)
                    converted_lines.append(converted_line)
                
                # 检查接口结束
                if brace_count == 0 and i > interface_start_line:
                    in_interface = False
                
                i += 1
                continue
            
            # 处理using语句（转换为import）
            if line.strip().startswith('using '):
                converted_line = self._convert_using_line(line)
                converted_lines.append(converted_line)
                i += 1
                continue
            
            # 处理namespace（转换为package）
            if line.strip().startswith('namespace '):
                converted_line = self._convert_namespace_line(line, package_name)
                converted_lines.append(converted_line)
                i += 1
                continue
            
            # 移除business interface相关的内容
            if 'business' in line.lower() and 'interface' in line.lower():
                # 跳过或转换包含business interface的行
                line = re.sub(r'\bbusiness\s+', '', line, flags=re.IGNORECASE)
                line = re.sub(r'\bBusiness\s+', '', line)
            
            # 其他行：转换类型引用
            converted_line = self._convert_types_in_line(line)
            converted_lines.append(converted_line)
            i += 1
        
        # 清理多余的空行
        result = '\n'.join(converted_lines)
        result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)
        
        return result

    def _is_comment_line(self, line: str) -> bool:
        """判断是否为注释行"""
        stripped = line.strip()
        return (stripped.startswith('//') or 
                stripped.startswith('/*') or 
                stripped.startswith('*') or
                stripped.startswith('///'))

    def _convert_comment_format(self, line: str) -> str:
        """转换注释格式为Java格式"""
        stripped = line.strip()
        
        # 处理XML注释 /// 转换为 JavaDoc /** */
        if stripped.startswith('///'):
            # 移除///前缀
            content = stripped[3:].strip()
            if not content:
                return '     *'
            
            # 检查是否是总结标签
            if content.startswith('<summary>'):
                content = content.replace('<summary>', '').replace('</summary>', '')
                return f'    /**\n     * {content}\n     */'
            
            # 检查是否是参数标签
            param_match = re.search(r'<param name="(\w+)">(.*?)</param>', content)
            if param_match:
                param_name, param_desc = param_match.groups()
                return f'     * @param {param_name} {param_desc}'
            
            # 检查是否是返回值标签
            if content.startswith('<returns>'):
                content = content.replace('<returns>', '').replace('</returns>', '')
                return f'     * @return {content}'
            
            # 普通XML注释转换为JavaDoc
            return f'    /**\n     * {content}\n     */'
        
        # 处理单行注释 //
        elif stripped.startswith('//') and not stripped.startswith('///'):
            content = stripped[2:].strip()
            return f'    // {content}'
        
        # 处理多行注释开始 /*
        elif stripped.startswith('/*'):
            return line
        
        # 处理多行注释中间 *
        elif stripped.startswith('*'):
            return line
        
        return line

    def _convert_interface_line(self, line: str) -> Tuple[str, Optional[str]]:
        """
        转换接口声明行，去掉I前缀，添加Service后缀
        
        Returns:
            Tuple[str, Optional[str]]: (转换后的行, 新的接口名)
        """
        # 提取接口名
        match = re.search(r'\binterface\s+(\w+)', line)
        if not match:
            return line, None
        
        old_name = match.group(1)
        
        # 去掉I前缀
        if old_name.startswith('I') and len(old_name) > 1 and old_name[1].isupper():
            base_name = old_name[1:]
        else:
            base_name = old_name
        
        # 添加Service后缀
        new_name = base_name + 'Service'
        
        # 替换接口名
        line = line.replace(old_name, new_name)
        
        # 处理泛型
        line = re.sub(r'<([^<>]+)>', r'<\1>', line)
        
        # 转换访问修饰符
        line = re.sub(r'\bpublic\s+', 'public ', line)
        line = re.sub(r'\binternal\s+', '', line)
        line = re.sub(r'\bprivate\s+', '', line)
        
        # 处理继承
        line = re.sub(r':\s*(\w+)', r'extends \1', line)
        line = re.sub(r',\s*(\w+)', r', \1', line)
        
        # 移除partial关键字
        line = re.sub(r'\bpartial\s+', '', line)
        
        return line.rstrip(), new_name

    def _convert_method_line(self, line: str) -> str:
        """转换方法声明行"""
        # 转换返回类型
        for cs_type, java_type in self.type_mappings.items():
            line = re.sub(rf'\b{cs_type}\b(?=\s+\w+\s*\()', java_type, line)
        
        # 转换参数中的类型
        line = self._convert_parameter_types(line)
        
        # 移除body（如果有）
        line = re.sub(r'\s*\{.*$', ';', line)
        
        # 如果没有分号，添加分号
        if not line.strip().endswith(';'):
            line = line.rstrip() + ';'
        
        # 处理异步方法
        line = re.sub(r'\basync\s+', '', line)
        
        # 处理override关键字
        line = re.sub(r'\boverride\s+', '', line)
        
        # 处理virtual关键字
        line = re.sub(r'\bvirtual\s+', '', line)
        
        # 处理泛型约束
        line = re.sub(r'\bwhere\s+\w+\s*:.*$', '', line)
        
        return line.rstrip()

    def _convert_property_line(self, line: str) -> str:
        """转换属性为getter/setter方法"""
        # 匹配属性模式：Type PropertyName { get; set; }
        match = re.search(r'(\w+)\s+(\w+)\s*\{\s*get;\s*set;\s*\}', line)
        if match:
            prop_type, prop_name = match.groups()
            java_type = self.type_mappings.get(prop_type, prop_type)
            
            # 生成getter和setter方法声明
            getter = f'    {java_type} get{prop_name.capitalize()}();'
            setter = f'    void set{prop_name.capitalize()}({java_type} {prop_name});'
            return f'{getter}\n    {setter}'
        
        # 只读属性：Type PropertyName { get; }
        match = re.search(r'(\w+)\s+(\w+)\s*\{\s*get;\s*\}', line)
        if match:
            prop_type, prop_name = match.groups()
            java_type = self.type_mappings.get(prop_type, prop_type)
            return f'    {java_type} get{prop_name.capitalize()}();'
        
        return line

    def _convert_event_line(self, line: str) -> str:
        """转换事件为观察者模式方法"""
        match = re.search(r'event\s+(\w+)\s+(\w+)', line)
        if match:
            event_type, event_name = match.groups()
            return (f'    void add{event_name.capitalize()}Listener({event_type} listener);\n'
                    f'    void remove{event_name.capitalize()}Listener({event_type} listener);')
        return line

    def _convert_using_line(self, line: str) -> str:
        """转换using语句为import语句"""
        match = re.search(r'using\s+([\w.]+);', line)
        if match:
            namespace = match.group(1)
            
            # C#命名空间到Java包的映射
            namespace_mappings = {
                'System': 'java.lang',
                'System.Collections.Generic': 'java.util',
                'System.Collections': 'java.util',
                'System.Threading.Tasks': 'java.util.concurrent',
                'System.IO': 'java.io',
                'System.Linq': 'java.util.stream',
            }
            
            for cs_ns, java_pkg in namespace_mappings.items():
                if namespace.startswith(cs_ns):
                    remaining = namespace[len(cs_ns):].strip('.')
                    if remaining:
                        return f'import {java_pkg}.{remaining};'
                    else:
                        return f'import {java_pkg}.*;'
            
            # 如果没有匹配，添加注释
            return f'// TODO: 需要手动转换 - {line.strip()}'
        
        return f'// {line.strip()}'

    def _convert_namespace_line(self, line: str, package_name: str = None) -> str:
        """转换namespace为package，移除business"""
        if package_name:
            # 如果包名包含business，移除它
            package_name = re.sub(r'\bbusiness\.', '', package_name, flags=re.IGNORECASE)
            package_name = re.sub(r'\.business', '', package_name, flags=re.IGNORECASE)
            return f'package {package_name};'
        
        match = re.search(r'namespace\s+([\w.]+)', line)
        if match:
            namespace = match.group(1)
            # 将命名空间转换为小写包名，并移除business
            namespace = re.sub(r'\bbusiness\.', '', namespace, flags=re.IGNORECASE)
            namespace = re.sub(r'\.business', '', namespace, flags=re.IGNORECASE)
            package = namespace.lower()
            return f'package {package};'
        
        return '// ' + line.strip()

    def _convert_parameter_types(self, line: str) -> str:
        """转换参数中的类型"""
        def replace_param_type(match):
            params = match.group(1)
            for cs_type, java_type in self.type_mappings.items():
                params = re.sub(rf'\b{cs_type}\b(?=\s+\w+)', java_type, params)
            return f'({params})'
        
        return re.sub(r'\(([^)]*)\)', replace_param_type, line)

    def _convert_types_in_line(self, line: str) -> str:
        """转换行中的类型引用"""
        # 转换类型
        for cs_type, java_type in self.type_mappings.items():
            line = re.sub(rf'\b{cs_type}\b(?=\s+\w+|\s*[\[<]|\s*$)', java_type, line)
        
        # 处理可空类型（Type? -> Optional<Type>）
        line = re.sub(r'(\w+)\?', lambda m: f'Optional<{self.type_mappings.get(m.group(1), m.group(1))}>', line)
        
        # 处理泛型
        line = re.sub(r'List<([^>]+)>', r'List<\1>', line)
        line = re.sub(r'Dictionary<([^,]+),\s*([^>]+)>', r'Map<\1, \2>', line)
        
        return line

    def _clean_braces(self, code: str) -> str:
        """清理多余的大括号"""
        code = re.sub(r'\}\s*$', '', code.strip())
        return code

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
        description='C#接口转Java接口工具 - 注释转换、接口重命名（去掉I前缀，添加Service后缀）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
转换规则:
  1. 注释转换: /// <summary> -> /** */, <param> -> @param, <returns> -> @return
  2. 接口重命名: IUserRepository -> UserRepositoryService (去掉I前缀，添加Service后缀)
  3. 包名处理: 自动移除namespace中的business关键字
  4. 类型映射: C#类型自动转换为Java类型

使用示例:
  # 转换单个文件
  python cs_to_java_interface.py -i IUserRepository.cs
  
  # 转换单个文件并指定输出路径
  python cs_to_java_interface.py -i IUserRepository.cs -o UserRepositoryService.java
  
  # 转换整个文件夹
  python cs_to_java_interface.py -i ./CSharpInterfaces -o ./JavaInterfaces
  
  # 递归转换所有子文件夹中的接口
  python cs_to_java_interface.py -i ./Project -o ./JavaProject --recursive
  
  # 指定包名（会自动移除business）
  python cs_to_java_interface.py -i IUserRepository.cs --package com.example.service
        """
    )
    
    parser.add_argument('-i', '--input', required=True,
                       help='输入文件或文件夹路径')
    parser.add_argument('-o', '--output',
                       help='输出文件或文件夹路径（可选）')
    parser.add_argument('-p', '--package',
                       help='指定Java包名（可选，会覆盖原有的namespace）')
    parser.add_argument('-r', '--recursive', action='store_true',
                       help='递归处理子文件夹')
    parser.add_argument('--pattern', default='*.cs',
                       help='文件匹配模式（默认：*.cs）')
    
    args = parser.parse_args()
    
    # 创建转换器
    converter = CSharpToJavaConverter()
    
    # 检查输入类型
    input_path = Path(args.input)
    
    if input_path.is_file():
        # 转换单个文件
        print(f"开始转换单个文件: {args.input}")
        print("-" * 60)
        converter.convert_file(args.input, args.output, args.package)
        
    elif input_path.is_dir():
        # 转换文件夹
        print(f"开始转换文件夹: {args.input}")
        print("-" * 60)
        converter.convert_folder(args.input, args.output, 
                                 args.pattern, args.recursive, 
                                 args.package)
    else:
        print(f"错误：输入路径不存在 - {args.input}")
        sys.exit(1)


if __name__ == "__main__":
    main()
