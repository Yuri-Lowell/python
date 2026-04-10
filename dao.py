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
        
        # LINQ操作符映射
        self.linq_operators = {
            'Where': 'WHERE',
            'Select': 'SELECT',
            'OrderBy': 'ORDER BY',
            'OrderByDescending': 'ORDER BY DESC',
            'ThenBy': 'ORDER BY',
            'ThenByDescending': 'ORDER BY DESC',
            'GroupBy': 'GROUP BY',
            'Join': 'JOIN',
            'Include': 'LEFT JOIN',
            'FirstOrDefault': 'LIMIT 1',
            'First': 'LIMIT 1',
            'SingleOrDefault': 'LIMIT 1',
            'Single': 'LIMIT 1',
            'Count': 'COUNT',
            'Any': 'EXISTS',
            'All': 'NOT EXISTS',
            'Sum': 'SUM',
            'Average': 'AVG',
            'Max': 'MAX',
            'Min': 'MIN',
            'Skip': 'OFFSET',
            'Take': 'LIMIT',
            'Contains': 'IN',
            'StartsWith': 'LIKE',
            'EndsWith': 'LIKE',
            'Contains': 'LIKE'
        }

    def find_dao_files(self, input_path: str) -> List[str]:
        """查找所有C# DAO文件"""
        dao_files = []
        input_path = Path(input_path)
        
        if input_path.is_file():
            if input_path.suffix == '.cs':
                dao_files.append(str(input_path))
        else:
            # 递归查找所有.cs文件
            for cs_file in input_path.rglob('*.cs'):
                # 检查文件名是否包含DAO或Repository
                if any(keyword in cs_file.stem for keyword in ['DAO', 'Dao', 'Repository', 'DAL', 'Service']):
                    dao_files.append(str(cs_file))
                else:
                    # 检查文件内容是否包含LINQ查询
                    try:
                        with open(cs_file, 'r', encoding='utf-8') as f:
                            content = f.read(2000)
                            if re.search(r'from\s+\w+\s+in\s+\w+|\.Where\(|\.Select\(|\.FirstOrDefault\(', content):
                                dao_files.append(str(cs_file))
                    except:
                        pass
        
        return dao_files

    def parse_csharp_dao(self, file_content: str) -> Dict:
        """解析C# DAO文件，提取类名、方法和LINQ查询"""
        result = {
            'namespace': '',
            'class_name': '',
            'methods': [],
            'usings': [],
            'linq_queries': []
        }
        
        # 提取using语句
        using_matches = re.findall(r'using\s+([\w.]+);', file_content)
        result['usings'] = using_matches
        
        # 提取namespace
        ns_match = re.search(r'namespace\s+([\w.]+)', file_content)
        if ns_match:
            result['namespace'] = ns_match.group(1)
        
        # 提取类名
        class_match = re.search(r'class\s+(\w+)(?:<[^>]+>)?(?:\s*:\s*\w+(?:<[^>]+>)?)?', file_content)
        if class_match:
            result['class_name'] = class_match.group(1)
        
        # 提取方法及其中的LINQ查询
        method_pattern = r'''
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
            
            # 解析参数
            parameters = self.parse_parameters(parameters_str)
            
            # 提取LINQ查询
            linq_queries = self.extract_linq_queries(method_body)
            
            # 推断SQL操作类型
            sql_type = self.infer_sql_type(method_name, linq_queries)
            
            # 生成SQL语句
            sql_statement = self.generate_sql_from_linq(linq_queries, method_name)
            
            result['methods'].append({
                'name': method_name,
                'return_type': return_type,
                'parameters': parameters,
                'sql_type': sql_type,
                'linq_queries': linq_queries,
                'sql_statement': sql_statement,
                'method_body': method_body
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
            
            # 匹配参数类型和名称
            match = re.match(r'(?:\[.*?\])?\s*(\w+(?:<[^>]+>)?(?:\?)?)\s+(\w+)(?:\s*=.*)?', param)
            if match:
                param_type = match.group(1)
                param_name = match.group(2)
                java_type = self.map_to_java_type(param_type)
                
                parameters.append({
                    'csharp_type': param_type,
                    'java_type': java_type,
                    'name': param_name,
                    'annotation': '@Param("' + param_name + '")'
                })
        
        return parameters

    def extract_linq_queries(self, method_body: str) -> List[Dict]:
        """提取方法体中的LINQ查询"""
        linq_queries = []
        
        # 提取方法链式调用
        chain_pattern = r'(\w+)\s*\.\s*(Where|Select|OrderBy|GroupBy|Join|Include|FirstOrDefault|First|SingleOrDefault|Single|Count|Any|Sum|Average|Max|Min|Skip|Take|ToList|ToArray)\s*\(\s*([^)]*)\s*\)'
        chains = re.finditer(chain_pattern, method_body)
        
        for chain in chains:
            linq_queries.append({
                'type': 'chain',
                'source': chain.group(1),
                'operator': chain.group(2),
                'predicate': chain.group(3)
            })
        
        # 提取查询表达式
        query_pattern = r'from\s+(\w+)\s+in\s+(\w+)\s+(?:join\s+\w+\s+in\s+\w+\s+on\s+[^\s]+\s+equals\s+[^\s]+\s+)?(?:where\s+([^\n]+))?(?:orderby\s+([^\n]+))?(?:select\s+([^\n]+))?'
        queries = re.finditer(query_pattern, method_body, re.IGNORECASE)
        
        for query in queries:
            linq_queries.append({
                'type': 'expression',
                'range_var': query.group(1),
                'source': query.group(2),
                'where': query.group(3),
                'orderby': query.group(4),
                'select': query.group(5)
            })
        
        return linq_queries

    def generate_sql_from_linq(self, linq_queries: List[Dict], method_name: str) -> str:
        """从LINQ查询生成SQL语句"""
        if not linq_queries:
            # 根据方法名生成默认SQL
            return self.generate_default_sql(method_name)
        
        sql_parts = []
        table_name = self.infer_table_name(method_name)
        
        for query in linq_queries:
            if query['type'] == 'chain':
                sql = self.convert_chain_to_sql(query, table_name)
                if sql:
                    sql_parts.append(sql)
            elif query['type'] == 'expression':
                sql = self.convert_expression_to_sql(query, table_name)
                if sql:
                    sql_parts.append(sql)
        
        return ' '.join(sql_parts) if sql_parts else self.generate_default_sql(method_name)

    def convert_chain_to_sql(self, query: Dict, table_name: str) -> str:
        """转换方法链式调用为SQL"""
        operator = query['operator']
        predicate = query['predicate']
        
        if operator == 'Where':
            return self.convert_where_to_sql(predicate)
        elif operator == 'Select':
            return self.convert_select_to_sql(predicate)
        elif operator == 'OrderBy':
            return f"ORDER BY {self.convert_field_name(predicate)} ASC"
        elif operator == 'OrderByDescending':
            return f"ORDER BY {self.convert_field_name(predicate)} DESC"
        elif operator == 'FirstOrDefault' or operator == 'First':
            return "LIMIT 1"
        elif operator == 'Count':
            return "SELECT COUNT(*) FROM"
        elif operator == 'Any':
            return "SELECT 1 FROM"
        elif operator in ['Sum', 'Average', 'Max', 'Min']:
            agg_func = operator.upper()
            field = self.convert_field_name(predicate) if predicate else '*'
            return f"SELECT {agg_func}({field}) FROM"
        elif operator == 'Skip':
            return "OFFSET"
        elif operator == 'Take':
            return "LIMIT"
        elif operator == 'ToList' or operator == 'ToArray':
            return ""
        
        return ""

    def convert_expression_to_sql(self, query: Dict, table_name: str) -> str:
        """转换查询表达式为SQL"""
        sql = "SELECT "
        
        # SELECT子句
        if query.get('select'):
            sql += self.convert_select_clause(query['select'])
        else:
            sql += "*"
        
        sql += f" FROM {table_name} AS {query['range_var']}"
        
        # WHERE子句
        if query.get('where'):
            where_sql = self.convert_where_to_sql(query['where'])
            sql += f" WHERE {where_sql}"
        
        # ORDER BY子句
        if query.get('orderby'):
            sql += f" ORDER BY {self.convert_field_name(query['orderby'])}"
        
        return sql

    def convert_where_to_sql(self, predicate: str) -> str:
        """转换WHERE条件为SQL"""
        if not predicate:
            return "1=1"
        
        # 替换C#运算符为SQL运算符
        sql = predicate
        
        # 相等比较
        sql = re.sub(r'==', '=', sql)
        sql = re.sub(r'!=', '!=', sql)
        
        # 逻辑运算符
        sql = re.sub(r'\&\&', 'AND', sql)
        sql = re.sub(r'\|\|', 'OR', sql)
        
        # 字符串方法
        sql = re.sub(r'\.Contains\(([^)]+)\)', r'LIKE CONCAT(\'%\', \1, \'%\')', sql)
        sql = re.sub(r'\.StartsWith\(([^)]+)\)', r'LIKE CONCAT(\1, \'%\')', sql)
        sql = re.sub(r'\.EndsWith\(([^)]+)\)', r'LIKE CONCAT(\'%\', \1)', sql)
        
        # 空值检查
        sql = re.sub(r'==\s*null', 'IS NULL', sql)
        sql = re.sub(r'!=\s*null', 'IS NOT NULL', sql)
        
        # 转换字段名
        sql = self.convert_field_names_in_expression(sql)
        
        return sql

    def convert_select_clause(self, select_expr: str) -> str:
        """转换SELECT子句"""
        if not select_expr:
            return "*"
        
        # 如果是 new { ... } 匿名对象
        if 'new {' in select_expr:
            fields = re.findall(r'(\w+)\s*=', select_expr)
            if fields:
                return ', '.join([self.convert_field_name(f) for f in fields])
        
        # 直接字段选择
        return self.convert_field_name(select_expr)

    def convert_field_name(self, field_expr: str) -> str:
        """转换字段名为数据库字段名（驼峰转下划线）"""
        # 提取字段名
        field_match = re.search(r'(\w+)', field_expr)
        if field_match:
            field = field_match.group(1)
            return self.camel_to_snake(field)
        return field_expr

    def convert_field_names_in_expression(self, expression: str) -> str:
        """转换表达式中的所有字段名"""
        # 匹配类似 obj.Field 的模式
        def replace_field(match):
            field = match.group(1)
            return self.camel_to_snake(field)
        
        # 匹配变量名.字段名
        pattern = r'\w+\.(\w+)'
        expression = re.sub(pattern, replace_field, expression)
        
        # 匹配独立的字段名（在比较表达式中）
        pattern2 = r'\b([a-z][a-zA-Z0-9]*)\b(?=\s*(?:==|!=|>|<|>=|<=|=|LIKE|IN))'
        expression = re.sub(pattern2, lambda m: self.camel_to_snake(m.group(1)), expression, flags=re.IGNORECASE)
        
        return expression

    def generate_default_sql(self, method_name: str) -> str:
        """根据方法名生成默认SQL"""
        method_lower = method_name.lower()
        
        if 'getby' in method_lower or 'findby' in method_lower:
            # 解析字段名
            fields = re.findall(r'(?:get|find)by(\w+)', method_lower, re.IGNORECASE)
            if fields:
                where_clause = ' AND '.join([f'{self.camel_to_snake(field)} = #{{{field}}}' for field in fields])
                return f"WHERE {where_clause}"
        
        return ""

    def infer_table_name(self, method_name: str) -> str:
        """推断表名"""
        # 从方法名推断
        if 'user' in method_name.lower():
            return 'user'
        elif 'order' in method_name.lower():
            return 'order'
        elif 'product' in method_name.lower():
            return 'product'
        else:
            return 'table_name'

    def infer_sql_type(self, method_name: str, linq_queries: List[Dict]) -> str:
        """推断SQL操作类型"""
        method_lower = method_name.lower()
        
        # 根据方法名判断
        if any(method_lower.startswith(prefix) for prefix in ['get', 'select', 'find', 'query', 'fetch']):
            return 'SELECT'
        elif any(method_lower.startswith(prefix) for prefix in ['insert', 'add', 'create', 'save']):
            return 'INSERT'
        elif any(method_lower.startswith(prefix) for prefix in ['update', 'modify', 'edit', 'change']):
            return 'UPDATE'
        elif any(method_lower.startswith(prefix) for prefix in ['delete', 'remove', 'erase']):
            return 'DELETE'
        
        # 根据LINQ操作符判断
        for query in linq_queries:
            if query.get('operator') in ['Count', 'Any', 'Sum', 'Average', 'Max', 'Min']:
                return 'SELECT'
        
        return 'SELECT'

    def map_to_java_type(self, csharp_type: str) -> str:
        """将C#类型映射到Java类型"""
        # 处理泛型
        if '<' in csharp_type:
            base_type = csharp_type[:csharp_type.index('<')]
            inner_type = csharp_type[csharp_type.index('<')+1:csharp_type.rindex('>')]
            
            if base_type in ['List', 'IEnumerable', 'ICollection']:
                return f'List<{self.map_to_java_type(inner_type)}>'
            elif base_type == 'Dictionary':
                types = inner_type.split(',')
                if len(types) == 2:
                    return f'Map<{self.map_to_java_type(types[0].strip())}, {self.map_to_java_type(types[1].strip())}>'
        
        # 基本类型映射
        base_type = csharp_type.rstrip('?')
        java_type = self.csharp_to_java_type.get(base_type, base_type)
        
        # 首字母大写（如果是自定义类型）
        if java_type not in self.csharp_to_java_type.values() and java_type != 'void':
            java_type = java_type[0].upper() + java_type[1:] if java_type else java_type
        
        return java_type

    def convert_method_name(self, method_name: str) -> str:
        """将C#方法名转换为Java方法名（首字母小写）"""
        if not method_name:
            return method_name
        
        if method_name[0].islower():
            return method_name
        
        return method_name[0].lower() + method_name[1:]

    def convert_return_type(self, method: Dict, entity_name: str) -> str:
        """转换返回类型"""
        return_type = method['return_type']
        
        # 处理集合类型
        if any(x in return_type for x in ['List', 'IEnumerable', 'ICollection']):
            return f'List<{entity_name}>'
        
        # 处理单个实体
        if return_type == entity_name or return_type == entity_name + '?':
            return entity_name
        
        # 处理值类型
        java_type = self.map_to_java_type(return_type)
        
        return java_type if java_type != 'void' else 'void'

    def generate_mapper_java(self, dao_info: Dict, entity_name: str = None) -> Tuple[str, str, str, str]:
        """生成Java Mapper接口代码"""
        class_name = dao_info['class_name']
        
        # 生成包名
        package_name = self.convert_namespace_to_package(dao_info['namespace'])
        
        # 生成Mapper名称
        mapper_name = class_name
        for suffix in ['DAO', 'Dao', 'Repository', 'DAL', 'Service']:
            if mapper_name.endswith(suffix):
                mapper_name = mapper_name[:-len(suffix)]
                break
        mapper_name += 'Mapper'
        
        # 确定实体类名
        if not entity_name:
            entity_name = class_name
            for suffix in ['DAO', 'Dao', 'Repository', 'DAL', 'Service']:
                if entity_name.endswith(suffix):
                    entity_name = entity_name[:-len(suffix)]
                    break
        
        # 生成导入语句
        imports = set()
        imports.add('org.apache.ibatis.annotations.Mapper')
        imports.add('org.apache.ibatis.annotations.Param')
        
        for method in dao_info['methods']:
            return_type = self.map_to_java_type(method['return_type'])
            if return_type.startswith('List<'):
                imports.add('java.util.List')
            elif return_type.startswith('Map<'):
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
        
        # 生成接口代码
        java_code = f"""package {package_name};

{import_lines}

/**
 * {class_name} 转换的MyBatis Mapper接口
 * 原始C#类: {class_name}
 * 命名空间: {dao_info['namespace']}
 * 
 * 注意: 此文件由工具自动生成，请根据实际需求调整SQL语句
 */
@Mapper
public interface {mapper_name} {{

"""
        
        # 生成方法
        for method in dao_info['methods']:
            method_name = self.convert_method_name(method['name'])
            return_type = self.convert_return_type(method, entity_name)
            
            # 构建参数列表
            params = []
            for param in method['parameters']:
                params.append(f"    @Param(\"{param['name']}\") {param['java_type']} {param['name']}")
            
            param_str = ',\n'.join(params) if params else ''
            if param_str:
                param_str = '\n' + param_str + '\n'
            
            # 生成方法注释
            comment_lines = [
                "    /**",
                f"     * {method_name}",
                f"     * 原始C#方法: {method['name']}",
                f"     * SQL操作类型: {method['sql_type']}",
                "     *",
            ]
            
            for param in method['parameters']:
                comment_lines.append(f"     * @param {param['name']} ")
            
            comment_lines.append(f"     * @return {return_type}")
            comment_lines.append("     */")
            
            comment = '\n'.join(comment_lines)
            
            # 生成方法定义
            method_code = f"""
{comment}
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

    <!-- ==================== 基础配置 ==================== -->
    
    <!-- 基础结果映射 -->
    <resultMap id="BaseResultMap" type="{entity_name}">
        <!-- TODO: 根据实体类配置字段映射 -->
        <!-- 示例:
        <id column="id" property="id" jdbcType="BIGINT"/>
        <result column="create_time" property="createTime" jdbcType="TIMESTAMP"/>
        <result column="update_time" property="updateTime" jdbcType="TIMESTAMP"/>
        -->
    </resultMap>

    <!-- 基础字段列表 -->
    <sql id="Base_Column_List">
        <!-- TODO: 配置所有字段，例如: id, name, create_time -->
    </sql>

    <!-- ==================== SQL语句 ==================== -->
'''
        
        # 为每个方法生成SQL
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
            
            xml += '\n'
        
        xml += '</mapper>\n'
        return xml

    def generate_select_sql(self, sql_id: str, method: Dict, table_name: str, entity_name: str, sql_statement: str) -> str:
        """生成SELECT语句"""
        params = method['parameters']
        
        # 构建WHERE条件
        where_clause = ""
        if sql_statement:
            where_clause = f"        {sql_statement}"
        elif params:
            conditions = []
            for param in params:
                conditions.append(f"            <if test=\"{param['name']} != null\">\n                AND {self.camel_to_snake(param['name'])} = #{{{param['name']}}}\n            </if>")
            where_clause = "        <where>\n" + "\n".join(conditions) + "\n        </where>"
        else:
            where_clause = "        <!-- 添加WHERE条件 -->"
        
        xml = f'''    <!-- ========== {sql_id} ========== -->
    <select id="{sql_id}" resultMap="BaseResultMap" parameterType="map">
        SELECT <include refid="Base_Column_List"/>
        FROM {table_name}
{where_clause}
    </select>

'''
        return xml

    def generate_insert_sql(self, sql_id: str, method: Dict, table_name: str) -> str:
        """生成INSERT语句"""
        params = method['parameters']
        
        if not params:
            return f'''    <!-- ========== {sql_id} ========== -->
    <insert id="{sql_id}">
        INSERT INTO {table_name}
        <!-- TODO: 配置插入字段 -->
    </insert>

'''
        
        columns = [self.camel_to_snake(p['name']) for p in params]
        values = [f"#{{{p['name']}}}" for p in params]
        
        xml = f'''    <!-- ========== {sql_id} ========== -->
    <insert id="{sql_id}" parameterType="map" useGeneratedKeys="true" keyProperty="id">
        INSERT INTO {table_name} (
            {', '.join(columns)}
        ) VALUES (
            {', '.join(values)}
        )
    </insert>

'''
        return xml

    def generate_update_sql(self, sql_id: str, method: Dict, table_name: str) -> str:
        """生成UPDATE语句"""
        params = method['parameters']
        
        if not params:
            return f'''    <!-- ========== {sql_id} ========== -->
    <update id="{sql_id}">
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
        
        xml = f'''    <!-- ========== {sql_id} ========== -->
    <update id="{sql_id}" parameterType="map">
        UPDATE {table_name}
        <set>
{set_str}
        </set>
{where_clause}
    </update>

