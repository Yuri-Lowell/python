import re
import os
from pathlib import Path
from typing import List, Dict, Tuple

class CSharpToJavaMapperConverter:
    def __init__(self):
        self.type_mapping = {
            'int': 'Integer',
            'long': 'Long',
            'string': 'String',
            'bool': 'Boolean',
            'boolean': 'Boolean',
            'DateTime': 'Date',
            'decimal': 'BigDecimal',
            'double': 'Double',
            'float': 'Float',
            'Guid': 'String'
        }
        
        self.csharp_to_java_type = {
            'int': 'Integer',
            'int?': 'Integer',
            'long': 'Long',
            'long?': 'Long',
            'string': 'String',
            'bool': 'Boolean',
            'bool?': 'Boolean',
            'boolean': 'Boolean',
            'DateTime': 'Date',
            'DateTime?': 'Date',
            'decimal': 'BigDecimal',
            'decimal?': 'BigDecimal',
            'double': 'Double',
            'double?': 'Double',
            'float': 'Float',
            'float?': 'Float',
            'Guid': 'String',
            'Guid?': 'String'
        }

    def parse_csharp_dao(self, file_content: str) -> Dict:
        """解析C# DAO文件，提取类名和方法信息"""
        result = {
            'namespace': '',
            'class_name': '',
            'methods': []
        }
        
        # 提取namespace
        ns_match = re.search(r'namespace\s+([\w.]+)', file_content)
        if ns_match:
            result['namespace'] = ns_match.group(1)
        
        # 提取类名
        class_match = re.search(r'class\s+(\w+)(?:\s*:\s*\w+)?', file_content)
        if class_match:
            result['class_name'] = class_match.group(1)
        
        # 提取方法
        method_pattern = r'(?:public|private|protected|internal)\s+(async\s+)?(?:Task<)?(\w+)(?:>)?\s+(\w+)\s*\(([^)]*)\)'
        methods = re.finditer(method_pattern, file_content)
        
        for method in methods:
            is_async = method.group(1) is not None
            return_type = method.group(2)
            method_name = method.group(3)
            parameters_str = method.group(4)
            
            # 解析参数
            parameters = self.parse_parameters(parameters_str)
            
            # 推断SQL操作类型
            sql_type = self.infer_sql_type(method_name)
            
            result['methods'].append({
                'name': method_name,
                'return_type': return_type,
                'parameters': parameters,
                'is_async': is_async,
                'sql_type': sql_type
            })
        
        return result

    def parse_parameters(self, params_str: str) -> List[Dict]:
        """解析方法参数"""
        if not params_str or params_str.strip() == '':
            return []
        
        parameters = []
        # 分割参数
        param_parts = params_str.split(',')
        
        for param in param_parts:
            param = param.strip()
            if not param:
                continue
            
            # 匹配参数类型和名称，支持可选参数
            match = re.match(r'(?:\[.*?\])?\s*(\w+(?:\?)?)\s+(\w+)(?:\s*=.*)?', param)
            if match:
                param_type = match.group(1)
                param_name = match.group(2)
                
                # 映射Java类型
                java_type = self.csharp_to_java_type.get(param_type, 'Object')
                
                parameters.append({
                    'csharp_type': param_type,
                    'java_type': java_type,
                    'name': param_name,
                    'annotation': '@Param("' + param_name + '")'
                })
        
        return parameters

    def infer_sql_type(self, method_name: str) -> str:
        """根据方法名推断SQL操作类型"""
        method_lower = method_name.lower()
        
        if method_lower.startswith('get') or method_lower.startswith('select') or method_lower.startswith('find'):
            return 'SELECT'
        elif method_lower.startswith('insert') or method_lower.startswith('add') or method_lower.startswith('create'):
            return 'INSERT'
        elif method_lower.startswith('update') or method_lower.startswith('modify') or method_lower.startswith('edit'):
            return 'UPDATE'
        elif method_lower.startswith('delete') or method_lower.startswith('remove'):
            return 'DELETE'
        else:
            return 'SELECT'

    def generate_mapper_java(self, dao_info: Dict, entity_name: str = None) -> str:
        """生成Java Mapper接口代码"""
        class_name = dao_info['class_name']
        
        # 如果类名以DAO或Repository结尾，去掉后缀
        mapper_name = class_name
        if mapper_name.endswith('DAO'):
            mapper_name = mapper_name[:-3]
        elif mapper_name.endswith('Repository'):
            mapper_name = mapper_name[:-10]
        mapper_name += 'Mapper'
        
        # 确定实体类名
        if not entity_name:
            entity_name = class_name.replace('DAO', '').replace('Repository', '')
        
        # 生成导入语句
        imports = set()
        imports.add('org.apache.ibatis.annotations.Mapper')
        imports.add('org.apache.ibatis.annotations.Param')
        
        for method in dao_info['methods']:
            for param in method['parameters']:
                if param['java_type'] in ['Date', 'BigDecimal']:
                    if param['java_type'] == 'Date':
                        imports.add('java.util.Date')
                    elif param['java_type'] == 'BigDecimal':
                        imports.add('java.math.BigDecimal')
        
        import_lines = '\n'.join([f'import {imp};' for imp in sorted(imports)])
        
        # 生成接口代码
        java_code = f"""package mapper;

{import_lines}

@Mapper
public interface {mapper_name} {{

"""
        
        # 生成方法
        for method in dao_info['methods']:
            # 转换返回类型
            return_type = self.convert_return_type(method['return_type'], method['sql_type'], entity_name)
            
            # 构建参数列表
            params = []
            for param in method['parameters']:
                params.append(f"@Param(\"{param['name']}\") {param['java_type']} {param['name']}")
            
            param_str = ', '.join(params) if params else ''
            
            # 生成方法注释
            comment = f"""    /**
     * {method['name']}
     * SQL Type: {method['sql_type']}
     """
            if method['parameters']:
                for param in method['parameters']:
                    comment += f"\n     * @param {param['name']} "
            comment += f"""
     * @return {return_type}
     */"""
            
            # 生成方法定义
            method_code = f"""
{comment}
    {return_type} {method['name']}({param_str});
"""
            java_code += method_code + "\n"
        
        java_code += "}\n"
        return java_code, mapper_name, entity_name

    def convert_return_type(self, csharp_type: str, sql_type: str, entity_name: str) -> str:
        """转换返回类型"""
        # 处理异步方法
        if csharp_type.lower() == 'task':
            return 'void'
        
        # 处理集合类型
        if 'List<' in csharp_type or 'IEnumerable<' in csharp_type or 'ICollection<' in csharp_type:
            # 提取泛型类型
            match = re.search(r'<(\w+)>', csharp_type)
            if match:
                inner_type = match.group(1)
                if inner_type in self.csharp_to_java_type:
                    inner_type = self.csharp_to_java_type[inner_type]
                return f'List<{inner_type}>'
            return f'List<{entity_name}>'
        
        # 处理单个实体
        if csharp_type == entity_name or csharp_type == entity_name + '?':
            return entity_name
        
        # 处理值类型
        if csharp_type in self.csharp_to_java_type:
            java_type = self.csharp_to_java_type[csharp_type]
            if sql_type in ['SELECT', 'INSERT', 'UPDATE']:
                return java_type
            return java_type
        
        # 处理int等
        if csharp_type == 'int':
            return 'int'
        
        return 'Object'

    def generate_mapper_xml(self, dao_info: Dict, mapper_name: str, entity_name: str, table_name: str = None) -> str:
        """生成MyBatis Mapper XML文件"""
        class_name = dao_info['class_name']
        
        if not table_name:
            # 将类名转换为表名（下划线命名）
            table_name = self.camel_to_snake(entity_name)
        
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="mapper.{mapper_name}">

    <!-- 基础结果映射 -->
    <resultMap id="BaseResultMap" type="{entity_name}">
        <!-- TODO: 根据实体类配置字段映射 -->
        <!--
        <id column="id" property="id" jdbcType="BIGINT"/>
        <result column="create_time" property="createTime" jdbcType="TIMESTAMP"/>
        -->
    </resultMap>

    <!-- 基础字段列表 -->
    <sql id="Base_Column_List">
        <!-- TODO: 配置所有字段 -->
    </sql>

