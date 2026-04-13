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
            'void': 'void', 'Task': 'void'
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

    def extract_comments_from_csharp(self, file_content: str, method_start_pos: int) -> Dict[str, str]:
        """从C#文件中提取方法前的注释"""
        result = {'summary': '', 'params': {}, 'returns': ''}
        
        # 向前查找注释
        start = max(0, method_start_pos - 1000)
        before_text = file_content[start:method_start_pos]
        
        # 查找最近的注释块
        lines = before_text.split('\n')
        comment_lines = []
        
        for line in reversed(lines):
            stripped = line.strip()
            if stripped.startswith('///'):
                comment_lines.insert(0, line)
            elif stripped.startswith('//') and not stripped.startswith('///'):
                comment_lines.insert(0, line)
            elif stripped.startswith('/*'):
                comment_lines.insert(0, line)
                break
            elif stripped and not stripped.startswith('[') and not stripped.startswith('using') and not stripped.startswith('namespace'):
                # 遇到非注释行，停止
                if comment_lines:
                    break
        
        if not comment_lines:
            return result
        
        comment_text = '\n'.join(comment_lines)
        
        # 提取summary - 处理多行情况
        summary_match = re.search(r'///\s*<summary>\s*(.*?)\s*</summary>', comment_text, re.DOTALL | re.IGNORECASE)
        if summary_match:
            summary = summary_match.group(1).strip()
            # 清理多余的空格和换行
            summary = re.sub(r'\s+', ' ', summary)
            result['summary'] = summary
        
        # 提取所有param
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
        """解析C# DAO文件"""
        result = {
            'namespace': '',
            'class_name': '',
            'class_comments': '',
            'methods': [],
            'usings': []
        }
        
        # 提取using
        using_matches = re.findall(r'using\s+([\w.]+);', file_content)
        result['usings'] = using_matches
        
        # 提取namespace
        ns_match = re.search(r'namespace\s+([\w.]+)', file_content)
        if ns_match:
            result['namespace'] = ns_match.group(1)
        
        # 提取类注释
        class_pattern = r'((?:///.*?\n|/\*\*.*?\*/)\s*)\s*(?:public|internal|private)?\s*class\s+(\w+)'
        class_match = re.search(class_pattern, file_content, re.DOTALL)
        if class_match:
            result['class_name'] = class_match.group(2)
            comment_text = class_match.group(1)
            if comment_text:
                summary_match = re.search(r'<summary>(.*?)</summary>', comment_text, re.DOTALL)
                if summary_match:
                    result['class_comments'] = re.sub(r'\s+', ' ', summary_match.group(1).strip())
        else:
            simple_match = re.search(r'class\s+(\w+)', file_content)
            if simple_match:
                result['class_name'] = simple_match.group(1)
        
        # 逐行解析方法
        lines = file_content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 方法匹配模式
            method_pattern = r'^(?:public|private|protected|internal)\s+(?:static\s+)?(?:virtual\s+)?(?:override\s+)?(?:async\s+)?(?:Task<)?(\w+(?:<[^>]+>)?)(?:>)?\s+(\w+)\s*\(([^)]*)\)'
            match = re.match(method_pattern, line)
            
            if match and match.group(2) != result['class_name']:
                return_type = match.group(1)
                method_name = match.group(2)
                params_str = match.group(3)
                
                # 计算方法在文件中的位置
                char_pos = sum(len(lines[j]) + 1 for j in range(i))
                
                # 提取注释
                comments = self.extract_comments_from_csharp(file_content, char_pos)
                
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
                    'comments': comments
                })
            
            i += 1
        
        return result

    def parse_parameters(self, params_str: str) -> List[Dict]:
        """解析方法参数"""
        if not params_str or params_str.strip() == '':
            return []
        
        parameters = []
        param_parts = params_str.split(',')
        
        for param in param_parts:
            param = param.strip()
            if not param:
                continue
            
            match = re.match(r'(\w+(?:<[^>]+>)?(?:\?)?)\s+(\w+)', param)
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

    def generate_sql_from_method(self, method_body: str, method_name: str, parameters: List[Dict]) -> Tuple[str, str]:
        """从方法体生成SQL语句"""
        method_lower = method_name.lower()
        table_name = self.infer_table_name(method_name)
        
        # 推断SQL类型
        if method_lower.startswith(('insert', 'add', 'create', 'save')):
            return f"INSERT INTO {table_name}", 'INSERT'
        elif method_lower.startswith(('update', 'modify', 'edit', 'change')):
            return f"UPDATE {table_name} SET", 'UPDATE'
        elif method_lower.startswith(('delete', 'remove', 'erase')):
            return f"DELETE FROM {table_name}", 'DELETE'
        
        # SELECT查询
        where_conditions = []
        
        # 查找各种LINQ模式
        patterns = [
            (r'FirstOrDefault\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)', 'first'),
            (r'First\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)', 'first'),
            (r'Where\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)', 'where'),
            (r'SingleOrDefault\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)', 'single'),
            (r'Count\s*\(\s*\)', 'count'),
            (r'Any\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)', 'any'),
        ]
        
        for pattern, ptype in patterns:
            match = re.search(pattern, method_body)
            if match:
                if ptype == 'count':
                    return f"SELECT COUNT(*) FROM {table_name}", 'SELECT'
                elif ptype == 'any':
                    condition = match.group(1)
                    where_conditions.append(self.convert_condition(condition, parameters))
                    return f"SELECT 1 FROM {table_name} WHERE {' AND '.join(where_conditions)} LIMIT 1", 'SELECT'
                elif match.groups():
                    condition = match.group(1)
                    where_conditions.append(self.convert_condition(condition, parameters))
                break
        
        # 根据方法名生成条件
        if not where_conditions:
            # 解析方法名 GetUserById, FindUserByName
            by_match = re.search(r'(?:get|find)(\w+)(?:By)?(\w*)', method_name, re.IGNORECASE)
            if by_match:
                field_part = by_match.group(2) or by_match.group(1)
                if field_part:
                    field_name = field_part
                    param_name = field_name[0].lower() + field_name[1:] if field_name else 'id'
                    snake_field = self.camel_to_snake(field_name)
                    where_conditions.append(f"{snake_field} = #{{{param_name}}}")
        
        # 构建SQL
        if where_conditions:
            where_sql = ' AND '.join(where_conditions)
            return f"SELECT * FROM {table_name} WHERE {where_sql}", 'SELECT'
        
        # 默认查询所有
        return f"SELECT * FROM {table_name}", 'SELECT'

    def convert_condition(self, condition: str, parameters: List[Dict]) -> str:
        """转换C#条件为SQL条件"""
        sql = condition
        
        # 替换运算符
        sql = re.sub(r'==', '=', sql)
        sql = re.sub(r'!=', '!=', sql)
        sql = re.sub(r'&&', 'AND', sql)
        sql = re.sub(r'\|\|', 'OR', sql)
        
        # 处理字符串方法
        sql = re.sub(r'\.Contains\(([^)]+)\)', r'LIKE CONCAT(\'%\', \1, \'%\')', sql)
        sql = re.sub(r'\.StartsWith\(([^)]+)\)', r'LIKE CONCAT(\1, \'%\')', sql)
        sql = re.sub(r'\.EndsWith\(([^)]+)\)', r'LIKE CONCAT(\'%\', \1)', sql)
        
        # 移除lambda参数
        sql = re.sub(r'\w+\s*=>\s*', '', sql)
        
        # 转换字段名
        def replace_field(match):
            field = match.group(1)
            return self.camel_to_snake(field)
        
        sql = re.sub(r'(\w+)\.(\w+)', lambda m: self.camel_to_snake(m.group(2)), sql)
        
        # 替换参数
        for param in parameters:
            sql = re.sub(rf'\b{param["name"]}\b', f'#{{{param["name"]}}}', sql)
        
        return sql

    def infer_table_name(self, method_name: str) -> str:
        """推断表名"""
        method_lower = method_name.lower()
        
        table_mappings = {
            'user': 'user', 'users': 'user',
            'order': 'orders', 'orders': 'orders',
            'product': 'product', 'products': 'product',
            'customer': 'customer', 'customers': 'customer',
        }
        
        for keyword, table in table_mappings.items():
            if keyword in method_lower:
                return table
        
        # 从方法名提取实体名
        entity_match = re.search(r'(?:get|find|insert|update|delete)(\w+)', method_name, re.IGNORECASE)
        if entity_match:
            entity = entity_match.group(1)
            return self.camel_to_snake(entity)
        
        return 'table_name'

    def map_to_java_type(self, csharp_type: str) -> str:
        """将C#类型映射到Java类型"""
        if '<' in csharp_type:
            base_type = csharp_type[:csharp_type.index('<')]
            inner_type = csharp_type[csharp_type.index('<')+1:csharp_type.rindex('>')]
            
            if base_type in ['List', 'IEnumerable', 'ICollection']:
                return f'List<{self.map_to_java_type(inner_type)}>'
        
        base_type = csharp_type.rstrip('?')
        return self.csharp_to_java_type.get(base_type, base_type)

    def convert_method_name(self, method_name: str) -> str:
        """方法名首字母小写"""
        if not method_name:
            return method_name
        return method_name[0].lower() + method_name[1:] if method_name[0].isupper() else method_name

    def convert_return_type(self, method: Dict, entity_name: str) -> Tuple[str, bool]:
        """转换返回类型"""
        return_type = method['return_type']
        
        is_collection = any(x in return_type for x in ['List', 'IEnumerable', 'ICollection'])
        
        if is_collection:
            inner_match = re.search(r'<(\w+)>', return_type)
            if inner_match:
                inner_type = inner_match.group(1)
                if inner_type == entity_name or inner_type == entity_name + '?':
                    return f'List<{entity_name}>', True
            return f'List<{entity_name}>', True
        
        if return_type == entity_name or return_type == entity_name + '?':
            return entity_name, False
        
        if return_type.lower() in ['void', 'task']:
            return 'void', False
        
        return self.map_to_java_type(return_type), False

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
        
        package_name = 'mapper'
        if dao_info['namespace']:
            package_name = dao_info['namespace'].lower().replace('.', '.') + '.mapper'
        
        mapper_name = class_name
        for suffix in ['DAO', 'Dao', 'Repository', 'DAL']:
            if mapper_name.endswith(suffix):
                mapper_name = mapper_name[:-len(suffix)]
                break
        mapper_name += 'Mapper'
        
        if not entity_name:
            entity_name = class_name
            for suffix in ['DAO', 'Dao', 'Repository', 'DAL']:
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
        
        package = 'mapper'
        if dao_info['namespace']:
            package = dao_info['namespace'].lower().replace('.', '.') + '.mapper'
        
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="{package}.{mapper_name}">

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
                xml += self.generate_insert_sql(sql_id, method, table_name)
            elif sql_type == 'UPDATE':
                xml += self.generate_update_sql(sql_id, method, table_name)
            elif sql_type == 'DELETE':
                xml += self.generate_delete_sql(sql_id, method, table_name)
        
        xml += '</mapper>\n'
        return xml

    def generate_select_sql(self, sql_id: str, method: Dict, table_name: str, entity_name: str, sql_statement: str) -> str:
        """生成SELECT语句"""
        method_lower = method['name'].lower()
        
        # 确定返回类型
        if 'count' in method_lower:
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

    def generate_insert_sql(self, sql_id: str, method: Dict, table_name: str) -> str:
        """生成INSERT语句"""
        params = method['parameters']
        
        if not params:
            return f'''    <insert id="{sql_id}">
        INSERT INTO {table_name}
    </insert>

'''
        
        columns = [self.camel_to_snake(p['name']) for p in params]
        values = [f"#{{{p['name']}}}" for p in params]
        
        return f'''    <insert id="{sql_id}" useGeneratedKeys="true" keyProperty="id">
        INSERT INTO {table_name} ({', '.join(columns)})
        VALUES ({', '.join(values)})
    </insert>

'''

    def generate_update_sql(self, sql_id: str, method: Dict, table_name: str) -> str:
        """生成UPDATE语句"""
        params = method['parameters']
        
        if not params:
            return f'''    <update id="{sql_id}">
        UPDATE {table_name}
    </update>

'''
        
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
        WHERE id = #{'id'}
    </update>

