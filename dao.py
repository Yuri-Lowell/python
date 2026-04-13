#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C# LINQ to SQL to Java MyBatis Mapper Converter
将C# LINQ DAO层转换为Java MyBatis Mapper接口和XML文件
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import argparse

class LinqToMyBatisConverter:
    """C# LINQ to SQL 到 Java MyBatis 转换器"""
    
    def __init__(self):
        """初始化类型映射表"""
        self.csharp_to_java_type = {
            'int': 'Integer', 'int?': 'Integer',
            'long': 'Long', 'long?': 'Long',
            'short': 'Short', 'short?': 'Short',
            'byte': 'Byte', 'byte?': 'Byte',
            'bool': 'Boolean', 'bool?': 'Boolean',
            'boolean': 'Boolean',
            'float': 'Float', 'float?': 'Float',
            'double': 'Double', 'double?': 'Double',
            'decimal': 'BigDecimal', 'decimal?': 'BigDecimal',
            'string': 'String', 'char': 'String', 'char?': 'String',
            'DateTime': 'Date', 'DateTime?': 'Date',
            'Guid': 'String', 'Guid?': 'String',
            'void': 'void', 'Task': 'void',
            'object': 'Object', 'Object': 'Object'
        }

    def find_dao_files(self, input_path: str) -> List[str]:
        """查找所有C# DAO文件"""
        dao_files = []
        input_path = Path(input_path)
        
        if input_path.is_file():
            if input_path.suffix == '.cs':
                dao_files.append(str(input_path))
        else:
            for cs_file in input_path.rglob('*.cs'):
                if any(keyword in cs_file.stem for keyword in ['DAO', 'Dao', 'Repository', 'DAL']):
                    dao_files.append(str(cs_file))
        
        return dao_files

    def extract_comments_from_csharp(self, lines: List[str], method_line_idx: int) -> Dict[str, str]:
        """从C#文件中提取方法前的注释"""
        result = {'summary': '', 'params': {}, 'returns': ''}
        
        # 向上查找注释行
        comment_lines = []
        i = method_line_idx - 1
        
        while i >= 0 and i > method_line_idx - 30:  # 最多向上找30行
            line = lines[i].strip()
            if line.startswith('///'):
                comment_lines.insert(0, lines[i])
            elif line.startswith('//') and not line.startswith('///'):
                comment_lines.insert(0, lines[i])
            elif line.startswith('/*'):
                comment_lines.insert(0, lines[i])
                # 多行注释需要继续向上找
                if '*/' not in line:
                    j = i - 1
                    while j >= 0:
                        comment_lines.insert(0, lines[j])
                        if '*/' in lines[j]:
                            break
                        j -= 1
                break
            elif line and not line.startswith('[') and not line.startswith('using') and not line.startswith('namespace'):
                # 遇到非注释非属性行，停止
                if comment_lines:
                    break
            i -= 1
        
        if not comment_lines:
            return result
        
        comment_text = '\n'.join(comment_lines)
        
        # 提取summary
        summary_match = re.search(r'///\s*<summary>\s*(.*?)\s*</summary>', comment_text, re.DOTALL | re.IGNORECASE)
        if summary_match:
            summary = summary_match.group(1).strip()
            summary = re.sub(r'\s+', ' ', summary)
            result['summary'] = summary
        else:
            # 尝试普通注释
            for line in comment_lines:
                line_stripped = line.strip()
                if line_stripped.startswith('///') and '<' not in line_stripped:
                    content = line_stripped[3:].strip()
                    if content:
                        result['summary'] = content
                        break
                elif line_stripped.startswith('//') and not line_stripped.startswith('///'):
                    content = line_stripped[2:].strip()
                    if content:
                        result['summary'] = content
                        break
        
        # 提取param
        param_pattern = r'///\s*<param\s+name="(\w+)">\s*(.*?)\s*</param>'
        for match in re.finditer(param_pattern, comment_text, re.DOTALL | re.IGNORECASE):
            param_name = match.group(1)
            param_desc = match.group(2).strip()
            param_desc = re.sub(r'\s+', ' ', param_desc)
            result['params'][param_name] = param_desc
        
        # 提取returns
        returns_match = re.search(r'///\s*<returns>\s*(.*?)\s*</returns>', comment_text, re.DOTALL | re.IGNORECASE)
        if returns_match:
            returns_desc = returns_match.group(1).strip()
            returns_desc = re.sub(r'\s+', ' ', returns_desc)
            result['returns'] = returns_desc
        
        return result

    def parse_csharp_dao(self, file_content: str) -> Dict:
        """解析C# DAO文件 - 完整解析所有方法"""
        result = {
            'namespace': '',
            'class_name': '',
            'class_comments': '',
            'methods': [],
            'usings': []
        }
        
        lines = file_content.split('\n')
        
        # 提取using
        for line in lines:
            using_match = re.match(r'using\s+([\w.]+);', line.strip())
            if using_match:
                result['usings'].append(using_match.group(1))
        
        # 提取namespace
        for line in lines:
            ns_match = re.search(r'namespace\s+([\w.]+)', line)
            if ns_match:
                result['namespace'] = ns_match.group(1)
                break
        
        # 提取类名和类注释
        for i, line in enumerate(lines):
            class_match = re.search(r'(?:public|internal|private)?\s*(?:static\s+)?(?:partial\s+)?class\s+(\w+)', line)
            if class_match:
                result['class_name'] = class_match.group(1)
                # 提取类注释
                for j in range(i-1, max(0, i-20), -1):
                    prev_line = lines[j].strip()
                    if prev_line.startswith('///'):
                        summary_match = re.search(r'<summary>(.*?)</summary>', prev_line, re.DOTALL)
                        if summary_match:
                            result['class_comments'] = re.sub(r'\s+', ' ', summary_match.group(1).strip())
                            break
                break
        
        # 解析所有方法 - 使用更全面的匹配
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 更完整的方法匹配模式
            method_pattern = r'^(?:public|private|protected|internal)\s+' + \
                           r'(?:static\s+)?(?:virtual\s+)?(?:override\s+)?(?:async\s+)?' + \
                           r'(?:new\s+)?' + \
                           r'(?:Task<)?' + \
                           r'(\w+(?:<[^>]+>)?(?:\?)?)' + \
                           r'(?:>)?\s+' + \
                           r'(\w+)\s*' + \
                           r'\(([^)]*)\)'
            
            match = re.match(method_pattern, line)
            
            if match:
                return_type = match.group(1)
                method_name = match.group(2)
                params_str = match.group(3)
                
                # 跳过构造函数
                if method_name == result['class_name']:
                    i += 1
                    continue
                
                # 提取注释
                comments = self.extract_comments_from_csharp(lines, i)
                
                # 解析参数
                parameters = self.parse_parameters(params_str)
                
                # 查找方法体
                method_body = ""
                brace_count = 0
                j = i
                found_start = False
                
                while j < len(lines):
                    current_line = lines[j]
                    if '{' in current_line and not found_start:
                        found_start = True
                        brace_count += current_line.count('{')
                        method_body += current_line + '\n'
                    elif found_start:
                        method_body += current_line + '\n'
                        brace_count -= current_line.count('}')
                        if brace_count <= 0:
                            break
                    j += 1
                
                # 生成SQL
                sql_statement, sql_type = self.generate_sql_from_method(method_body, method_name, parameters)
                
                result['methods'].append({
                    'name': method_name,
                    'return_type': return_type,
                    'parameters': parameters,
                    'sql_type': sql_type,
                    'sql_statement': sql_statement,
                    'comments': comments,
                    'line_number': i
                })
            
            i += 1
        
        return result

    def parse_parameters(self, params_str: str) -> List[Dict]:
        """解析方法参数 - 支持复杂参数"""
        if not params_str or params_str.strip() == '':
            return []
        
        parameters = []
        
        # 处理参数中的泛型
        param_parts = []
        current_param = ""
        angle_bracket_count = 0
        
        for char in params_str:
            if char == '<':
                angle_bracket_count += 1
            elif char == '>':
                angle_bracket_count -= 1
            elif char == ',' and angle_bracket_count == 0:
                param_parts.append(current_param.strip())
                current_param = ""
                continue
            current_param += char
        
        if current_param.strip():
            param_parts.append(current_param.strip())
        
        for param in param_parts:
            if not param:
                continue
            
            # 匹配参数类型和名称
            match = re.match(r'(?:\[.*?\])?\s*(\w+(?:<[^>]+>)?(?:\?)?)\s+(\w+)', param)
            if match:
                param_type = match.group(1)
                param_name = match.group(2)
                java_type = self.map_to_java_type(param_type)
                
                parameters.append({
                    'csharp_type': param_type,
                    'java_type': java_type,
                    'name': param_name
                })
            else:
                # 尝试匹配带默认值的参数
                match2 = re.match(r'(?:\[.*?\])?\s*(\w+(?:<[^>]+>)?(?:\?)?)\s+(\w+)\s*=', param)
                if match2:
                    param_type = match2.group(1)
                    param_name = match2.group(2)
                    java_type = self.map_to_java_type(param_type)
                    
                    parameters.append({
                        'csharp_type': param_type,
                        'java_type': java_type,
                        'name': param_name
                    })
        
        return parameters

    def generate_sql_from_method(self, method_body: str, method_name: str, parameters: List[Dict]) -> Tuple[str, str]:
        """从方法体生成SQL语句"""
        method_lower = method_name.lower()
        table_name = self.infer_table_name(method_name)
        
        # 推断SQL类型
        if method_lower.startswith(('insert', 'add', 'create', 'save')):
            if parameters:
                columns = [self.camel_to_snake(p['name']) for p in parameters]
                values = [f"#{{{p['name']}}}" for p in parameters]
                return f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)})", 'INSERT'
            return f"INSERT INTO {table_name}", 'INSERT'
        
        elif method_lower.startswith(('update', 'modify', 'edit', 'change')):
            if parameters:
                set_clause = [f"{self.camel_to_snake(p['name'])} = #{{{p['name']}}}" for p in parameters if p['name'].lower() != 'id']
                if set_clause:
                    return f"UPDATE {table_name} SET {', '.join(set_clause)}", 'UPDATE'
            return f"UPDATE {table_name} SET", 'UPDATE'
        
        elif method_lower.startswith(('delete', 'remove', 'erase')):
            return f"DELETE FROM {table_name}", 'DELETE'
        
        # SELECT查询
        where_conditions = []
        
        # 查找各种LINQ模式
        # 1. FirstOrDefault(u => u.Id == id)
        pattern1 = r'FirstOrDefault\s*\(\s*\w+\s*=>\s*([^,]+?)\s*\)'
        match = re.search(pattern1, method_body)
        if match:
            condition = match.group(1)
            where_conditions.append(self.convert_condition(condition, parameters))
        
        # 2. Where(u => u.Name == name).ToList()
        pattern2 = r'Where\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)'
        match = re.search(pattern2, method_body)
        if match:
            condition = match.group(1)
            where_conditions.append(self.convert_condition(condition, parameters))
        
        # 3. SingleOrDefault(u => u.Id == id)
        pattern3 = r'SingleOrDefault\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)'
        match = re.search(pattern3, method_body)
        if match:
            condition = match.group(1)
            where_conditions.append(self.convert_condition(condition, parameters))
        
        # 4. Count()
        if re.search(r'\.Count\s*\(\s*\)', method_body):
            return f"SELECT COUNT(*) FROM {table_name}", 'SELECT'
        
        # 5. Any(u => u.Id == id)
        pattern5 = r'Any\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)'
        match = re.search(pattern5, method_body)
        if match:
            condition = match.group(1)
            where_conditions.append(self.convert_condition(condition, parameters))
            return f"SELECT COUNT(1) FROM {table_name} WHERE {' AND '.join(where_conditions)}", 'SELECT'
        
        # 根据方法名生成条件
        if not where_conditions:
            # 解析方法名 GetUserById, FindUserByName, GetByUserName
            patterns = [
                r'(?:get|find)(\w+)By(\w+)',
                r'(?:get|find)By(\w+)',
                r'(?:get|find)(\w+)',
            ]
            
            for pat in patterns:
                by_match = re.search(pat, method_name, re.IGNORECASE)
                if by_match:
                    groups = [g for g in by_match.groups() if g]
                    if groups:
                        field_part = groups[-1]
                        if field_part:
                            field_name = field_part
                            param_name = field_name[0].lower() + field_name[1:]
                            snake_field = self.camel_to_snake(field_name)
                            where_conditions.append(f"{snake_field} = #{{{param_name}}}")
                    break
        
        # 构建SQL
        if where_conditions:
            where_sql = ' AND '.join(where_conditions)
            # 检查是否是分页查询
            if 'page' in method_lower or 'paging' in method_lower:
                return f"SELECT * FROM {table_name} WHERE {where_sql} LIMIT #{{offset}}, #{{pageSize}}", 'SELECT'
            return f"SELECT * FROM {table_name} WHERE {where_sql}", 'SELECT'
        
        # 检查是否是获取所有
        if 'getall' in method_lower or 'findall' in method_lower or 'list' in method_lower:
            return f"SELECT * FROM {table_name}", 'SELECT'
        
        # 默认
        return f"SELECT * FROM {table_name}", 'SELECT'

    def convert_condition(self, condition: str, parameters: List[Dict]) -> str:
        """转换C#条件为SQL条件"""
        sql = condition
        
        # 替换运算符
        sql = re.sub(r'==', '=', sql)
        sql = re.sub(r'!=', '!=', sql)
        sql = re.sub(r'&&', 'AND', sql)
        sql = re.sub(r'\|\|', 'OR', sql)
        sql = re.sub(r'!', 'NOT ', sql)
        
        # 处理字符串方法
        sql = re.sub(r'\.Contains\(([^)]+)\)', r'LIKE CONCAT(\'%\', \1, \'%\')', sql)
        sql = re.sub(r'\.StartsWith\(([^)]+)\)', r'LIKE CONCAT(\1, \'%\')', sql)
        sql = re.sub(r'\.EndsWith\(([^)]+)\)', r'LIKE CONCAT(\'%\', \1)', sql)
        sql = re.sub(r'\.ToLower\(\)', 'LOWER', sql)
        sql = re.sub(r'\.ToUpper\(\)', 'UPPER', sql)
        
        # 移除lambda参数
        sql = re.sub(r'\w+\s*=>\s*', '', sql)
        
        # 转换字段名
        def replace_field(match):
            field = match.group(2) if match.group(2) else match.group(1)
            return self.camel_to_snake(field)
        
        sql = re.sub(r'(\w+)\.(\w+)', replace_field, sql)
        
        # 替换参数
        for param in parameters:
            sql = re.sub(rf'\b{param["name"]}\b', f'#{{{param["name"]}}}', sql)
        
        return sql

    def infer_table_name(self, method_name: str) -> str:
        """推断表名"""
        method_lower = method_name.lower()
        
        # 常见表名映射
        table_mappings = {
            'user': 'user', 'users': 'user',
            'order': 'orders', 'orders': 'orders',
            'product': 'product', 'products': 'product',
            'customer': 'customer', 'customers': 'customer',
            'employee': 'employee', 'employees': 'employee',
            'role': 'role', 'roles': 'role',
            'permission': 'permission', 'permissions': 'permission',
            'menu': 'menu', 'menus': 'menu',
            'log': 'log', 'logs': 'log'
        }
        
        for keyword, table in table_mappings.items():
            if keyword in method_lower:
                return table
        
        # 从方法名提取实体名
        entity_match = re.search(r'(?:get|find|insert|update|delete|save|add|remove)([A-Z][a-z]+)', method_name)
        if entity_match:
            entity = entity_match.group(1)
            return self.camel_to_snake(entity)
        
        return 'table_name'

    def map_to_java_type(self, csharp_type: str) -> str:
        """将C#类型映射到Java类型"""
        # 处理泛型
        if '<' in csharp_type:
            base_type = csharp_type[:csharp_type.index('<')]
            inner_type = csharp_type[csharp_type.index('<')+1:csharp_type.rindex('>')]
            
            if base_type in ['List', 'IEnumerable', 'ICollection', 'IList']:
                return f'List<{self.map_to_java_type(inner_type)}>'
            elif base_type == 'Dictionary' or base_type == 'IDictionary':
                return f'Map<{self.map_to_java_type(inner_type.split(",")[0].strip())}, {self.map_to_java_type(inner_type.split(",")[1].strip())}>'
            elif base_type == 'Task':
                return self.map_to_java_type(inner_type)
        
        # 基本类型映射
        base_type = csharp_type.rstrip('?')
        java_type = self.csharp_to_java_type.get(base_type, base_type)
        
        # 如果是自定义类型，首字母大写
        if java_type not in self.csharp_to_java_type.values() and java_type != 'void':
            java_type = java_type[0].upper() + java_type[1:] if java_type else java_type
        
        return java_type

    def convert_method_name(self, method_name: str) -> str:
        """方法名首字母小写"""
        if not method_name:
            return method_name
        return method_name[0].lower() + method_name[1:] if method_name[0].isupper() else method_name

    def convert_return_type(self, method: Dict, entity_name: str) -> Tuple[str, bool]:
        """转换返回类型"""
        return_type = method['return_type']
        
        # 检查是否是集合类型
        is_collection = any(x in return_type for x in ['List', 'IEnumerable', 'ICollection', 'IList'])
        
        if is_collection:
            inner_match = re.search(r'<(\w+)>', return_type)
            if inner_match:
                inner_type = inner_match.group(1)
                if inner_type == entity_name or inner_type == entity_name + '?':
                    return f'List<{entity_name}>', True
                else:
                    java_inner = self.map_to_java_type(inner_type)
                    return f'List<{java_inner}>', True
            return f'List<{entity_name}>', True
        
        # 处理单个实体
        if return_type == entity_name or return_type == entity_name + '?':
            return entity_name, False
        
        # 处理void
        if return_type.lower() in ['void', 'task']:
            return 'void', False
        
        # 处理值类型
        java_type = self.map_to_java_type(return_type)
        return java_type, False

    def generate_java_comment(self, comments: Dict, method_name: str, parameters: List[Dict], return_type: str) -> str:
        """生成Java注释"""
        java_lines = ["    /**"]
        
        # 添加summary
        if comments.get('summary'):
            java_lines.append(f"     * {comments['summary']}")
        else:
            java_lines.append(f"     * {method_name}")
        
        java_lines.append("     *")
        
        # 添加@param
        for param in parameters:
            param_name = param['name']
            param_desc = comments.get('params', {}).get(param_name, "")
            java_lines.append(f"     * @param {param_name} {param_desc}")
        
        # 添加@return
        if return_type != 'void':
            returns_desc = comments.get('returns', "")
            if returns_desc:
                java_lines.append(f"     * @return {return_type} {returns_desc}")
            else:
                java_lines.append(f"     * @return {return_type}")
        
        java_lines.append("     */")
        
        return '\n'.join(java_lines)

    def generate_mapper_java(self, dao_info: Dict, entity_name: str = None) -> Tuple[str, str, str, str]:
        """生成Java Mapper接口"""
        class_name = dao_info['class_name']
        
        # 生成包名
        package_name = 'mapper'
        if dao_info['namespace']:
            parts = dao_info['namespace'].lower().split('.')
            if len(parts) > 1:
                package_name = '.'.join(parts[:-1]) + '.mapper'
            else:
                package_name = 'mapper'
        
        # 生成Mapper名称
        mapper_name = class_name
        for suffix in ['DAO', 'Dao', 'Repository', 'DAL']:
            if mapper_name.endswith(suffix):
                mapper_name = mapper_name[:-len(suffix)]
                break
        mapper_name += 'Mapper'
        
        # 确定实体类名
        if not entity_name:
            entity_name = class_name
            for suffix in ['DAO', 'Dao', 'Repository', 'DAL']:
                if entity_name.endswith(suffix):
                    entity_name = entity_name[:-len(suffix)]
                    break
        
        # 生成导入语句
        imports = set()
        imports.add('org.apache.ibatis.annotations.Mapper')
        imports.add('org.apache.ibatis.annotations.Param')
        
        for method in dao_info['methods']:
            return_type, is_collection = self.convert_return_type(method, entity_name)
            if is_collection or 'List<' in return_type:
                imports.add('java.util.List')
            elif 'Map<' in return_type:
                imports.add('java.util.Map')
            
            for param in method['parameters']:
                java_type = param['java_type']
                if java_type == 'Date':
                    imports.add('java.util.Date')
                elif java_type == 'BigDecimal':
                    imports.add('java.math.BigDecimal')
        
        if entity_name and entity_name not in ['Object', 'void']:
            imports.add(f'entity.{entity_name}')
        
        import_lines = '\n'.join([f'import {imp};' for imp in sorted(imports)])
        
        # 类注释
        class_comment = ""
        if dao_info.get('class_comments'):
            class_comment = f"""
/**
 * {dao_info['class_comments']}
 */"""
        
        java_code = f"""package {package_name};
{import_lines}
{class_comment}
@Mapper
public interface {mapper_name} {{

"""
        
        # 生成方法
        for method in dao_info['methods']:
            method_name = self.convert_method_name(method['name'])
            return_type, _ = self.convert_return_type(method, entity_name)
            
            method_comment = self.generate_java_comment(
                method.get('comments', {}),
                method_name,
                method['parameters'],
                return_type
            )
            
            params = []
            for param in method['parameters']:
                params.append(f"@Param(\"{param['name']}\") {param['java_type']} {param['name']}")
            
            param_str = ', '.join(params) if params else ''
            
            method_code = f"""
{method_comment}
    {return_type} {method_name}({param_str});
"""
            java_code += method_code + "\n"
        
        java_code += "}\n"
        return java_code, mapper_name, entity_name, package_name

    def generate_mapper_xml(self, dao_info: Dict, mapper_name: str, entity_name: str, table_name: str = None) -> str:
        """生成MyBatis XML"""
        if not table_name:
            table_name = self.camel_to_snake(entity_name)
        
        package_name = 'mapper'
        if dao_info['namespace']:
            parts = dao_info['namespace'].lower().split('.')
            if len(parts) > 1:
                package_name = '.'.join(parts[:-1]) + '.mapper'
            else:
                package_name = 'mapper'
        
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="{package_name}.{mapper_name}">

    <sql id="Base_Column_List">
        <!-- TODO: id, name, create_time -->
    </sql>