'''
        
        # 为每个方法生成SQL
        for method in dao_info['methods']:
            sql_id = method['name']
            sql_type = method['sql_type']
            
            if sql_type == 'SELECT':
                xml += self.generate_select_sql(sql_id, method, table_name, entity_name)
            elif sql_type == 'INSERT':
                xml += self.generate_insert_sql(sql_id, method, table_name)
            elif sql_type == 'UPDATE':
                xml += self.generate_update_sql(sql_id, method, table_name)
            elif sql_type == 'DELETE':
                xml += self.generate_delete_sql(sql_id, method, table_name)
            
            xml += '\n'
        
        xml += '</mapper>\n'
        return xml

    def generate_select_sql(self, sql_id: str, method: Dict, table_name: str, entity_name: str) -> str:
        """生成SELECT语句"""
        params = method['parameters']
        
        # 构建WHERE条件
        where_clause = ""
        if params:
            conditions = []
            for param in params:
                conditions.append(f"            AND {self.camel_to_snake(param['name'])} = #{{{param['name']}}}")
            where_clause = "        WHERE 1=1\n" + "\n".join(conditions)
        
        xml = f'''    <!-- {sql_id} -->
    <select id="{sql_id}" resultMap="BaseResultMap" parameterType="map">
        SELECT
        <include refid="Base_Column_List"/>
        FROM {table_name}
{where_clause}
    </select>

'''
        return xml

    def generate_insert_sql(self, sql_id: str, method: Dict, table_name: str) -> str:
        """生成INSERT语句"""
        params = method['parameters']
        
        if not params:
            return f'''    <!-- {sql_id} -->
    <insert id="{sql_id}">
        INSERT INTO {table_name}
        <!-- TODO: 配置插入字段 -->
    </insert>

