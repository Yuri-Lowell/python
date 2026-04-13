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
            'int': 'Integer', 'int?': 'Integer',
            'long': 'Long', 'long?': 'Long',
            'short': 'Short', 'short?': 'Short',
            'byte': 'Byte', 'byte?': 'Byte',
            'bool': 'Boolean', 'bool?': 'Boolean',
            'boolean': 'Boolean',
            'float': 'Float', 'float?': 'Float',
            'double': 'Double', 'double?': 'Double',
            'decimal': 'BigDecimal', 'decimal?': 'BigDecimal',
            
            # 字符串
            'string': 'String', 'char': 'String', 'char?': 'String',
            
            # 日期时间
            'DateTime': 'Date', 'DateTime?': 'Date',
            'TimeSpan': 'String', 'TimeSpan?': 'String',
            
            # 特殊类型
            'Guid': 'String', 'Guid?': 'String',
            'object': 'Object', 'Object': 'Object',
            'void': 'void', 'Task': 'void',
            
            # 集合类型
            'IEnumerable': 'List', 'ICollection': 'List', 'IList': 'List',
            
            # DAO结果类型 - 转换为void
            'DaoExecuteResult': 'void',
            'DaoExecuteResult?': 'void',
            'ExecuteResult': 'void',
            'OperationResult': 'void',
            'DbResult': 'void'
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

    def extract_comments_from_method(self, method_text: str) -> Dict[str, str]:
        """从方法文本中提取注释"""
        result = {'summary': '', 'params': {}, 'returns': ''}
        
        # 提取summary
        summary_match = re.search(r'///\s*<summary>\s*(.*?)\s*</summary>', method_text, re.DOTALL | re.IGNORECASE)
        if summary_match:
            result['summary'] = re.sub(r'\s+', ' ', summary_match.group(1).strip())
        
        # 提取param
        param_pattern = r'///\s*<param\s+name="(\w+)">\s*(.*?)\s*</param>'
        for match in re.finditer(param_pattern, method_text, re.DOTALL):
            result['params'][match.group(1)] = re.sub(r'\s+', ' ', match.group(2).strip())
        
        # 提取returns
        returns_match = re.search(r'///\s*<returns>\s*(.*?)\s*</returns>', method_text, re.DOTALL)
        if returns_match:
            result['returns'] = re.sub(r'\s+', ' ', returns_match.group(1).strip())
        
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
        
        # 提取类名
        class_match = re.search(r'class\s+(\w+)', file_content)
        if class_match:
            result['class_name'] = class_match.group(1)
        
        # 方法匹配模式
        method_pattern = r'''
            (?:public|private|protected|internal)\s+
            (?:static\s+)?
            (?:virtual\s+)?
            (?:override\s+)?
            (?:async\s+)?
            (?:Task<)?
            ([\w<>\[\]?]+)
            (?:>)?
            \s+(\w+)\s*
            \(([^)]*)\)
            \s*
            (?:\{)
            (.*?)
            (?:\n\s*\})
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
            method_start = method.start()
            comment_text = ""
            if method_start > 0:
                before_method = file_content[max(0, method_start - 500):method_start]
                comment_lines = []
                lines = before_method.split('\n')
                for line in reversed(lines):
                    if line.strip().startswith('///') or line.strip().startswith('//') or line.strip().startswith('/*'):
                        comment_lines.insert(0, line)
                    elif line.strip() and not line.strip().startswith('[') and not line.strip().startswith('using'):
                        break
                comment_text = '\n'.join(comment_lines)
            
            method_comments = self.extract_comments_from_method(comment_text)
            
            # 解析参数
            parameters = self.parse_parameters(parameters_str)
            
            # 生成SQL
            sql_statement, sql_type = self.generate_sql_from_method(method_body, method_name, parameters)
            
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
        
        # 查找LINQ Where条件
        where_match = re.search(r'\.Where\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)', method_body)
        if where_match:
            condition = where_match.group(1)
            where_conditions.append(self.convert_condition(condition, parameters))
        
        # 查找FirstOrDefault条件
        first_match = re.search(r'FirstOrDefault\s*\(\s*\w+\s*=>\s*([^)]+)\s*\)', method_body)
        if first_match:
            condition = first_match.group(1)
            where_conditions.append(self.convert_condition(condition, parameters))
        
        # 查找Count
        if re.search(r'\.Count\s*\(\s*\)', method_body):
            return f"SELECT COUNT(*) FROM {table_name}", 'SELECT'
        
        # 根据方法名生成条件
        if not where_conditions:
            by_match = re.search(r'(?:get|find)(\w+)By(\w+)', method_name, re.IGNORECASE)
            if by_match:
                field_name = by_match.group(2)
                param_name = field_name[0].lower() + field_name[1:]
                snake_field = self.camel_to_snake(field_name)
                where_conditions.append(f"{snake_field} = #{{{param_name}}}")
            else:
                single_match = re.search(r'(?:get|find)(\w+)', method_name, re.IGNORECASE)
                if single_match and single_match.group(1).lower() not in ['all', 'list']:
                    entity = single_match.group(1)
                    param_name = entity[0].lower() + entity[1:] + "Id"
                    snake_field = self.camel_to_snake(entity) + "_id"
                    where_conditions.append(f"{snake_field} = #{{{param_name}}}")
        
        # 构建SQL
        if where_conditions:
            where_sql = ' AND '.join(where_conditions)
            return f"SELECT * FROM {table_name} WHERE {where_sql}", 'SELECT'
        
        # 获取所有
        if 'all' in method_lower or 'list' in method_lower:
            return f"SELECT * FROM {table_name}", 'SELECT'
        
        return f"SELECT * FROM {table_name}", 'SELECT'

    def convert_condition(self, condition: str, parameters: List[Dict]) -> str:
        """转换C#条件为SQL"""
        sql = condition
        
        # 运算符
        sql = re.sub(r'==', '=', sql)
        sql = re.sub(r'!=', '!=', sql)
        sql = re.sub(r'&&', 'AND', sql)
        sql = re.sub(r'\|\|', 'OR', sql)
        
        # 字符串方法
        sql = re.sub(r'\.Contains\(([^)]+)\)', r'LIKE CONCAT(\'%\', \1, \'%\')', sql)
        sql = re.sub(r'\.StartsWith\(([^)]+)\)', r'LIKE CONCAT(\1, \'%\')', sql)
        sql = re.sub(r'\.EndsWith\(([^)]+)\)', r'LIKE CONCAT(\'%\', \1)', sql)
        
        # 移除lambda
        sql = re.sub(r'\w+\s*=>\s*', '', sql)
        
        # 转换字段名
        sql = re.sub(r'(\w+)\.(\w+)', lambda m: self.camel_to_snake(m.group(2)), sql)
        
        # 替换参数
        for param in parameters:
            sql = re.sub(rf'\b{param["name"]}\b', f'#{{{param["name"]}}}', sql)
        
        return sql

    def infer_table_name(self, method_name: str) -> str:
        """推断表名"""
        method_lower = method_name.lower()
        
        table_map = {
            'user': 'user', 'users': 'user',
            'order': 'orders', 'orders': 'orders',
            'product': 'product', 'products': 'product',
            'customer': 'customer', 'customers': 'customer',
        }
        
        for key, table in table_map.items():
            if key in method_lower:
                return table
        
        match = re.search(r'(?:get|find|insert|update|delete)([A-Z][a-z]+)', method_name)
        if match:
            return self.camel_to_snake(match.group(1))
        
        return 'table_name'

    def map_to_java_type(self, csharp_type: str) -> str:
        """C#类型转Java类型 - 优先处理DaoExecuteResult"""
        # 先处理DaoExecuteResult类型
        if 'DaoExecuteResult' in csharp_type or 'ExecuteResult' in csharp_type or 'OperationResult' in csharp_type:
            return 'void'
        
        # 处理泛型
        if '<' in csharp_type:
            base_type = csharp_type[:csharp_type.index('<')]
            inner_type = csharp_type[csharp_type.index('<')+1:csharp_type.rindex('>')]
            
            if base_type in ['List', 'IEnumerable', 'ICollection', 'IList']:
                return f'List<{self.map_to_java_type(inner_type)}>'
            elif base_type in ['Task']:
                return self.map_to_java_type(inner_type)
        
        # 基本类型映射
        base_type = csharp_type.rstrip('?')
        java_type = self.csharp_to_java_type.get(base_type, base_type)
        
        # 自定义类型首字母大写
        if java_type not in self.csharp_to_java_type.values() and java_type != 'void':
            java_type = java_type[0].upper() + java_type[1:] if java_type else java_type
        
        return java_type

    def convert_method_name(self, name: str) -> str:
        """方法名首字母小写"""
        return name[0].lower() + name[1:] if name and name[0].isupper() else name

    def convert_return_type(self, method: Dict, entity_name: str) -> Tuple[str, bool]:
        """转换返回类型"""
        return_type = method['return_type']
        
        # 处理DaoExecuteResult类型
        if 'DaoExecuteResult' in return_type or 'ExecuteResult' in return_type or 'OperationResult' in return_type:
            return 'void', False
        
        # 处理Task<DaoExecuteResult>
        if 'Task<' in return_type and ('DaoExecuteResult' in return_type or 'ExecuteResult' in return_type):
            return 'void', False
        
        # 集合类型
        if any(x in return_type for x in ['List', 'IEnumerable', 'ICollection', 'IList']):
            inner_match = re.search(r'<(\w+)>', return_type)
            if inner_match:
                inner = inner_match.group(1)
                if inner == entity_name or inner == entity_name + '?':
                    return f'List<{entity_name}>', True
                # 处理集合中的DaoExecuteResult
                if 'DaoExecuteResult' in inner or 'ExecuteResult' in inner:
                    return 'void', False
            return f'List<{entity_name}>', True
        
        # 实体类型
        if return_type == entity_name or return_type == entity_name + '?':
            return entity_name, False
        
        # void和Task
        if return_type.lower() in ['void', 'task']:
            return 'void', False
        
        # 其他类型
        java_type = self.map_to_java_type(return_type)
        
        # 如果映射后还是DaoExecuteResult，转为void
        if 'DaoExecuteResult' in java_type or 'ExecuteResult' in java_type:
            return 'void', False
        
        return java_type, False

    def generate_java_comment(self, comments: Dict, method_name: str, params: List[Dict], return_type: str) -> str:
        """生成Java注释"""
        lines = ["    /**"]
        
        summary = comments.get('summary', method_name)
        lines.append(f"     * {summary}")
        lines.append("     *")
        
        for p in params:
            desc = comments.get('params', {}).get(p['name'], '')
            lines.append(f"     * @param {p['name']} {desc}")
        
        if return_type != 'void':
            desc = comments.get('returns', '')
            lines.append(f"     * @return {return_type} {desc}")
        
        lines.append("     */")
        return '\n'.join(lines)

    def generate_mapper_java(self, dao_info: Dict, entity_name: str = None) -> Tuple[str, str, str, str]:
        """生成Java Mapper接口"""
        class_name = dao_info['class_name']
        
        # 包名
        package = 'mapper'
        if dao_info['namespace']:
            parts = dao_info['namespace'].lower().split('.')
            if len(parts) > 1:
                package = '.'.join(parts[:-1]) + '.mapper'
        
        # Mapper名
        mapper = class_name
        for suffix in ['DAO', 'Dao', 'Repository', 'DAL']:
            if mapper.endswith(suffix):
                mapper = mapper[:-len(suffix)]
                break
        mapper += 'Mapper'
        
        # 实体名
        if not entity_name:
            entity_name = class_name
            for suffix in ['DAO', 'Dao', 'Repository', 'DAL']:
                if entity_name.endswith(suffix):
                    entity_name = entity_name[:-len(suffix)]
                    break
        
        # 导入
        imports = {'org.apache.ibatis.annotations.Mapper', 'org.apache.ibatis.annotations.Param'}
        
        for method in dao_info['methods']:
            ret_type, is_col = self.convert_return_type(method, entity_name)
            if is_col or 'List<' in ret_type:
                imports.add('java.util.List')
            elif 'Map<' in ret_type:
                imports.add('java.util.Map')
            for p in method['parameters']:
                if p['java_type'] == 'Date':
                    imports.add('java.util.Date')
                elif p['java_type'] == 'BigDecimal':
                    imports.add('java.math.BigDecimal')
                elif p['java_type'] == 'List':
                    imports.add('java.util.List')
        
        if entity_name and entity_name not in ['Object', 'void']:
            imports.add(f'entity.{entity_name}')
        
        import_lines = '\n'.join(sorted([f'import {i};' for i in imports]))
        
        # 类注释
        class_comment = ""
        if dao_info.get('class_comments'):
            class_comment = f"\n/**\n * {dao_info['class_comments']}\n */"
        
        # 生成代码
        code = f"""package {package};
{import_lines}
{class_comment}
@Mapper
public interface {mapper} {{

"""
        
        for method in dao_info['methods']:
            method_name = self.convert_method_name(method['name'])
            ret_type, _ = self.convert_return_type(method, entity_name)
            
            comment = self.generate_java_comment(
                method.get('comments', {}),
                method_name,
                method['parameters'],
                ret_type
            )
            
            params = [f"@Param(\"{p['name']}\") {p['java_type']} {p['name']}" for p in method['parameters']]
            param_str = ', '.join(params)
            
            code += f"""
{comment}
    {ret_type} {method_name}({param_str});
"""
        
        code += "\n}\n"
        return code, mapper, entity_name, package

    def generate_mapper_xml(self, dao_info: Dict, mapper_name: str, entity_name: str, table_name: str = None) -> str:
        """生成XML"""
        if not table_name:
            table_name = self.camel_to_snake(entity_name)
        
        package = 'mapper'
        if dao_info['namespace']:
            parts = dao_info['namespace'].lower().split('.')
            if len(parts) > 1:
                package = '.'.join(parts[:-1]) + '.mapper'
        
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="{package}.{mapper_name}">

    <sql id="Base_Column_List">
        <!-- id, name, create_time -->
    </sql>

'''
        
        for method in dao_info['methods']:
            sql_id = self.convert_method_name(method['name'])
            sql_type = method['sql_type']
            sql_stmt = method.get('sql_statement', '')
            
            if sql_type == 'SELECT':
                xml += self._gen_select(sql_id, method, table_name, entity_name, sql_stmt)
            elif sql_type == 'INSERT':
                xml += self._gen_insert(sql_id, method, table_name, sql_stmt)
            elif sql_type == 'UPDATE':
                xml += self._gen_update(sql_id, method, table_name, sql_stmt)
            elif sql_type == 'DELETE':
                xml += self._gen_delete(sql_id, method, table_name, sql_stmt)
        
        xml += '</mapper>\n'
        return xml

    def _gen_select(self, sql_id: str, method: Dict, table: str, entity: str, sql_stmt: str) -> str:
        """生成SELECT"""
        method_lower = method['name'].lower()
        result_type = 'int' if 'count' in method_lower else entity
        
        if sql_stmt:
            return f'''    <select id="{sql_id}" resultType="{result_type}">
        {sql_stmt}
    </select>

'''
        
        if method['parameters']:
            conds = []
            for p in method['parameters']:
                conds.append(f"            <if test=\"{p['name']} != null\">\n                AND {self.camel_to_snake(p['name'])} = #{{{p['name']}}}\n            </if>")
            where = '\n'.join(conds)
            return f'''    <select id="{sql_id}" resultType="{result_type}">
        SELECT * FROM {table}
        <where>
{where}
        </where>
    </select>

'''
        
        return f'''    <select id="{sql_id}" resultType="{result_type}">
        SELECT * FROM {table}
    </select>

'''

    def _gen_insert(self, sql_id: str, method: Dict, table: str, sql_stmt: str) -> str:
        """生成INSERT"""
        if sql_stmt and sql_stmt.startswith('INSERT'):
            return f'''    <insert id="{sql_id}" useGeneratedKeys="true" keyProperty="id">
        {sql_stmt}
    </insert>

'''
        
        params = method['parameters']
        if params:
            cols = [self.camel_to_snake(p['name']) for p in params if p['name'] != 'id']
            vals = [f"#{{{p['name']}}}" for p in params if p['name'] != 'id']
            if cols:
                return f'''    <insert id="{sql_id}" useGeneratedKeys="true" keyProperty="id">
        INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(vals)})
    </insert>

'''
        
        return f'''    <insert id="{sql_id}" useGeneratedKeys="true" keyProperty="id">
        INSERT INTO {table}
    </insert>

'''

    def _gen_update(self, sql_id: str, method: Dict, table: str, sql_stmt: str) -> str:
        """生成UPDATE"""
        if sql_stmt and sql_stmt.startswith('UPDATE'):
            return f'''    <update id="{sql_id}">
        {sql_stmt}
        WHERE id = #{{id}}
    </update>

'''
        
        params = method['parameters']
        if params:
            sets = []
            for p in params:
                if p['name'].lower() != 'id':
                    sets.append(f"            {self.camel_to_snake(p['name'])} = #{{{p['name']}}},")
            set_str = '\n'.join(sets) if sets else "            -- TODO"
            return f'''    <update id="{sql_id}">
        UPDATE {table}
        <set>
{set_str}
        </set>
        WHERE id = #{{id}}
    </update>

'''
        
        return f'''    <update id="{sql_id}">
        UPDATE {table}
        WHERE id = #{{id}}
    </update>

'''

    def _gen_delete(self, sql_id: str, method: Dict, table: str, sql_stmt: str) -> str:
        """生成DELETE"""
        if sql_stmt and sql_stmt.startswith('DELETE'):
            return f'''    <delete id="{sql_id}">
        {sql_stmt}
    </delete>

'''
        
        return f'''    <delete id="{sql_id}">
        DELETE FROM {table}
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
            filename = os.path.basename(input_file)
            print(f"  读取: {filename}")
            
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            dao_info = self.parse_csharp_dao(content)
            
            if not dao_info['class_name']:
                print(f"  ⚠️ 无法解析类名")
                return False
            
            method_count = len(dao_info['methods'])
            print(f"  类: {dao_info['class_name']}, 方法数: {method_count}")
            
            if method_count == 0:
                print(f"  ⚠️ 未找到任何方法")
                return False
            
            # 输出目录
            if preserve_structure and base_path:
                rel_path = os.path.relpath(input_file, base_path)
                out_sub = os.path.dirname(rel_path)
                java_dir = os.path.join(output_dir, "java", out_sub)
                xml_dir = os.path.join(output_dir, "xml", out_sub)
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