'''
        
        for method in dao_info['methods']:
            sql_id = self.convert_method_name(method['name'])
            sql_type = method['sql_type']
            sql_statement = method.get('sql_statement', '')
            
            if sql_type == 'SELECT':
                xml += self.generate_select_sql(sql_id, method, table_name, entity_name, sql_statement)
            elif sql_type == 'INSERT':
                xml += self.generate_insert_sql(sql_id, method, table_name, sql_statement)
            elif sql_type == 'UPDATE':
                xml += self.generate_update_sql(sql_id, method, table_name, sql_statement)
            elif sql_type == 'DELETE':
                xml += self.generate_delete_sql(sql_id, method, table_name, sql_statement)
        
        xml += '</mapper>\n'
        return xml

    def generate_select_sql(self, sql_id: str, method: Dict, table_name: str, entity_name: str, sql_statement: str) -> str:
        """生成SELECT语句"""
        method_lower = method['name'].lower()
        
        # 确定返回类型
        if 'count' in method_lower or 'total' in method_lower:
            result_type = 'int'
        elif 'exists' in method_lower:
            result_type = 'int'
        else:
            result_type = entity_name
        
        if sql_statement:
            return f'''    <select id="{sql_id}" resultType="{result_type}">
        {sql_statement}
    </select>

