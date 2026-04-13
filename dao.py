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
            # 值类型
            'int': 'Integer',
            'int?': 'Integer',
            'long': 'Long',
            'long?': 'Long',
            'short': 'Short',
            'short?': 'Short',
            'byte': 'Byte',
            'byte?': 'Byte',
            'bool': 'Boolean',
            'bool?': 'Boolean',
            'boolean': 'Boolean',
            'float': 'Float',
            'float?': 'Float',
            'double': 'Double',
            'double?': 'Double',
            'decimal': 'BigDecimal',
            'decimal?': 'BigDecimal',
            
            # 字符串
            'string': 'String',
            'char': 'String',
            'char?': 'String',
            
            # 日期时间
            'DateTime': 'Date',
            'DateTime?': 'Date',
            'TimeSpan': 'String',
            'TimeSpan?': 'String',
            
            # 其他
            'Guid': 'String',
            'Guid?': 'String',
            'object': 'Object',
            'void': 'void',
            'Task': 'void'
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
                if any(keyword in cs_file.stem for keyword in ['DAO', 'Dao', 'Repository', 'DAL', 'Service']):
                    dao_files.append(str(cs_file))
                else:
                    try:
                        with open(cs_file, 'r', encoding='utf-8') as f:
                            content = f.read(2000)
                            if re.search(r'from\s+\w+\s+in\s+\w+|\.Where\(|\.Select\(|\.FirstOrDefault\(', content):
                                dao_files.append(str(cs_file))
                    except:
                        pass
        
        return dao_files

    def extract_method_comments(self, method_text: str) -> Dict[str, str]:
        """提取C#方法中的注释，返回{summary: '', params: {}, returns: ''}"""
        result = {
            'summary': '',
            'params': {},
            'returns': ''
        }
        
        # 提取summary
        summary_match = re.search(r'///\s*<summary>\s*(.*?)\s*</summary>', method_text, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
            # 去除多余的换行和空格
            summary = re.sub(r'\s+', ' ', summary)
            result['summary'] = summary
        else:
            # 尝试提取普通注释
            single_comment = re.search(r'//\s*(.+?)(?=\n)', method_text)
            if single_comment:
                result['summary'] = single_comment.group(1).strip()
        
        # 提取所有param
        param_pattern = r'///\s*<param\s+name="(\w+)">\s*(.*?)\s*</param>'
        for match in re.finditer(param_pattern, method_text, re.DOTALL):
            param_name = match.group(1)
            param_desc = re.sub(r'\s+', ' ', match.group(2).strip())
            result['params'][param_name] = param_desc
        
        # 提取returns
        returns_match = re.search(r'///\s*<returns>\s*(.*?)\s*</returns>', method_text, re.DOTALL)
        if returns_match:
            returns_desc = re.sub(r'\s+', ' ', returns_match.group(1).strip())
            result['returns'] = returns_desc
        
        return result

    def parse_csharp_dao(self, file_content: str) -> Dict:
        """解析C# DAO文件，提取类名、方法、注释和LINQ查询"""
        result = {
            'namespace': '',
            'class_name': '',
            'class_comments': '',
            'methods': [],
            'usings': []
        }
        
        # 提取using语句
        using_matches = re.findall(r'using\s+([\w.]+);', file_content)
        result['usings'] = using_matches
        
        # 提取namespace
        ns_match = re.search(r'namespace\s+([\w.]+)', file_content)
        if ns_match:
            result['namespace'] = ns_match.group(1)
        
        # 提取类名和类注释
        class_match = re.search(r'((?:///\s*<summary>.*?</summary>|///\s*<remarks>.*?</remarks>|//.*?\n|/\*\*.*?\*/)*?)\s*(?:public|internal|private)?\s*(?:static\s+)?(?:partial\s+)?class\s+(\w+)', 
                                file_content, re.DOTALL)
        if class_match:
            comment_text = class_match.group(1)
            result['class_name'] = class_match.group(2)
            if comment_text:
                summary_match = re.search(r'<summary>(.*?)</summary>', comment_text, re.DOTALL)
                if summary_match:
                    result['class_comments'] = re.sub(r'\s+', ' ', summary_match.group(1).strip())
        else:
            simple_class_match = re.search(r'class\s+(\w+)', file_content)
            if simple_class_match:
                result['class_name'] = simple_class_match.group(1)
        
        # 提取方法 - 改进正则表达式以正确捕获注释
        # 先按方法分割
        method_pattern = r'''
            (?:(?:///.*?\n|//.*?\n|/\*.*?\*/)\s*)*
            (?:public|private|protected|internal)\s+
            (?:static\s+)?
            (?:virtual\s+)?
            (?:override\s+)?
            (?:async\s+)?
            (?:Task<)?
            (\w+(?:<[^>]+>)?)
            (?:>)?
            \s+(\w+)\s*
            \(([^)]*)\)
            \s*
            \{
            (.*?)
            \n\s*\}
        '''
        
        methods = re.finditer(method_pattern, file_content, re.VERBOSE | re.DOTALL)
        
        for method in methods:
            return_type = method.group(1)
            method_name = method.group(2)
            parameters_str = method.group(3)
            method_body = method.group(4)
            
            # 跳过构造函数
            if method_name == result['class_name']:
                continue
            
            # 提取方法前的注释
            # 找到方法在原文中的位置
            method_start = method.start()
            # 向前查找注释
            comment_text = ""
            if method_start > 0:
                before_method = file_content[max(0, method_start - 500):method_start]
                # 查找连续的行注释或XML注释
                comment_lines = []
                lines = before_method.split('\n')
                for line in reversed(lines):
                    if line.strip().startswith('///') or line.strip().startswith('//') or line.strip().startswith('/*'):
                        comment_lines.insert(0, line)
                    elif line.strip() and not line.strip().startswith('['):  # 不是属性
                        break
                comment_text = '\n'.join(comment_lines)
            
            method_comments = self.extract_method_comments(comment_text)
            
            # 解析参数
            parameters = self.parse_parameters(parameters_str)
            
            # 提取LINQ查询并生成SQL
            sql_statement = self.generate_sql_from_method(method_body, method_name, parameters)
            
            # 推断SQL操作类型
            sql_type = self.infer_sql_type(method_name, method_body)
            
            result['methods'].append({
                'name': method_name,
                'return_type': return_type,
                'parameters': parameters,
                'sql_type': sql_type,
                'sql_statement': sql_statement,
                'comments': method_comments
            })
        
        return result

    def parse_parameters(self, params_str: str) -> List[Dict]:
        """解析方法参数"""
        if not params_str or params_str.strip() == '':
            return []
        
        parameters = []
        param_parts = []
        current_param = ""
        bracket_count = 0
        
        for char in params_str:
            if char == '<':
                bracket_count += 1
            elif char == '>':
                bracket_count -= 1
            elif char == ',' and bracket_count == 0:
                param_parts.append(current_param.strip())
                current_param = ""
                continue
            current_param += char
        
        if current_param:
            param_parts.append(current_param.strip())
        
        for param in param_parts:
            if not param:
                continue
            
            match = re.match(r'(?:\[.*?\])?\s*(\w+(?:<[^>]+>)?(?:\?)?)\s+(\w+)(?:\s*=.*)?', param)
            if match:
                param_type = match.group(1)
                param_name = match.group(2)
                java_type = self.map_to_java_type(param_type)
                
                parameters.append({
                    'csharp_type': param_type,
                    'java_type': java_type,
                    'name': param_name
                })
        
        return parameters

    def generate_sql_from_method(self, method_body: str, method_name: str, parameters: List[Dict]) -> str:
        """从方法体和LINQ查询生成SQL语句"""
        method_lower = method_name.lower()
        
        # 查找Entity Framework的LINQ模式
        linq_patterns = [
            # _context.Users.Where(u => u.Id == id).FirstOrDefault()
            r'_context\.(\w+)\.Where\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)\s*\.(FirstOrDefault|First|SingleOrDefault|ToList|ToArray)',
            # _context.Users.FirstOrDefault(u => u.Id == id)
            r'_context\.(\w+)\.(FirstOrDefault|First|SingleOrDefault)\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)',
            # from u in _context.Users where u.Id == id select u
            r'from\s+(\w+)\s+in\s+_context\.(\w+)\s+where\s+([^\s]+)\s*==\s*([^\s]+)\s+select\s+\1',
            # _context.Users.Where(u => u.Name.Contains(name)).ToList()
            r'_context\.(\w+)\.Where\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)\s*\.ToList',
            # _context.Users.Count()
            r'_context\.(\w+)\.Count\s*\(\s*\)',
            # _context.Users.Any(u => u.Id == id)
            r'_context\.(\w+)\.Any\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)',
        ]
        
        table_name = self.infer_table_name(method_name)
        where_conditions = []
        is_count = False
        is_any = False
        
        for pattern in linq_patterns:
            match = re.search(pattern, method_body)
            if match:
                if pattern == r'_context\.(\w+)\.Count\s*\(\s*\)':
                    is_count = True
                    table_name = self.camel_to_snake(match.group(1))
                    break
                elif pattern == r'_context\.(\w+)\.Any\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)':
                    is_any = True
                    table_name = self.camel_to_snake(match.group(1))
                    condition = match.group(2)
                    where_conditions.append(self.convert_condition_to_sql(condition, parameters))
                    break
                elif 'Where' in pattern:
                    if len(match.groups()) >= 2:
                        table_name = self.camel_to_snake(match.group(1))
                        condition = match.group(2)
                        where_conditions.append(self.convert_condition_to_sql(condition, parameters))
                        break
                elif 'FirstOrDefault' in pattern or 'First' in pattern:
                    if len(match.groups()) >= 3:
                        table_name = self.camel_to_snake(match.group(1))
                        condition = match.group(3)
                        where_conditions.append(self.convert_condition_to_sql(condition, parameters))
                        break
                elif pattern == r'from\s+(\w+)\s+in\s+_context\.(\w+)\s+where\s+([^\s]+)\s*==\s*([^\s]+)\s+select\s+\1':
                    table_name = self.camel_to_snake(match.group(2))
                    left = match.group(3)
                    right = match.group(4)
                    # 转换字段名
                    left_field = self.camel_to_snake(left.split('.')[-1] if '.' in left else left)
                    where_conditions.append(f"{left_field} = #{{{right}}}")
                    break
        
        # 如果没有找到LINQ模式，根据方法名生成SQL
        if not where_conditions and not is_count and not is_any:
            # 解析方法名如 GetUserById, FindUserByName
            if 'get' in method_lower or 'find' in method_lower:
                # 提取条件字段
                condition_match = re.search(r'(?:get|find)(\w+)(?:by)?(\w*)', method_name, re.IGNORECASE)
                if condition_match:
                    entity_part = condition_match.group(1)
                    field_part = condition_match.group(2)
                    if field_part:
                        field_name = field_part
                        param_name = field_part[0].lower() + field_part[1:] if field_part else field_part
                    else:
                        field_name = 'id'
                        param_name = 'id'
                    
                    snake_field = self.camel_to_snake(field_name)
                    where_conditions.append(f"{snake_field} = #{{{param_name}}}")
            
            # 处理count查询
            if 'count' in method_lower:
                is_count = True
        
        # 构建SQL语句
        if is_count:
            return f"SELECT COUNT(*) FROM {table_name}"
        
        if is_any:
            where_sql = ' AND '.join(where_conditions) if where_conditions else '1=1'
            return f"SELECT 1 FROM {table_name} WHERE {where_sql} LIMIT 1"
        
        if where_conditions:
            where_sql = ' AND '.join(where_conditions)
            return f"SELECT * FROM {table_name} WHERE {where_sql}"
        
        # 默认查询所有
        if 'getall' in method_lower or 'findall' in method_lower:
            return f"SELECT * FROM {table_name}"
        
        # 插入操作
        if 'insert' in method_lower or 'add' in method_lower:
            return f"INSERT INTO {table_name}"
        
        # 更新操作
        if 'update' in method_lower:
            return f"UPDATE {table_name} SET"
        
        # 删除操作
        if 'delete' in method_lower or 'remove' in method_lower:
            return f"DELETE FROM {table_name}"
        
        return f"SELECT * FROM {table_name}"

    def convert_condition_to_sql(self, condition: str, parameters: List[Dict]) -> str:
        """将C#条件表达式转换为SQL WHERE条件"""
        sql = condition
        
        # 处理相等比较
        sql = re.sub(r'==', '=', sql)
        sql = re.sub(r'!=', '!=', sql)
        
        # 处理字符串方法
        sql = re.sub(r'\.Contains\(([^)]+)\)', r'LIKE CONCAT(\'%\', \1, \'%\')', sql)
        sql = re.sub(r'\.StartsWith\(([^)]+)\)', r'LIKE CONCAT(\1, \'%\')', sql)
        sql = re.sub(r'\.EndsWith\(([^)]+)\)', r'LIKE CONCAT(\'%\', \1)', sql)
        
        # 处理lambda表达式参数 (u => u.Id == id)
        sql = re.sub(r'\w+\s*=>\s*', '', sql)
        
        # 转换字段名 (Id -> id, UserName -> user_name)
        def replace_field(match):
            field = match.group(1)
            return self.camel_to_snake(field)
        
        sql = re.sub(r'(\w+)\.(\w+)', lambda m: f"{self.camel_to_snake(m.group(2))}", sql)
        
        # 替换参数为MyBatis格式
        for param in parameters:
            sql = re.sub(rf'\b{param["name"]}\b', f'#{{{param["name"]}}}', sql)
        
        return sql

    def infer_table_name(self, method_name: str) -> str:
        """推断表名"""
        method_lower = method_name.lower()
        
        table_mappings = {
            'user': 'user',
            'users': 'user',
            'order': 'orders',
            'orders': 'orders',
            'product': 'product',
            'products': 'product',
            'customer': 'customer',
            'customers': 'customer',
            'employee': 'employee',
            'employees': 'employee'
        }
        
        for keyword, table in table_mappings.items():
            if keyword in method_lower:
                return table
        
        return 'table_name'

    def infer_sql_type(self, method_name: str, method_body: str) -> str:
        """推断SQL操作类型"""
        method_lower = method_name.lower()
        
        if any(method_lower.startswith(prefix) for prefix in ['get', 'select', 'find', 'query', 'fetch']):
            return 'SELECT'
        elif any(method_lower.startswith(prefix) for prefix in ['insert', 'add', 'create', 'save']):
            return 'INSERT'
        elif any(method_lower.startswith(prefix) for prefix in ['update', 'modify', 'edit', 'change']):
            return 'UPDATE'
        elif any(method_lower.startswith(prefix) for prefix in ['delete', 'remove', 'erase']):
            return 'DELETE'
        
        if 'Count' in method_name or 'count' in method_lower:
            return 'SELECT'
        
        return 'SELECT'

    def map_to_java_type(self, csharp_type: str) -> str:
        """将C#类型映射到Java类型"""
        if '<' in csharp_type:
            base_type = csharp_type[:csharp_type.index('<')]
            inner_type = csharp_type[csharp_type.index('<')+1:csharp_type.rindex('>')]
            
            if base_type in ['List', 'IEnumerable', 'ICollection']:
                return f'List<{self.map_to_java_type(inner_type)}>'
            elif base_type == 'Dictionary':
                types = inner_type.split(',')
                if len(types) == 2:
                    return f'Map<{self.map_to_java_type(types[0].strip())}, {self.map_to_java_type(types[1].strip())}>'
        
        base_type = csharp_type.rstrip('?')
        java_type = self.csharp_to_java_type.get(base_type, base_type)
        
        return java_type

    def convert_method_name(self, method_name: str) -> str:
        """将C#方法名转换为Java方法名（首字母小写）"""
        if not method_name:
            return method_name
        
        if method_name[0].islower():
            return method_name
        
        return method_name[0].lower() + method_name[1:]

    def convert_return_type(self, method: Dict, entity_name: str) -> Tuple[str, bool]:
        """转换返回类型"""
        return_type = method['return_type']
        
        is_collection = any(x in return_type for x in ['List', 'IEnumerable', 'ICollection', 'IList'])
        
        if is_collection:
            inner_match = re.search(r'<(\w+)>', return_type)
            if inner_match:
                inner_type = inner_match.group(1)
                if inner_type == entity_name or inner_type == entity_name + '?':
                    return f'List<{entity_name}>', True
                else:
                    return f'List<{self.map_to_java_type(inner_type)}>', True
            return f'List<{entity_name}>', True
        
        if return_type == entity_name or return_type == entity_name + '?':
            return entity_name, False
        
        if return_type.lower() in ['void', 'task']:
            return 'void', False
        
        java_type = self.map_to_java_type(return_type)
        return java_type, False

    def generate_java_comment(self, comments: Dict, method_name: str, parameters: List[Dict], return_type: str) -> str:
        """生成Java注释，去除XML标签"""
        java_lines = ["    /**"]
        
        # 添加summary
        if comments.get('summary'):
            java_lines.append(f"     * {comments['summary']}")
        else:
            java_lines.append(f"     * {method_name}")
        
        java_lines.append("     *")
        
        # 添加@param标签
        for param in parameters:
            param_name = param['name']
            param_desc = comments.get('params', {}).get(param_name, "")
            java_lines.append(f"     * @param {param_name} {param_desc}")
        
        # 添加@return标签
        if return_type != 'void':
            returns_desc = comments.get('returns', "")
            if returns_desc:
                java_lines.append(f"     * @return {return_type} {returns_desc}")
            else:
                java_lines.append(f"     * @return {return_type}")
        
        java_lines.append("     */")
        
        return '\n'.join(java_lines)

    def generate_mapper_java(self, dao_info: Dict, entity_name: str = None) -> Tuple[str, str, str, str]:
        """生成Java Mapper接口代码"""
        class_name = dao_info['class_name']
        
        package_name = self.convert_namespace_to_package(dao_info['namespace'])
        
        mapper_name = class_name
        for suffix in ['DAO', 'Dao', 'Repository', 'DAL', 'Service']:
            if mapper_name.endswith(suffix):
                mapper_name = mapper_name[:-len(suffix)]
                break
        mapper_name += 'Mapper'
        
        if not entity_name:
            entity_name = class_name
            for suffix in ['DAO', 'Dao', 'Repository', 'DAL', 'Service']:
                if entity_name.endswith(suffix):
                    entity_name = entity_name[:-len(suffix)]
                    break
        
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
                if java_type in ['Date']:
                    imports.add('java.util.Date')
                elif java_type in ['BigDecimal']:
                    imports.add('java.math.BigDecimal')
        
        if entity_name and entity_name not in ['Object', 'void']:
            imports.add(f'entity.{entity_name}')
        
        import_lines = '\n'.join([f'import {imp};' for imp in sorted(imports)])
        
        # 生成类注释
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
        """生成MyBatis Mapper XML文件"""
        if not table_name:
            table_name = self.camel_to_snake(entity_name)
        
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="{self.convert_namespace_to_package(dao_info['namespace'])}.{mapper_name}">

    <!-- 基础字段列表 -->
    <sql id="Base_Column_List">
        <!-- TODO: 配置所有字段，例如: id, name, create_time -->
    </sql>

'''
        
        for method in dao_info['methods']:
            sql_id = self.convert_method_name(method['name'])
            sql_type = method['sql_type']
            sql_statement = method.get('sql_statement', '')
            
            if sql_type == 'SELECT':
                xml += self.generate_select_sql(sql_id, method, table_name, entity_name, sql_statement)
            elif sql_type == 'INSERT':
                xml += self.generate_insert_sql(sql_id, method, table_name)
            elif sql_type == 'UPDATE':
                xml += self.generate_update_sql(sql_id, method, table_name)
            elif sql_type == 'DELETE':
                xml += self.generate_delete_sql(sql_id, method, table_name)
        
        xml += '</mapper>\n'
        return xml

    def generate_select_sql(self, sql_id: str, method: Dict, table_name: str, entity_name: str, sql_statement: str) -> str:
        """生成SELECT语句"""
        method_name_lower = method['name'].lower()
        
        # 确定返回类型
        if 'count' in method_name_lower or 'total' in method_name_lower:
            result_type = 'int'
        elif 'exists' in method_name_lower or 'any' in method_name_lower:
            result_type = 'int'
        else:
            result_type = entity_name
        
        # 处理SQL语句
        if sql_statement:
            # 移除可能的多余空格
            sql_statement = sql_statement.strip()
            
            # 如果SQL以SELECT开头，直接使用
            if sql_statement.upper().startswith('SELECT'):
                return f'''    <select id="{sql_id}" resultType="{result_type}" parameterType="map">
        {sql_statement}
    </select>

'''
            # 如果只有WHERE条件
            elif sql_statement.upper().startswith('WHERE'):
                return f'''    <select id="{sql_id}" resultType="{result_type}" parameterType="map">
        SELECT * FROM {table_name}
        {sql_statement}
    </select>

'''
            # 其他情况，作为WHERE条件处理
            else:
                return f'''    <select id="{sql_id}" resultType="{result_type}" parameterType="map">
        SELECT * FROM {table_name}
        WHERE {sql_statement}
    </select>

'''
        
        # 默认生成带条件的SQL
        if method['parameters']:
            conditions = []
            for param in method['parameters']:
                conditions.append(f"            <if test=\"{param['name']} != null\">\n                AND {self.camel_to_snake(param['name'])} = #{{{param['name']}}}\n            </if>")
            where_clause = "        <where>\n" + "\n".join(conditions) + "\n        </where>"
            
            return f'''    <select id="{sql_id}" resultType="{result_type}" parameterType="map">
        SELECT * FROM {table_name}
{where_clause}
    </select>

'''
        
        return f'''    <select id="{sql_id}" resultType="{result_type}" parameterType="map">
        SELECT * FROM {table_name}
    </select>

'''

    def generate_insert_sql(self, sql_id: str, method: Dict, table_name: str) -> str:
        """生成INSERT语句"""
        params = method['parameters']
        
        if not params:
            return f'''    <insert id="{sql_id}">
        INSERT INTO {table_name}
        <!-- TODO: 配置插入字段 -->
    </insert>

'''
        
        columns = [self.camel_to_snake(p['name']) for p in params]
        values = [f"#{{{p['name']}}}" for p in params]
        
        return f'''    <insert id="{sql_id}" parameterType="map" useGeneratedKeys="true" keyProperty="id">
        INSERT INTO {table_name} (
            {', '.join(columns)}
        ) VALUES (
            {', '.join(values)}
        )
    </insert>

'''

    def generate_update_sql(self, sql_id: str, method: Dict, table_name: str) -> str:
        """生成UPDATE语句"""
        params = method['parameters']
        
        if not params:
            return f'''    <update id="{sql_id}">
        UPDATE {table_name}
        <set>
            <!-- TODO: 配置更新字段 -->
        </set>
        <!-- TODO: 配置WHERE条件 -->
    </update>

'''
        
        id_params = []
        update_params = []
        
        for param in params:
            if param['name'].lower() in ['id', 'ids', 'key', 'primarykey']:
                id_params.append(param)
            else:
                update_params.append(param)
        
        set_clause = []
        for param in update_params:
            set_clause.append(f"            <if test=\"{param['name']} != null\">\n                {self.camel_to_snake(param['name'])} = #{{{param['name']}}},\n            </if>")
        
        set_str = "\n".join(set_clause) if set_clause else "            <!-- TODO: 配置更新字段 -->"
        
        where_clause = ""
        if id_params:
            conditions = []
            for param in id_params:
                conditions.append(f"            AND {self.camel_to_snake(param['name'])} = #{{{param['name']}}}")
            where_clause = "        <where>\n" + "\n".join(conditions) + "\n        </where>"
        else:
            where_clause = "        <!-- TODO: 配置WHERE条件 -->"
        
        return f'''    <update id="{sql_id}" parameterType="map">
        UPDATE {table_name}
        <set>
{set_str}
        </set>
{where_clause}
    </update>

'''

    def generate_delete_sql(self, sql_id: str, method: Dict, table_name: str) -> str:
        """生成DELETE语句"""
        params = method['parameters']
        
        where_clause = ""
        if params:
            conditions = []
            for param in params:
                conditions.append(f"            <if test=\"{param['name']} != null\">\n                AND {self.camel_to_snake(param['name'])} = #{{{param['name']}}}\n            </if>")
            where_clause = "        <where>\n" + "\n".join(conditions) + "\n        </where>"
        else:
            where_clause = "        <!-- TODO: 配置WHERE条件 -->"
        
        return f'''    <delete id="{sql_id}" parameterType="map">
        DELETE FROM {table_name}
{where_clause}
    </delete>

'''

    def convert_namespace_to_package(self, namespace: str) -> str:
        """将C#命名空间转换为Java包名"""
        if not namespace:
            return "mapper"
        
        package = namespace.lower()
        package = package.replace('.', '.')
        
        if not package.endswith('mapper'):
            if '.' in package:
                package += '.mapper'
            else:
                package = 'mapper'
        
        return package

    def camel_to_snake(self, name: str) -> str:
        """驼峰命名转下划线命名"""
        if not name:
            return name
        
        # 处理首字母大写
        if name[0].isupper():
            name = name[0].lower() + name[1:]
        
        # 转换驼峰为下划线
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        result = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        
        return result

    def convert_file(self, input_file: str, output_dir: str = "./output", 
                    entity_name: str = None, table_name: str = None,
                    preserve_structure: bool = False, base_path: str = None) -> bool:
        """转换单个C# DAO文件"""
        try:
            print(f"  读取文件: {input_file}")
            
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            dao_info = self.parse_csharp_dao(content)
            
            if not dao_info['class_name']:
                print(f"  ⚠️  无法解析类名: {input_file}")
                return False
            
            if not dao_info['methods']:
                print(f"  ⚠️  未找到方法: {input_file}")
                return False
            
            print(f"  解析到 {len(dao_info['methods'])} 个方法")
            
            if preserve_structure and base_path:
                rel_path = os.path.relpath(input_file, base_path)
                output_subdir = os.path.dirname(rel_path)
                java_output_dir = os.path.join(output_dir, "java", output_subdir)
                xml_output_dir = os.path.join(output_dir, "xml", output_subdir)
            else:
                java_output_dir = os.path.join(output_dir, "java")
                xml_output_dir = os.path.join(output_dir, "xml")
            
            Path(java_output_dir).mkdir(parents=True, exist_ok=True)
            Path(xml_output_dir).mkdir(parents=True, exist_ok=True)
            
            java_code, mapper_name, auto_entity_name, package_name = self.generate_mapper_java(dao_info, entity_name)
            xml_code = self.generate_mapper_xml(dao_info, mapper_name, auto_entity_name, table_name)
            
            java_file = os.path.join(java_output_dir, f"{mapper_name}.java")
            xml_file = os.path.join(xml_output_dir, f"{mapper_name}.xml")
            
            with open(java_file, 'w', encoding='utf-8') as f:
                f.write(java_code)
            
            with open(xml_file, 'w', encoding='utf-8') as f:
                f.write(xml_code)
            
            print(f"  ✅ 转换成功: {Path(input_file).name} -> {mapper_name}")
            return True
            
        except Exception as e:
            print(f"  ❌ 转换失败: {input_file}")
            print(f"     错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def convert_folder(self, input_folder: str, output_dir: str = "./output",
                      entity_name: str = None, table_name: str = None,
                      recursive: bool = True, preserve_structure: bool = False):
        """转换文件夹中的所有C# DAO文件"""
        print(f"\n{'='*70}")
        print(f"  C# LINQ to SQL -> Java MyBatis Mapper 转换工具")
        print(f"{'='*70}")
        print(f"输入路径: {input_folder}")
        print(f"输出目录: {output_dir}")
        print(f"{'='*70}\n")
        
        dao_files = self.find_dao_files(input_folder)
        
        if not dao_files:
            print("❌ 未找到任何C# DAO文件")
            return
        
        print(f"找到 {len(dao_files)} 个C# DAO文件\n")
        
        success_count = 0
        fail_count = 0
        base_path = input_folder if preserve_structure else None
        
        for i, dao_file in enumerate(dao_files, 1):
            print(f"[{i}/{len(dao_files)}] 处理: {dao_file}")
            
            if self.convert_file(dao_file, output_dir, entity_name, table_name, 
                               preserve_structure, base_path):
                success_count += 1
            else:
                fail_count += 1
            print()
        
        print(f"{'='*70}")
        print(f"转换完成!")
        print(f"成功: {success_count} 个文件")
        print(f"失败: {fail_count} 个文件")
        print(f"输出目录: {output_dir}")
        print(f"{'='*70}\n")
        
        self.generate_summary_report(output_dir, success_count, fail_count)

    def generate_summary_report(self, output_dir: str, success_count: int, fail_count: int):
        """生成转换汇总报告"""
        report_path = os.path.join(output_dir, "conversion_report.txt")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("C# LINQ to SQL 转 Java MyBatis Mapper 转换报告\n")
            f.write("="*60 + "\n")
            f.write(f"转换时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"成功数量: {success_count}\n")
            f.write(f"失败数量: {fail_count}\n")
            f.write("="*60 + "\n\n")
            f.write("生成的Java Mapper接口和XML文件位于:\n")
            f.write(f"  Java文件: {os.path.join(output_dir, 'java')}\n")
            f.write(f"  XML文件: {os.path.join(output_dir, 'xml')}\n")
        
        print(f"📄 转换报告已生成: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description='将C# LINQ DAO转换为Java MyBatis Mapper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python linq_to_mybatis.py -i UserDAO.cs -o ./output
  python linq_to_mybatis.py -i ./CSharpProject/DAL -o ./mybatis
  python linq_to_mybatis.py -i ./CSharpProject -o ./mybatis -r -s
        """
    )
    
    parser.add_argument('-i', '--input', required=True, help='输入的C#文件或文件夹路径')
    parser.add_argument('-o', '--output', default='./mybatis_output', help='输出目录')
    parser.add_argument('-e', '--entity', help='实体类名')
    parser.add_argument('-t', '--table', help='数据库表名')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归搜索子文件夹')
    parser.add_argument('-s', '--preserve-structure', action='store_true', help='保持原始目录结构')
    
    args = parser.parse_args()
    
    converter = LinqToMyBatisConverter()
    
    if os.path.isfile(args.input):
        print(f"\n转换单个文件: {args.input}")
        converter.convert_file(args.input, args.output, args.entity, args.table)
    elif os.path.isdir(args.input):
        converter.convert_folder(args.input, args.output, args.entity, args.table, 
                               args.recursive, args.preserve_structure)
    else:
        print(f"错误: 路径不存在 - {args.input}")


if __name__ == "__main__":
    main()