'''
        
        columns = [self.camel_to_snake(p['name']) for p in params]
        values = [f"#{{{p['name']}}}" for p in params]
        
        xml = f'''    <!-- {sql_id} -->
    <insert id="{sql_id}" parameterType="map">
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
            return f'''    <!-- {sql_id} -->
    <update id="{sql_id}">
        UPDATE {table_name}
        <!-- TODO: 配置更新字段 -->
    </update>

'''
        
        # 假设第一个参数是ID或其他条件
        set_clause = []
        where_clause = ""
        
        for i, param in enumerate(params):
            if i == 0 and param['name'].lower() in ['id', 'ids']:
                where_clause = f"        WHERE {self.camel_to_snake(param['name'])} = #{{{param['name']}}}"
            else:
                set_clause.append(f"            {self.camel_to_snake(param['name'])} = #{{{param['name']}}}")
        
        set_str = ",\n".join(set_clause) if set_clause else "            <!-- TODO: 配置更新字段 -->"
        
        xml = f'''    <!-- {sql_id} -->
    <update id="{sql_id}" parameterType="map">
        UPDATE {table_name}
        SET
{set_str}
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
                conditions.append(f"            AND {self.camel_to_snake(param['name'])} = #{{{param['name']}}}")
            where_clause = "        WHERE 1=1\n" + "\n".join(conditions)
        
        xml = f'''    <!-- {sql_id} -->
    <delete id="{sql_id}" parameterType="map">
        DELETE FROM {table_name}
{where_clause}
    </delete>

'''
        return xml

    def camel_to_snake(self, name: str) -> str:
        """驼峰命名转下划线命名"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def convert_file(self, input_file: str, output_dir: str = "./output", entity_name: str = None, table_name: str = None):
        """转换单个C# DAO文件"""
        # 读取C#文件
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析C# DAO
        dao_info = self.parse_csharp_dao(content)
        
        if not dao_info['class_name']:
            print(f"无法解析文件: {input_file}")
            return
        
        # 创建输出目录
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        Path(f"{output_dir}/java").mkdir(parents=True, exist_ok=True)
        Path(f"{output_dir}/xml").mkdir(parents=True, exist_ok=True)
        
        # 生成Java Mapper
        java_code, mapper_name, auto_entity_name = self.generate_mapper_java(dao_info, entity_name)
        
        # 生成XML
        xml_code = self.generate_mapper_xml(dao_info, mapper_name, auto_entity_name, table_name)
        
        # 保存文件
        java_file = f"{output_dir}/java/{mapper_name}.java"
        xml_file = f"{output_dir}/xml/{mapper_name}.xml"
        
        with open(java_file, 'w', encoding='utf-8') as f:
            f.write(java_code)
        
        with open(xml_file, 'w', encoding='utf-8') as f:
            f.write(xml_code)
        
        print(f"转换完成:")
        print(f"  Java Mapper: {java_file}")
        print(f"  XML Mapper: {xml_file}")
        print(f"  实体类名: {auto_entity_name}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='将C# DAO转换为Java MyBatis Mapper')
    parser.add_argument('input', help='输入的C# DAO文件路径')
    parser.add_argument('-o', '--output', default='./output', help='输出目录 (默认: ./output)')
    parser.add_argument('-e', '--entity', help='实体类名 (默认: 自动推断)')
    parser.add_argument('-t', '--table', help='数据库表名 (默认: 根据实体名转换)')
    
    args = parser.parse_args()
    
    converter = CSharpToJavaMapperConverter()
    converter.convert_file(args.input, args.output, args.entity, args.table)

if __name__ == "__main__":
    # 示例用法
    # python csharp_dao_to_mapper.py input/UserDAO.cs -o ./mybatis -e User -t t_user
    
    # 如果没有命令行参数，运行示例
    import sys
    if len(sys.argv) == 1:
        # 示例代码
        example_csharp = """
using System;
using System.Collections.Generic;

namespace MyApp.DAO
{
    public class UserDAO
    {
        public User GetUserById(int id)
        {
            // 获取用户
            return null;
        }
        
        public List<User> GetUsersByName(string name, int age)
        {
            // 获取用户列表
            return null;
        }
        
        public int InsertUser(User user)
        {
            // 插入用户
            return 1;
        }
        
        public bool UpdateUser(string name, int id)
        {
            // 更新用户
            return true;
        }
        
        public void DeleteUser(int id)
        {
            // 删除用户
        }
    }
}
"""
        # 保存示例文件
        with open("example_UserDAO.cs", "w", encoding='utf-8') as f:
            f.write(example_csharp)
        
        print("示例文件已创建: example_UserDAO.cs")
        print("运行转换...")
        converter = CSharpToJavaMapperConverter()
        converter.convert_file("example_UserDAO.cs", "./example_output")
    else:
        main()