'''
        
        # 默认SQL
        if method['parameters']:
            conditions = []
            for param in method['parameters']:
                conditions.append(f"            <if test=\"{param['name']} != null\">\n                AND {self.camel_to_snake(param['name'])} = #{{{param['name']}}}\n            </if>")
            where_clause = "\n".join(conditions)
            
            return f'''    <select id="{sql_id}" resultType="{result_type}">
        SELECT * FROM {table_name}
        <where>
{where_clause}
        </where>
    </select>

'''
        
        return f'''    <select id="{sql_id}" resultType="{result_type}">
        SELECT * FROM {table_name}
    </select>

'''

    def generate_insert_sql(self, sql_id: str, method: Dict, table_name: str, sql_statement: str) -> str:
        """生成INSERT语句"""
        if sql_statement and sql_statement.startswith('INSERT'):
            return f'''    <insert id="{sql_id}" useGeneratedKeys="true" keyProperty="id">
        {sql_statement}
    </insert>

'''
        
        params = method['parameters']
        if params:
            columns = [self.camel_to_snake(p['name']) for p in params]
            values = [f"#{{{p['name']}}}" for p in params]
            return f'''    <insert id="{sql_id}" useGeneratedKeys="true" keyProperty="id">
        INSERT INTO {table_name} ({', '.join(columns)})
        VALUES ({', '.join(values)})
    </insert>

