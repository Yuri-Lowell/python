import re
import os
from pathlib import Path
from typing import List, Dict, Tuple
import argparse

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
            'Guid?': 'String',
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
            # 递归查找所有.cs文件
            for cs_file in input_path.rglob('*.cs'):
                # 检查文件名是否包含DAO或Repository
                if 'DAO' in cs_file.stem or 'Repository' in cs_file.stem or 'Dao' in cs_file.stem:
                    dao_files.append(str(cs_file))
                else:
                    # 也可以检查文件内容是否包含DAO特征
                    try:
                        with open(cs_file, 'r', encoding='utf-8') as f:
                            content = f.read(1000)  # 只读前1000字符
                            if re.search(r'class\s+\w*(?:DAO|Repository|Dao)\w*', content, re.IGNORECASE):
                                dao_files.append(str(cs_file))
                    except:
                        pass
        
        return dao_files

    def parse_csharp_dao(self, file_content: str) -> Dict:
        """解析C# DAO文件，提取类名和方法信息"""
        result = {
            'namespace': '',
            'class_name': '',
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
        
        # 提取类名（包括泛型）
        class_match = re.search(r'class\s+(\w+)(?:<[^>]+>)?(?:\s*:\s*\w+(?:<[^>]+>)?)?', file_content)
        if class_match:
            result['class_name'] = class_match.group(1)
        
        # 提取方法 - 支持更多C#语法
        method_pattern = r'''
            (?:public|private|protected|internal)\s+     # 访问修饰符
            (?:static\s+)?                               # 可选的static
            (?:virtual\s+)?                              # 可选的virtual
            (?:override\s+)?                             # 可选的override
            (?:async\s+)?                                # 可选的async
            (?:Task<)?                                    # 可选的Task<前缀
            (\w+(?:<[^>]+>)?)                             # 返回类型
            (?:>)?                                        # 可选的>后缀
            \s+(\w+)\s*                                   # 方法名
            \(([^)]*)\)                                   # 参数列表
        '''
        
        methods = re.finditer(method_pattern, file_content, re.VERBOSE)
        
        for method in methods:
            return_type = method.group(1)
            method_name = method.group(2)
            parameters_str = method.group(3)
            
            # 跳过构造函数和属性
            if method_name == result['class_name'] or return_type in ['get', 'set']:
                continue
            
            # 解析参数
            parameters = self.parse_parameters(parameters_str)
            
            # 推断SQL操作类型
            sql_type = self.infer_sql_type(method_name)
            
            # 检查是否可能有返回实体
            returns_entity = self.is_entity_type(return_type, result['class_name'])
            
            result['methods'].append({
                'name': method_name,
                'return_type': return_type,
                'parameters': parameters,
                'sql_type': sql_type,
                'returns_entity': returns_entity
            })
        
        return result

    def parse_parameters(self, params_str: str) -> List[Dict]:
        """解析方法参数，支持复杂类型"""
        if not params_str or params_str.strip() == '':
            return []
        
        parameters = []
        
        # 处理参数中的泛型和复杂类型
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
            
            # 匹配参数类型和名称（支持默认值和特性）
            # 格式: [Attribute] Type paramName = defaultValue
            match = re.match(r'(?:\[.*?\])?\s*(\w+(?:<[^>]+>)?(?:\?)?)\s+(\w+)(?:\s*=.*)?', param)
            if match:
                param_type = match.group(1)
                param_name = match.group(2)
                
                # 映射Java类型
                java_type = self.map_to_java_type(param_type)
                
                parameters.append({
                    'csharp_type': param_type,
                    'java_type': java_type,
                    'name': param_name,
                    'annotation': '@Param("' + param_name + '")'
                })
        
        return parameters

    def map_to_java_type(self, csharp_type: str) -> str:
        """将C#类型映射到Java类型"""
        # 处理泛型
        if '<' in csharp_type:
            base_type = csharp_type[:csharp_type.index('<')]
            inner_type = csharp_type[csharp_type.index('<')+1:csharp_type.rindex('>')]
            
            if base_type in ['List', 'IEnumerable', 'ICollection']:
                return f'List<{self.map_to_java_type(inner_type)}>'
            elif base_type == 'Dictionary':
                return f'Map<{self.map_to_java_type(inner_type.split(",")[0].strip())}, {self.map_to_java_type(inner_type.split(",")[1].strip())}>'
        
        # 基本类型映射
        base_type = csharp_type.rstrip('?')
        java_type = self.csharp_to_java_type.get(base_type, base_type)
        
        # 首字母大写（如果是自定义类型）
        if java_type not in self.csharp_to_java_type.values() and java_type != 'void':
            java_type = java_type[0].upper() + java_type[1:] if java_type else java_type
        
        return java_type

    def is_entity_type(self, return_type: str, dao_class_name: str) -> bool:
        """判断返回类型是否为实体类型"""
        # 移除泛型标记
        clean_type = return_type.split('<')[0].rstrip('?')
        
        # 排除基本类型
        basic_types = ['int', 'long', 'string', 'bool', 'boolean', 'DateTime', 
                      'decimal', 'double', 'float', 'Guid', 'void', 'Task']
        
        if clean_type in basic_types:
            return False
        
        # 如果是集合类型，检查内部类型
        if '<' in return_type:
            inner_match = re.search(r'<(\w+)>', return_type)
            if inner_match:
                inner_type = inner_match.group(1)
                return inner_type not in basic_types
        
        # 排除DAO类本身
        if clean_type == dao_class_name:
            return False
        
        return True

    def infer_sql_type(self, method_name: str) -> str:
        """根据方法名推断SQL操作类型"""
        method_lower = method_name.lower()
        
        # SELECT操作
        if any(method_lower.startswith(prefix) for prefix in ['get', 'select', 'find', 'query', 'fetch', 'retrieve']):
            return 'SELECT'
        # INSERT操作
        elif any(method_lower.startswith(prefix) for prefix in ['insert', 'add', 'create', 'save']):
            return 'INSERT'
        # UPDATE操作
        elif any(method_lower.startswith(prefix) for prefix in ['update', 'modify', 'edit', 'change', 'set']):
            return 'UPDATE'
        # DELETE操作
        elif any(method_lower.startswith(prefix) for prefix in ['delete', 'remove', 'erase', 'clear']):
            return 'DELETE'
        # COUNT操作
        elif any(method_lower.startswith(prefix) for prefix in ['count', 'total']):
            return 'SELECT'
        # EXISTS操作
        elif any(method_lower.startswith(prefix) for prefix in ['exists', 'contain']):
            return 'SELECT'
        else:
            return 'SELECT'

    def generate_mapper_java(self, dao_info: Dict, entity_name: str = None) -> Tuple[str, str, str]:
        """生成Java Mapper接口代码"""
        class_name = dao_info['class_name']
        
        # 生成包名（基于namespace）
        package_name = self.convert_namespace_to_package(dao_info['namespace'])
        
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
        
        # 收集需要导入的类型
        for method in dao_info['methods']:
            # 返回类型
            return_type = self.map_to_java_type(method['return_type'])
            if return_type.startswith('List<'):
                imports.add('java.util.List')
            elif return_type.startswith('Map<'):
                imports.add('java.util.Map')
            
            # 参数类型
            for param in method['parameters']:
                java_type = param['java_type']
                if java_type in ['Date']:
                    imports.add('java.util.Date')
                elif java_type in ['BigDecimal']:
                    imports.add('java.math.BigDecimal')
                elif java_type in ['List']:
                    imports.add('java.util.List')
                elif java_type in ['Map']:
                    imports.add('java.util.Map')
        
        # 添加实体类导入
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
 */
@Mapper
public interface {mapper_name} {{

"""
        
        # 生成方法
        for method in dao_info['methods']:
            # 转换返回类型
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
                f"     * {method['name']}",
                f"     * SQL操作类型: {method['sql_type']}",
                "     *",
            ]
            
            for param in method['parameters']:
                comment_lines.append(f"     * @param {param['name']} 参数说明")
            
            comment_lines.append(f"     * @return {return_type}")
            comment_lines.append("     */")
            
            comment = '\n'.join(comment_lines)
            
            # 生成方法定义
            method_code = f"""
{comment}
    {return_type} {method['name']}({param_str});
"""
            java_code += method_code + "\n"
        
        java_code += "}\n"
        return java_code, mapper_name, entity_name, package_name

    def convert_namespace_to_package(self, namespace: str) -> str:
        """将C#命名空间转换为Java包名"""
        if not namespace:
            return "mapper"
        
        # 转换为小写
        package = namespace.lower()
        
        # 替换常见的命名空间
        replacements = {
            'myapp': 'com.company',
            'dao': 'mapper',
            'dal': 'mapper',
            'repository': 'mapper'
        }
        
        for old, new in replacements.items():
            if package.startswith(old):
                package = package.replace(old, new, 1)
                break
        
        # 确保以mapper结尾
        if not package.endswith('mapper'):
            package += '.mapper'
        
        return package

    def convert_return_type(self, method: Dict, entity_name: str) -> str:
        """转换返回类型"""
        return_type = method['return_type']
        sql_type = method['sql_type']
        
        # 处理异步方法
        if return_type.lower() == 'task':
            return 'void'
        
        # 处理集合类型
        if 'List<' in return_type or 'IEnumerable<' in return_type or 'ICollection<' in return_type:
            # 提取泛型类型
            match = re.search(r'<(\w+)>', return_type)
            if match:
                inner_type = match.group(1)
                java_inner_type = self.map_to_java_type(inner_type)
                if java_inner_type == inner_type and inner_type != 'Object':
                    # 可能是实体类
                    return f'List<{entity_name}>'
                return f'List<{java_inner_type}>'
            return f'List<{entity_name}>'
        
        # 处理单个实体
        if method['returns_entity'] or return_type == entity_name:
            return entity_name
        
        # 处理值类型
        java_type = self.map_to_java_type(return_type)
        
        # 对于SELECT操作，如果返回int/long，可能表示count
        if sql_type == 'SELECT' and java_type in ['Integer', 'Long', 'int', 'long']:
            return java_type
        
        return java_type if java_type != 'void' else 'void'

    def generate_mapper_xml(self, dao_info: Dict, mapper_name: str, entity_name: str, table_name: str = None) -> str:
        """生成MyBatis Mapper XML文件"""
        class_name = dao_info['class_name']
        
        if not table_name:
            # 将实体名转换为表名（下划线命名）
            table_name = self.camel_to_snake(entity_name)
        
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="mapper.{mapper_name}">

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
        method_lower = method['name'].lower()
        
        # 判断是否是count查询
        is_count = 'count' in method_lower or 'total' in method_lower
        
        # 判断是否是exists查询
        is_exists = 'exists' in method_lower or 'contain' in method_lower
        
        # 构建WHERE条件
        where_clause = ""
        if params:
            conditions = []
            for param in params:
                conditions.append(f"            <if test=\"{param['name']} != null\">\n                AND {self.camel_to_snake(param['name'])} = #{{{param['name']}}}\n            </if>")
            where_clause = "        <where>\n" + "\n".join(conditions) + "\n        </where>"
        else:
            where_clause = "        <!-- 添加WHERE条件 -->"
        
        # 选择返回类型
        if is_count:
            result_type = "int"
            select_clause = "COUNT(*)"
        elif is_exists:
            result_type = "int"
            select_clause = "COUNT(1)"
        else:
            result_type = "BaseResultMap"
            select_clause = "<include refid=\"Base_Column_List\"/>"
        
        xml = f'''    <!-- ========== {sql_id} ========== -->
    <select id="{sql_id}" {"resultType=\"" + result_type + "\"" if result_type != "BaseResultMap" else "resultMap=\"BaseResultMap\""} parameterType="map">
        SELECT {select_clause}
        FROM {table_name}
{where_clause}
    </select>

'''
        return xml

    def generate_insert_sql(self, sql_id: str, method: Dict, table_name: str) -> str:
        """生成INSERT语句"""
        params = method['parameters']
        
        # 检查是否有实体参数
        entity_param = None
        for param in params:
            if param['java_type'] not in self.csharp_to_java_type.values():
                entity_param = param
                break
        
        if entity_param:
            # 如果有实体参数，使用更复杂的插入
            xml = f'''    <!-- ========== {sql_id} ========== -->
    <insert id="{sql_id}" parameterType="{entity_param['java_type']}" useGeneratedKeys="true" keyProperty="id">
        INSERT INTO {table_name} (
            <!-- TODO: 配置需要插入的字段 -->
            <include refid="Base_Column_List"/>
        ) VALUES (
            <!-- TODO: 配置对应的值 -->
            <foreach collection="{entity_param['name']}" item="item" separator=",">
                #{'{item.xxx}'}
            </foreach>
        )
    </insert>

'''
        else:
            # 简单插入
            columns = [self.camel_to_snake(p['name']) for p in params]
            values = [f"#{{{p['name']}}}" for p in params]
            
            if columns:
                xml = f'''    <!-- ========== {sql_id} ========== -->
    <insert id="{sql_id}" parameterType="map">
        INSERT INTO {table_name} (
            {', '.join(columns)}
        ) VALUES (
            {', '.join(values)}
        )
    </insert>

'''
            else:
                xml = f'''    <!-- ========== {sql_id} ========== -->
    <insert id="{sql_id}">
        INSERT INTO {table_name}
        <!-- TODO: 配置插入字段和值 -->
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
        
        # 智能识别ID参数和更新参数
        id_params = []
        update_params = []
        
        for param in params:
            if param['name'].lower() in ['id', 'ids', 'key', 'primarykey']:
                id_params.append(param)
            else:
                update_params.append(param)
        
        # 构建SET子句
        set_clause = []
        for param in update_params:
            set_clause.append(f"            <if test=\"{param['name']} != null\">\n                {self.camel_to_snake(param['name'])} = #{{{param['name']}}},\n            </if>")
        
        set_str = "\n".join(set_clause) if set_clause else "            <!-- TODO: 配置更新字段 -->"
        
        # 构建WHERE子句
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

    def camel_to_snake(self, name: str) -> str:
        """驼峰命名转下划线命名"""
        # 处理首字母大写的情况
        if name and name[0].isupper():
            name = name[0].lower() + name[1:]
        
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def convert_file(self, input_file: str, output_dir: str = "./output", 
                    entity_name: str = None, table_name: str = None,
                    preserve_structure: bool = False, base_path: str = None) -> bool:
        """转换单个C# DAO文件"""
        try:
            # 读取C#文件
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析C# DAO
            dao_info = self.parse_csharp_dao(content)
            
            if not dao_info['class_name'] or not dao_info['methods']:
                print(f"  ⚠️  跳过: {input_file} (没有找到有效方法)")
                return False
            
            # 确定输出路径
            if preserve_structure and base_path:
                rel_path = os.path.relpath(input_file, base_path)
                output_subdir = os.path.dirname(rel_path)
                java_output_dir = os.path.join(output_dir, "java", output_subdir)
                xml_output_dir = os.path.join(output_dir, "xml", output_subdir)
            else:
                java_output_dir = os.path.join(output_dir, "java")
                xml_output_dir = os.path.join(output_dir, "xml")
            
            # 创建输出目录
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
            print(f"     Java: {java_file}")
            print(f"     XML:  {xml_file}")
            return True
            
        except Exception as e:
            print(f"  ❌ 转换失败: {input_file}")
            print(f"     错误: {str(e)}")
            return False

    def convert_folder(self, input_folder: str, output_dir: str = "./output",
                      entity_name: str = None, table_name: str = None,
                      recursive: bool = True, preserve_structure: bool = False):
        """转换文件夹中的所有C# DAO文件"""
        print(f"\n{'='*60}")
        print(f"开始转换C# DAO文件")
        print(f"输入路径: {input_folder}")
        print(f"输出目录: {output_dir}")
        print(f"{'='*60}\n")
        
        # 查找所有DAO文件
        dao_files = self.find_dao_files(input_folder)
        
        if not dao_files:
            print("未找到任何C# DAO文件")
            return
        
        print(f"找到 {len(dao_files)} 个C# DAO文件\n")
        
        # 转换统计
        success_count = 0
        fail_count = 0
        
        # 转换每个文件
        base_path = input_folder if preserve_structure else None
        
        for i, dao_file in enumerate(dao_files, 1):
            print(f"[{i}/{len(dao_files)}] 处理: {dao_file}")
            
            if self.convert_file(dao_file, output_dir, entity_name, table_name, 
                               preserve_structure, base_path):
                success_count += 1
            else:
                fail_count += 1
            print()
        
        # 输出总结
        print(f"{'='*60}")
        print(f"转换完成!")
        print(f"成功: {success_count} 个文件")
        print(f"失败: {fail_count} 个文件")
        print(f"输出目录: {output_dir}")
        print(f"{'='*60}\n")
        
        # 生成汇总报告
        self.generate_summary_report(output_dir, success_count, fail_count)

    def generate_summary_report(self, output_dir: str, success_count: int, fail_count: int):
        """生成转换汇总报告"""
        report_path = os.path.join(output_dir, "conversion_report.txt")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("C# DAO to Java MyBatis Mapper 转换报告\n")
            f.write("="*60 + "\n")
            f.write(f"转换时间: {self.get_current_time()}\n")
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
        
        print(f"转换报告已生成: {report_path}")

    def get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    parser = argparse.ArgumentParser(
        description='将C# DAO文件夹转换为Java MyBatis Mapper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 转换单个文件
  python csharp_dao_to_mapper.py -i UserDAO.cs
  
  # 转换整个文件夹
  python csharp_dao_to_mapper.py -i ./CSharpProject/DAL
  
  # 递归转换并保持目录结构
  python csharp_dao_to_mapper.py -i ./CSharpProject -o ./mybatis -r -s
  
  # 指定实体类和表名
  python csharp_dao_to_mapper.py -i UserDAO.cs -e User -t t_user
        """
    )
    
    parser.add_argument('-i', '--input', required=True, help='输入的C#文件或文件夹路径')
    parser.add_argument('-o', '--output', default='./mybatis_output', help='输出目录 (默认: ./mybatis_output)')
    parser.add_argument('-e', '--entity', help='实体类名 (默认: 自动推断)')
    parser.add_argument('-t', '--table', help='数据库表名 (默认: 根据实体名转换)')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归搜索子文件夹')
    parser.add_argument('-s', '--preserve-structure', action='store_true', help='保持原始目录结构')
    
    args = parser.parse_args()
    
    converter = CSharpToJavaMapperConverter()
    
    # 检查输入路径
    if os.path.isfile(args.input):
        # 转换单个文件
        print(f"\n转换单个文件: {args.input}")
        converter.convert_file(args.input, args.output, args.entity, args.table)
    elif os.path.isdir(args.input):
        # 转换文件夹
        converter.convert_folder(args.input, args.output, args.entity, args.table, 
                               args.recursive, args.preserve_structure)
    else:
        print(f"错误: 路径不存在 - {args.input}")

if __name__ == "__main__":
    main()