'''
        return xml

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
        
        xml = f'''    <!-- ========== {sql_id} ========== -->
    <delete id="{sql_id}" parameterType="map">
        DELETE FROM {table_name}
{where_clause}
    </delete>

'''
        return xml

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
        
        if name[0].isupper():
            name = name[0].lower() + name[1:]
        
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

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
            
            # 确定输出路径
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
            
            # 生成Java Mapper
            java_code, mapper_name, auto_entity_name, package_name = self.generate_mapper_java(dao_info, entity_name)
            
            # 生成XML
            xml_code = self.generate_mapper_xml(dao_info, mapper_name, auto_entity_name, table_name)
            
            # 保存文件
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
            f.write("\n注意事项:\n")
            f.write("1. 请根据实际业务需求完善生成的SQL语句\n")
            f.write("2. 请配置正确的实体类和字段映射\n")
            f.write("3. 请检查参数类型映射是否正确\n")
            f.write("4. 建议手动验证生成的代码\n")
            f.write("5. LINQ查询可能需要手动调整SQL语法\n")
        
        print(f"📄 转换报告已生成: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description='将C# LINQ DAO转换为Java MyBatis Mapper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 转换单个文件
  python linq_to_mybatis.py -i UserDAO.cs -o ./output
  
  # 转换整个文件夹
  python linq_to_mybatis.py -i ./CSharpProject/DAL -o ./mybatis
  
  # 递归转换并保持目录结构
  python linq_to_mybatis.py -i ./CSharpProject -o ./mybatis -r -s
  
  # 指定实体类和表名
  python linq_to_mybatis.py -i UserDAO.cs -e User -t t_user -o ./output
        """
    )
    
    parser.add_argument('-i', '--input', required=True, help='输入的C#文件或文件夹路径')
    parser.add_argument('-o', '--output', default='./mybatis_output', help='输出目录 (默认: ./mybatis_output)')
    parser.add_argument('-e', '--entity', help='实体类名 (默认: 自动推断)')
    parser.add_argument('-t', '--table', help='数据库表名 (默认: 根据实体名转换)')
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