'''
        
        return f'''    <insert id="{sql_id}" useGeneratedKeys="true" keyProperty="id">
        INSERT INTO {table_name}
        <!-- TODO -->
    </insert>

'''

    def generate_update_sql(self, sql_id: str, method: Dict, table_name: str, sql_statement: str) -> str:
        """生成UPDATE语句"""
        if sql_statement and sql_statement.startswith('UPDATE'):
            return f'''    <update id="{sql_id}">
        {sql_statement}
        WHERE id = #{{id}}
    </update>

'''
        
        params = method['parameters']
        if params:
            set_clause = []
            for param in params:
                if param['name'].lower() != 'id':
                    set_clause.append(f"            {self.camel_to_snake(param['name'])} = #{{{param['name']}}},")
            
            set_str = '\n'.join(set_clause) if set_clause else "            -- TODO"
            return f'''    <update id="{sql_id}">
        UPDATE {table_name}
        <set>
{set_str}
        </set>
        WHERE id = #{{id}}
    </update>

'''
        
        return f'''    <update id="{sql_id}">
        UPDATE {table_name}
        <!-- TODO -->
        WHERE id = #{{id}}
    </update>

'''

    def generate_delete_sql(self, sql_id: str, method: Dict, table_name: str, sql_statement: str) -> str:
        """生成DELETE语句"""
        if sql_statement and sql_statement.startswith('DELETE'):
            return f'''    <delete id="{sql_id}">
        {sql_statement}
    </delete>

