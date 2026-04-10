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
        # 转换方法名：首字母小写
        method_name = self.convert_method_name(method['name'])
        
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
            f"     * {method_name}",
            f"     * 原始C#方法: {method['name']}",
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
    {return_type} {method_name}({param_str});
"""
        java_code += method_code + "\n"
    
    java_code += "}\n"
    return java_code, mapper_name, entity_name, package_name

def convert_method_name(self, method_name: str) -> str:
    """
    将C#方法名转换为Java方法名（首字母小写）
    例如: GetUserById -> getUserById
          InsertUser -> insertUser
          DeleteUserById -> deleteUserById
    """
    if not method_name:
        return method_name
    
    # 如果已经是首字母小写，直接返回
    if method_name[0].islower():
        return method_name
    
    # 首字母小写
    return method_name[0].lower() + method_name[1:]

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
        # 转换方法名：首字母小写
        sql_id = self.convert_method_name(method['name'])
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
