import re
import sys
from pathlib import Path

class ASPToThymeleafConverter:
    """
    将ASP.NET标签和表达式转换为Thymeleaf格式的Python工具
    支持: <%= %>, <%: %>, <%# %>, <%$ %>, 以及runat="server"控件
    """

    def __init__(self):
        # 转换规则: (ASP模式, Thymeleaf替换, 标志)
        self.rules = [
            # 输出表达式: <%= xxx %>  -> th:text="${xxx}"
            (re.compile(r'<%=([^%]+)%>', re.IGNORECASE),
             r'th:text="${ \1 }"'),

            # HTML编码输出: <%: xxx %> -> th:utext="${xxx}" (注意: Thymeleaf需要转义, 使用utext)
            (re.compile(r'<%:([^%]+)%>', re.IGNORECASE),
             r'th:utext="${ \1 }"'),

            # 数据绑定表达式: <%# xxx %> -> th:text="${xxx}" (通常用于数据绑定)
            (re.compile(r'<%#([^%]+)%>', re.IGNORECASE),
             r'th:text="${ \1 }"'),

            # 资源表达式: <%$ Resources:xxx, yyy %> -> Thymeleaf中需要自定义处理，暂时转为#messages.xxx
            (re.compile(r'<%\$ Resources:([^,]+),([^%]+)%>', re.IGNORECASE),
             r'th:text="#{ \1.\2 }"'),

            # 服务器端注释: <%-- ... --%> -> 转换为Thymeleaf注释: <!--/* ... */-->
            (re.compile(r'<%--(.*?)--%>', re.DOTALL | re.IGNORECASE),
             r'<!--/*\1*/-->'),

            # 服务器端包含指令: <!--#include file="..." --> 或 <%@ include ... %> -> th:replace
            (re.compile(r'<%@\s+include\s+file="([^"]+)"\s*%>', re.IGNORECASE),
             r'th:replace="~{\1}"'),

            # 服务器端脚本块: <script runat="server"> ... </script> -> 需要移除或特殊标记
            (re.compile(r'<script\s+runat="server"[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE),
             r'<!-- ASP removed script block: \1 -->'),
        ]

        # 控件属性转换: 处理runat="server"的控件，将属性转换为th:attr或移除
        self.control_patterns = [
            # 提取标签并转换ID/runat等
            (re.compile(r'(<(?:asp:\w+|[^>]+))\s+runat="server"([^>]*>)', re.IGNORECASE),
             r'\1\2'),  # 简单移除runat="server"

            # asp:Label -> 保留为span或div，添加th属性
            (re.compile(r'<asp:Label\s+id="([^"]+)"[^>]*>(.*?)</asp:Label>', re.DOTALL | re.IGNORECASE),
             r'<span th:text="${#fields.hasErrors(\1) ? #fields.errors(\1) : \2}" id="\1"></span>'),

            # asp:TextBox -> 转换为input并尝试绑定
            (re.compile(r'<asp:TextBox\s+id="([^"]+)"[^>]*>(.*?)</asp:TextBox>', re.DOTALL | re.IGNORECASE),
             r'<input type="text" th:value="*\1" id="\1" />'),

            # asp:Button -> 转换为button
            (re.compile(r'<asp:Button\s+id="([^"]+)"\s+text="([^"]+)"[^>]*/>', re.IGNORECASE),
             r'<button type="submit" th:text="\2" id="\1"></button>'),
        ]

    def convert_expression(self, content):
        """转换内联表达式"""
        for pattern, replacement in self.rules:
            content = pattern.sub(replacement, content)
        return content

    def convert_controls(self, content):
        """转换服务器控件"""
        for pattern, replacement in self.control_patterns:
            content = pattern.sub(replacement, content)
        return content

    def convert_attributes(self, content):
        """
        转换其他常见属性:
        - EnableViewState -> th:remove 或忽略
        - Visible="false" -> th:if 或 style="display: none"
        - DataSourceID -> th:each等
        """
        # Visible false 转换为 th:if="false" 包装内容 (简单处理)
        content = re.sub(r'Visible="false"', r'th:if="false"', content, flags=re.IGNORECASE)
        # 移除EnableViewState
        content = re.sub(r'\s+EnableViewState="[^"]*"', '', content, flags=re.IGNORECASE)
        # 将CssClass替换为class
        content = re.sub(r'CssClass="([^"]+)"', r'class="\1"', content, flags=re.IGNORECASE)
        return content

    def convert(self, aspx_content):
        """执行完整转换"""
        content = aspx_content
        content = self.convert_expression(content)
        content = self.convert_controls(content)
        content = self.convert_attributes(content)

        # 添加文件头提示
        header = "<!-- Converted from ASPX to Thymeleaf. Please review manually. -->\n"
        header += "<html xmlns:th=\"http://www.thymeleaf.org\">\n"
        # 确保body内转换
        if "<body" not in content:
            content = "<body>\n" + content + "\n</body>"
        return header + content

def convert_file(input_path, output_path=None):
    """转换文件"""
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"错误: 文件 {input_path} 不存在")
        return False

    if output_path is None:
        output_path = input_file.stem + "_thymeleaf.html"

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        converter = ASPToThymeleafConverter()
        converted = converter.convert(content)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(converted)

        print(f"转换完成: {output_path}")
        return True
    except Exception as e:
        print(f"转换错误: {e}")
        return False

def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python asp_to_thymeleaf.py <input.aspx> [output.html]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    convert_file(input_file, output_file)

if __name__ == "__main__":
    # 示例用法
    sample_aspx = """
    <%@ Page Language="C#" %>
    <!DOCTYPE html>
    <html>
    <head>
        <title><%= Page.Title %></title>
    </head>
    <body>
        <form id="form1" runat="server">
            <asp:Label ID="lblMessage" runat="server" Text="Hello, world!" CssClass="message" />
            <asp:TextBox ID="txtName" runat="server" />
            <asp:Button ID="btnSubmit" runat="server" Text="Submit" />

            <%-- 服务器端注释 --%>
            <div>
                <%: Server.HtmlEncode(userInput) %>
                <%= DateTime.Now %>
            </div>

            <script runat="server">
                protected void Page_Load(object sender, EventArgs e) {
                    // 服务器代码
                }
            </script>
        </form>
    </body>
    </html>
    """

    print("===== 转换示例 =====")
    conv = ASPToThymeleafConverter()
    result = conv.convert(sample_aspx)
    print(result)

    # 如果命令行调用，转换文件
    if len(sys.argv) > 1:
        main()
