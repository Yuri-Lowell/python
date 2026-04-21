import os
import re
from pathlib import Path
from bs4 import BeautifulSoup

class MaterialWebConverter:
    def __init__(self):
        # 转换规则映射
        self.conversion_rules = {
            'button': self.convert_button,
            'input': self.convert_input,
            'textarea': self.convert_textarea,
            'select': self.convert_select,
            'checkbox': self.convert_checkbox,
            'radio': self.convert_radio,
            'progress': self.convert_progress,
            'div_card': self.convert_card
        }
    
    def convert_button(self, element, soup):
        """转换按钮 - 使用 outlined 样式"""
        button_text = element.get_text(strip=True)
        button_id = element.get('id', '')
        button_class = element.get('class', [])
        
        new_button = soup.new_tag('md-outlined-button')
        if button_id:
            new_button['id'] = button_id
        if button_class:
            new_button['class'] = ' '.join(button_class)
        
        # 处理禁用状态
        if element.get('disabled'):
            new_button['disabled'] = ''
        
        # 处理点击事件
        onclick = element.get('onclick', '')
        if onclick:
            new_button['onclick'] = onclick
        
        new_button.string = button_text
        return new_button
    
    def convert_input(self, element, soup):
        """转换输入框 - 使用 filled 样式"""
        input_type = element.get('type', 'text')
        
        if input_type == 'text' or input_type == 'email' or input_type == 'password':
            return self.convert_text_field(element, soup)
        elif input_type == 'checkbox':
            return self.convert_checkbox(element, soup)
        elif input_type == 'radio':
            return self.convert_radio(element, soup)
        elif input_type == 'submit' or input_type == 'reset':
            return self.convert_button(element, soup)
        else:
            return element
    
    def convert_text_field(self, element, soup):
        """转换文本输入框 - filled"""
        input_type = element.get('type', 'text')
        placeholder = element.get('placeholder', '')
        value = element.get('value', '')
        input_id = element.get('id', '')
        input_name = element.get('name', '')
        required = element.get('required', False)
        disabled = element.get('disabled', False)
        
        new_input = soup.new_tag('md-filled-text-field')
        
        if input_id:
            new_input['id'] = input_id
        if input_name:
            new_input['name'] = input_name
        if placeholder:
            new_input['label'] = placeholder
        if value:
            new_input['value'] = value
        if input_type == 'password':
            new_input['type'] = 'password'
        if required:
            new_input['required'] = ''
        if disabled:
            new_input['disabled'] = ''
        
        return new_input
    
    def convert_textarea(self, element, soup):
        """转换文本域 - filled"""
        placeholder = element.get('placeholder', '')
        rows = element.get('rows', '3')
        textarea_id = element.get('id', '')
        textarea_name = element.get('name', '')
        value = element.get_text(strip=True)
        
        new_textarea = soup.new_tag('md-filled-text-field')
        
        if textarea_id:
            new_textarea['id'] = textarea_id
        if textarea_name:
            new_textarea['name'] = textarea_name
        if placeholder:
            new_textarea['label'] = placeholder
        if value:
            new_textarea['value'] = value
        
        # 设置为多行模式
        new_textarea['type'] = 'textarea'
        new_textarea['rows'] = rows
        
        return new_textarea
    
    def convert_select(self, element, soup):
        """转换下拉菜单 - filled"""
        select_id = element.get('id', '')
        select_name = element.get('name', '')
        label = element.get('label', '请选择')
        
        new_select = soup.new_tag('md-filled-select')
        
        if select_id:
            new_select['id'] = select_id
        if select_name:
            new_select['name'] = select_name
        
        new_select['label'] = label
        
        # 转换选项
        for option in element.find_all('option'):
            new_option = soup.new_tag('md-select-option')
            new_option['value'] = option.get('value', '')
            
            if option.get('selected'):
                new_option['selected'] = ''
            
            headline = soup.new_tag('div', slot='headline')
            headline.string = option.get_text(strip=True)
            new_option.append(headline)
            
            new_select.append(new_option)
        
        return new_select
    
    def convert_checkbox(self, element, soup):
        """转换复选框 - filled"""
        checkbox_id = element.get('id', '')
        checkbox_name = element.get('name', '')
        checked = element.get('checked', False)
        disabled = element.get('disabled', False)
        
        # 创建复选框包装
        wrapper = soup.new_tag('div', **{'class': 'material-checkbox-wrapper'})
        
        new_checkbox = soup.new_tag('md-checkbox')
        
        if checkbox_id:
            new_checkbox['id'] = checkbox_id
        if checkbox_name:
            new_checkbox['name'] = checkbox_name
        if checked:
            new_checkbox['checked'] = ''
        if disabled:
            new_checkbox['disabled'] = ''
        
        new_checkbox['touch-target'] = 'wrapper'
        wrapper.append(new_checkbox)
        
        # 如果有标签文本，添加label
        parent = element.parent
        if parent and parent.name == 'label':
            label_text = parent.get_text(strip=True).replace(element.get_text(strip=True), '').strip()
            if label_text:
                new_label = soup.new_tag('label', **{'for': checkbox_id})
                new_label.string = label_text
                wrapper.append(new_label)
                # 移除原始label
                parent.replace_with(wrapper)
                return wrapper
        else:
            # 检查相邻文本节点
            next_sibling = element.next_sibling
            if next_sibling and isinstance(next_sibling, str) and next_sibling.strip():
                label_text = next_sibling.strip()
                new_label = soup.new_tag('label', **{'for': checkbox_id})
                new_label.string = label_text
                wrapper.append(new_label)
                # 移除原始文本节点
                element.replace_with(wrapper)
                return wrapper
        
        return new_checkbox
    
    def convert_radio(self, element, soup):
        """转换单选按钮 - filled"""
        radio_id = element.get('id', '')
        radio_name = element.get('name', '')
        radio_value = element.get('value', '')
        checked = element.get('checked', False)
        disabled = element.get('disabled', False)
        
        wrapper = soup.new_tag('div', **{'class': 'material-radio-wrapper'})
        
        new_radio = soup.new_tag('md-radio')
        
        if radio_id:
            new_radio['id'] = radio_id
        if radio_name:
            new_radio['name'] = radio_name
        if radio_value:
            new_radio['value'] = radio_value
        if checked:
            new_radio['checked'] = ''
        if disabled:
            new_radio['disabled'] = ''
        
        new_radio['touch-target'] = 'wrapper'
        wrapper.append(new_radio)
        
        # 处理标签文本
        parent = element.parent
        if parent and parent.name == 'label':
            label_text = parent.get_text(strip=True).replace(element.get_text(strip=True), '').strip()
            if label_text:
                new_label = soup.new_tag('label', **{'for': radio_id})
                new_label.string = label_text
                wrapper.append(new_label)
                parent.replace_with(wrapper)
                return wrapper
        
        return new_radio
    
    def convert_progress(self, element, soup):
        """转换进度条 - filled"""
        max_value = element.get('max', 100)
        value = element.get('value', 0)
        
        progress_value = float(value) / float(max_value) if max_value != 0 else 0
        
        new_progress = soup.new_tag('md-linear-progress')
        new_progress['value'] = str(progress_value)
        
        return new_progress
    
    def convert_card(self, element, soup):
        """转换卡片"""
        new_card = soup.new_tag('md-card')
        
        # 提取卡片内容
        content = element.decode_contents()
        content_soup = BeautifulSoup(content, 'html.parser')
        
        # 添加内边距包装
        inner_div = soup.new_tag('div', style='padding: 16px;')
        
        # 转换卡片内的标题和内容
        for child in content_soup.children:
            if child.name == 'h3':
                child['style'] = 'margin: 0 0 8px 0;'
            elif child.name == 'p':
                child['style'] = 'margin: 0;'
            inner_div.append(child)
        
        new_card.append(inner_div)
        return new_card
    
    def add_material_imports(self, soup):
        """添加Material Web组件的导入语句"""
        # 检查是否已经存在导入
        if soup.find('script', src=re.compile(r'@material/web')):
            return soup
        
        # 在head中添加字体和图标
        head = soup.find('head')
        if not head:
            head = soup.new_tag('head')
            soup.html.insert(0, head) if soup.html else soup.append(head)
        
        # 添加字体
        font_link = soup.new_tag('link', href='https://fonts.googleapis.com/css?family=Roboto:300,400,500', rel='stylesheet')
        head.append(font_link)
        
        # 添加Material Icons
        icons_link = soup.new_tag('link', href='https://fonts.googleapis.com/css?family=Material+Icons&display=block', rel='stylesheet')
        head.append(icons_link)
        
        # 添加Material Web组件
        material_script = soup.new_tag('script', type='import', src='https://unpkg.com/@material/web@2.0.0/index.js')
        head.append(material_script)
        
        # 添加基础样式
        style = soup.new_tag('style')
        style.string = '''
            :root {
                --md-sys-color-primary: #6200ee;
                --md-sys-color-surface: #ffffff;
            }
            body {
                font-family: 'Roboto', sans-serif;
                margin: 0;
                padding: 20px;
            }
            .material-checkbox-wrapper, .material-radio-wrapper {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                margin: 8px 0;
            }
            md-filled-text-field, md-outlined-text-field, md-filled-select {
                display: block;
                margin: 16px 0;
                width: 100%;
                max-width: 400px;
            }
            md-filled-button, md-outlined-button {
                margin: 8px;
            }
            md-card {
                margin: 16px 0;
                display: block;
            }
        '''
        head.append(style)
        
        return soup
    
    def convert_html_file(self, input_path, output_path):
        """转换单个HTML文件"""
        try:
            with open(input_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # 转换按钮（使用outlined）
            for button in soup.find_all('button'):
                new_button = self.convert_button(button, soup)
                button.replace_with(new_button)
            
            # 转换submit/reset按钮
            for input_elem in soup.find_all('input', {'type': ['submit', 'reset']}):
                new_button = self.convert_button(input_elem, soup)
                input_elem.replace_with(new_button)
            
            # 转换文本输入框
            for input_elem in soup.find_all('input', {'type': ['text', 'email', 'password']}):
                new_input = self.convert_text_field(input_elem, soup)
                input_elem.replace_with(new_input)
            
            # 转换文本域
            for textarea in soup.find_all('textarea'):
                new_textarea = self.convert_textarea(textarea, soup)
                textarea.replace_with(new_textarea)
            
            # 转换下拉菜单
            for select in soup.find_all('select'):
                new_select = self.convert_select(select, soup)
                select.replace_with(new_select)
            
            # 转换复选框
            for checkbox in soup.find_all('input', {'type': 'checkbox'}):
                new_checkbox = self.convert_checkbox(checkbox, soup)
                if new_checkbox != checkbox:
                    checkbox.replace_with(new_checkbox)
            
            # 转换单选按钮
            for radio in soup.find_all('input', {'type': 'radio'}):
                new_radio = self.convert_radio(radio, soup)
                if new_radio != radio:
                    radio.replace_with(new_radio)
            
            # 转换进度条
            for progress in soup.find_all('progress'):
                new_progress = self.convert_progress(progress, soup)
                progress.replace_with(new_progress)
            
            # 转换卡片（类名包含card的div）
            for card in soup.find_all('div', class_=re.compile(r'card', re.I)):
                new_card = self.convert_card(card, soup)
                card.replace_with(new_card)
            
            # 添加Material Web导入
            soup = self.add_material_imports(soup)
            
            # 保存转换后的文件
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(str(soup))
            
            print(f"✓ 转换完成: {input_path} -> {output_path}")
            return True
            
        except Exception as e:
            print(f"✗ 转换失败: {input_path} - {str(e)}")
            return False
    
    def convert_folder(self, input_folder, output_folder=None):
        """转换整个文件夹"""
        input_path = Path(input_folder)
        
        if not input_path.exists():
            print(f"错误: 文件夹不存在 - {input_folder}")
            return
        
        # 设置输出文件夹
        if output_folder is None:
            output_folder = input_path.parent / f"{input_path.name}_material"
        else:
            output_folder = Path(output_folder)
        
        # 创建输出文件夹
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # 统计信息
        success_count = 0
        fail_count = 0
        
        # 遍历所有HTML文件
        for html_file in input_path.rglob('*.html'):
            relative_path = html_file.relative_to(input_path)
            output_file = output_folder / relative_path
            
            # 创建输出文件的目录
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            if self.convert_html_file(str(html_file), str(output_file)):
                success_count += 1
            else:
                fail_count += 1
        
        # 复制其他资源文件（CSS, JS, 图片等）
        self.copy_assets(input_path, output_folder)
        
        print(f"\n转换完成！")
        print(f"成功: {success_count} 个文件")
        print(f"失败: {fail_count} 个文件")
        print(f"输出目录: {output_folder}")
    
    def copy_assets(self, input_path, output_path):
        """复制非HTML资源文件"""
        import shutil
        
        asset_extensions = {'.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp'}
        
        for asset_file in input_path.rglob('*'):
            if asset_file.suffix.lower() in asset_extensions:
                relative_path = asset_file.relative_to(input_path)
                output_file = output_path / relative_path
                
                if not output_file.exists():
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(asset_file), str(output_file))
                    print(f"📁 复制资源: {asset_file.name}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='将HTML文件转换为Material Web组件格式')
    parser.add_argument('input', help='输入文件夹路径')
    parser.add_argument('-o', '--output', help='输出文件夹路径（可选）', default=None)
    
    args = parser.parse_args()
    
    converter = MaterialWebConverter()
    converter.convert_folder(args.input, args.output)

if __name__ == "__main__":
    # 示例用法
    # python converter.py ./my_html_folder
    # python converter.py ./my_html_folder -o ./output_folder
    
    # 如果没有命令行参数，使用示例路径
    import sys
    if len(sys.argv) == 1:
        print("用法: python converter.py <输入文件夹> [-o 输出文件夹]")
        print("\n示例:")
        print("  python converter.py ./html_files")
        print("  python converter.py ./html_files -o ./material_output")
        print("\n请输入文件夹路径: ", end='')
        input_path = input().strip()
        if input_path:
            converter = MaterialWebConverter()
            converter.convert_folder(input_path)
    else:
        main()