'''
        
        return f'''    <delete id="{sql_id}">
        DELETE FROM {table_name}
        WHERE id = #{{id}}
    </delete>

'''

    def camel_to_snake(self, name: str) -> str:
        """驼峰转下划线"""
        if not name:
            return name
        
        name = name[0].lower() + name[1:] if name[0].isupper() else name
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def convert_file(self, input_file: str, output_dir: str = "./output", 
                    entity_name: str = None, table_name: str = None,
                    preserve_structure: bool = False, base_path: str = None) -> bool:
        """转换单个文件"""
        try:
            print(f"  读取: {os.path.basename(input_file)}")
            
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            dao_info = self.parse_csharp_dao(content)
            
            if not dao_info['class_name']:
                print(f"  ⚠️ 无法解析类名")
                return False
            
            method_count = len(dao_info['methods'])
            print(f"  类: {dao_info['class_name']}, 方法数: {method_count}")
            
            if method_count == 0:
                print(f"  ⚠️ 未找到方法")
                return False
            
            # 输出目录
            if preserve_structure and base_path:
                rel_path = os.path.relpath(input_file, base_path)
                output_subdir = os.path.dirname(rel_path)
                java_dir = os.path.join(output_dir, "java", output_subdir)
                xml_dir = os.path.join(output_dir, "xml", output_subdir)
            else:
                java_dir = os.path.join(output_dir, "java")
                xml_dir = os.path.join(output_dir, "xml")
            
            Path(java_dir).mkdir(parents=True, exist_ok=True)
            Path(xml_dir).mkdir(parents=True, exist_ok=True)
            
            # 生成文件
            java_code, mapper_name, auto_entity, _ = self.generate_mapper_java(dao_info, entity_name)
            xml_code = self.generate_mapper_xml(dao_info, mapper_name, auto_entity, table_name)
            
            java_file = os.path.join(java_dir, f"{mapper_name}.java")
            xml_file = os.path.join(xml_dir, f"{mapper_name}.xml")
            
            with open(java_file, 'w', encoding='utf-8') as f:
                f.write(java_code)
            
            with open(xml_file, 'w', encoding='utf-8') as f:
                f.write(xml_code)
            
            print(f"  ✅ 成功: {mapper_name} ({method_count}个方法)")
            return True
            
        except Exception as e:
            print(f"  ❌ 失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def convert_folder(self, input_folder: str, output_dir: str = "./output",
                      entity_name: str = None, table_name: str = None,
                      preserve_structure: bool = False):
        """转换文件夹"""
        print(f"\n{'='*60}")
        print("C# LINQ -> Java MyBatis Mapper 转换工具")
        print(f"输入: {input_folder}")
        print(f"输出: {output_dir}")
        print(f"{'='*60}\n")
        
        dao_files = self.find_dao_files(input_folder)
        
        if not dao_files:
            print("❌ 未找到DAO文件")
            return
        
        print(f"找到 {len(dao_files)} 个文件\n")
        
        success = 0
        total_methods = 0
        
        for i, f in enumerate(dao_files, 1):
            print(f"[{i}/{len(dao_files)}] {Path(f).name}")
            if self.convert_file(f, output_dir, entity_name, table_name, preserve_structure, input_folder):
                success += 1
            print()
        
        print(f"{'='*60}")
        print(f"完成! 成功: {success}, 失败: {len(dao_files)-success}")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description='C# LINQ DAO 转 Java MyBatis Mapper')
    parser.add_argument('-i', '--input', required=True, help='输入文件或文件夹')
    parser.add_argument('-o', '--output', default='./mybatis_output', help='输出目录')
    parser.add_argument('-e', '--entity', help='实体类名')
    parser.add_argument('-t', '--table', help='表名')
    parser.add_argument('-s', '--preserve-structure', action='store_true', help='保持目录结构')
    
    args = parser.parse_args()
    
    converter = LinqToMyBatisConverter()
    
    if os.path.isfile(args.input):
        converter.convert_file(args.input, args.output, args.entity, args.table)
    elif os.path.isdir(args.input):
        converter.convert_folder(args.input, args.output, args.entity, args.table, args.preserve_structure)
    else:
        print(f"路径不存在: {args.input}")


if __name__ == "__main__":
    main()