'''

    def generate_delete_sql(self, sql_id: str, method: Dict, table_name: str) -> str:
        """生成DELETE语句"""
        return f'''    <delete id="{sql_id}">
        DELETE FROM {table_name}
        WHERE id = #{'id'}
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
            print(f"  读取: {input_file}")
            
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            dao_info = self.parse_csharp_dao(content)
            
            if not dao_info['class_name']:
                print(f"  跳过: 无法解析类名")
                return False
            
            print(f"  类名: {dao_info['class_name']}, 方法数: {len(dao_info['methods'])}")
            
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
            
            print(f"  ✅ 成功: {mapper_name}")
            return True
            
        except Exception as e:
            print(f"  ❌ 失败: {str(e)}")
            return False

    def convert_folder(self, input_folder: str, output_dir: str = "./output",
                      entity_name: str = None, table_name: str = None,
                      preserve_structure: bool = False):
        """转换文件夹"""
        print(f"\n{'='*60}")
        print("C# LINQ -> Java MyBatis Mapper 转换")
        print(f"输入: {input_folder}")
        print(f"输出: {output_dir}")
        print(f"{'='*60}\n")
        
        dao_files = self.find_dao_files(input_folder)
        
        if not dao_files:
            print("未找到DAO文件")
            return
        
        print(f"找到 {len(dao_files)} 个文件\n")
        
        success = 0
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
