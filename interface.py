import os
import re
import sys
from pathlib import Path

class CSharpToJavaConverter:
    def __init__(self):
        # C# to Java type mappings
        self.type_mappings = {
            'string': 'String',
            'int': 'int',
            'long': 'long',
            'double': 'double',
            'float': 'float',
            'bool': 'boolean',
            'byte': 'byte',
            'char': 'char',
            'short': 'short',
            'object': 'Object',
            'void': 'void',
            'DateTime': 'LocalDateTime',
            'decimal': 'BigDecimal',
            'IEnumerable': 'Iterable',
            'IList': 'List',
            'ICollection': 'Collection',
            'IDictionary': 'Map',
            'Task': 'CompletableFuture',
        }
        
        # C# keywords that need to be escaped in Java if used as identifiers
        self.java_keywords = {
            'abstract', 'continue', 'for', 'new', 'switch', 'assert', 'default', 
            'goto', 'package', 'synchronized', 'boolean', 'do', 'if', 'private', 
            'this', 'break', 'double', 'implements', 'protected', 'throw', 'byte', 
            'else', 'import', 'public', 'throws', 'case', 'enum', 'instanceof', 
            'return', 'transient', 'catch', 'extends', 'int', 'short', 'try', 
            'char', 'final', 'interface', 'static', 'void', 'class', 'finally', 
            'long', 'strictfp', 'volatile', 'const', 'float', 'native', 'super', 
            'while'
        }

    def convert_file(self, input_path: str, output_path: str = None):
        """Convert a single C# interface file to Java"""
        try:
            with open(input_path, 'r', encoding='utf-8') as file:
                csharp_code = file.read()
            
            # Convert the code
            java_code = self.convert_interface(csharp_code)
            
            # Determine output path
            if output_path is None:
                output_path = input_path.replace('.cs', '.java')
            
            # Write the converted code
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(java_code)
            
            print(f"✓ Converted: {input_path} -> {output_path}")
            return True
            
        except Exception as e:
            print(f"✗ Error converting {input_path}: {str(e)}")
            return False

    def convert_folder(self, folder_path: str, output_folder: str = None):
        """Convert all C# interface files in a folder"""
        folder = Path(folder_path)
        if not folder.exists():
            print(f"Folder not found: {folder_path}")
            return
        
        # Create output folder if specified
        if output_folder:
            Path(output_folder).mkdir(parents=True, exist_ok=True)
        
        # Find all .cs files
        cs_files = list(folder.rglob('*.cs'))
        
        if not cs_files:
            print(f"No .cs files found in {folder_path}")
            return
        
        print(f"Found {len(cs_files)} C# file(s) to convert")
        
        success_count = 0
        for cs_file in cs_files:
            if output_folder:
                # Preserve relative path structure
                rel_path = cs_file.relative_to(folder)
                output_path = Path(output_folder) / rel_path.with_suffix('.java')
                output_path.parent.mkdir(parents=True, exist_ok=True)
                success = self.convert_file(str(cs_file), str(output_path))
            else:
                success = self.convert_file(str(cs_file))
            
            if success:
                success_count += 1
        
        print(f"\nConversion complete: {success_count}/{len(cs_files)} files converted successfully")

    def convert_interface(self, csharp_code: str) -> str:
        """Convert C# interface code to Java interface code"""
        # Remove using statements
        code = re.sub(r'^using\s+.*?;', '', csharp_code, flags=re.MULTILINE)
        
        # Convert namespace to package
        code = re.sub(r'namespace\s+([\w.]+)\s*\{', r'package \1;', code)
        
        # Convert interface declaration
        code = re.sub(
            r'public\s+interface\s+(\w+)(?:\s*:\s*([\w,\s<>]+))?',
            self._convert_interface_declaration,
            code
        )
        
        # Convert property declarations to getter/setter methods
        code = self._convert_properties(code)
        
        # Convert method signatures
        code = self._convert_methods(code)
        
        # Convert type references
        code = self._convert_types(code)
        
        # Remove C#-specific attributes
        code = re.sub(r'\[.*?\]', '', code)
        
        # Fix generic type syntax
        code = re.sub(r'<([^<>]+)>', r'<\1>', code)  # Already similar, but ensure proper spacing
        
        # Add semicolons after method declarations in interfaces
        code = re.sub(r'(\}\s*)$', r';\1', code, flags=re.MULTILINE)
        
        # Clean up extra braces
        code = self._clean_braces(code)
        
        return code.strip()

    def _convert_interface_declaration(self, match):
        """Convert C# interface declaration to Java"""
        interface_name = match.group(1)
        extends = match.group(2)
        
        if extends:
            # Split multiple interfaces
            interfaces = [i.strip() for i in extends.split(',')]
            extends_str = 'extends ' + ', '.join(interfaces)
            return f'public interface {interface_name} {extends_str}'
        else:
            return f'public interface {interface_name}'

    def _convert_properties(self, code: str) -> str:
        """Convert C# properties to Java getter/setter methods"""
