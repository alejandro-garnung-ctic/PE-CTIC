"""
Parser para extraer metadata de notebooks PE-CTIC
"""
import re
import json

def parse_notebook_header(notebook_path):
    """
    Extrae metadata de la cabecera del notebook
    
    Formato esperado:
    # ------------------------------------------------------------------
    # Metadata del Notebook
    #
    # Título: {valor}
    # Autor: {valor}
    # Fecha: {valor}
    # Tema: {valor}
    # Tópico: {valor}
    # Keywords: {valor}
    # Descripción: {valor}
    # ------------------------------------------------------------------
    
    Returns:
        dict con los campos extraídos (o valores por defecto si no se encuentran)
    """
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        metadata = {
            'titulo': '-',
            'autor': '-',
            'fecha': '-',
            'tema': '-',
            'topico': '-',
            'keywords': '-',
            'descripcion': '-'
        }
        
        # Buscar en las primeras celdas (puede ser markdown o code)
        if 'cells' in nb and len(nb['cells']) > 0:
            # Buscar en las primeras 3 celdas (por si la primera no es markdown)
            for cell_idx in range(min(3, len(nb['cells']))):
                cell = nb['cells'][cell_idx]
                source = cell.get('source', '')
                if isinstance(source, list):
                    source = ''.join(source)
                
                # Buscar cada campo con regex (funciona tanto en markdown como en code)
                patterns = {
                    'titulo': r'#\s*Título:\s*\{([^}]+)\}',
                    'autor': r'#\s*Autor:\s*\{([^}]+)\}',
                    'fecha': r'#\s*Fecha:\s*\{([^}]+)\}',
                    'tema': r'#\s*Tema:\s*\{([^}]+)\}',
                    'topico': r'#\s*Tópico:\s*\{([^}]+)\}',
                    'keywords': r'#\s*Keywords:\s*((?:\{[^}]+\}(?:\s*,\s*)*)+)',  # Captura múltiples {keyword}
                    'descripcion': r'#\s*Descripción:\s*\{([^}]+)\}'
                }
                
                # Procesar keywords de forma especial (puede tener múltiples {keyword})
                if metadata['keywords'] == '-':
                    # Buscar la línea completa de keywords (captura todo hasta el salto de línea)
                    keywords_line_match = re.search(r'#\s*Keywords:\s*([^\n#]+)', source, re.IGNORECASE | re.MULTILINE)
                    if keywords_line_match:
                        keywords_line = keywords_line_match.group(1).strip()
                        # Extraer todos los valores entre llaves de la línea
                        keywords_matches = re.findall(r'\{([^}]+)\}', keywords_line)
                        if keywords_matches:
                            keywords_clean = [k.strip() for k in keywords_matches if k.strip() and k.strip() != '-']
                            if keywords_clean:
                                metadata['keywords'] = ', '.join(keywords_clean)
                
                # Procesar otros campos
                for key, pattern in patterns.items():
                    if key == 'keywords':
                        continue  # Ya procesado arriba
                    if metadata[key] == '-':  # Solo actualizar si no se ha encontrado
                        match = re.search(pattern, source, re.IGNORECASE | re.MULTILINE)
                        if match:
                            value = match.group(1).strip()
                            if value and value != '-':
                                metadata[key] = value
                
                # Si ya encontramos todos los campos, salir
                if all(v != '-' for v in metadata.values()):
                    break
        
        return metadata
    except Exception as e:
        # Si hay error, devolver valores por defecto
        return {
            'titulo': '-',
            'autor': '-',
            'fecha': '-',
            'tema': '-',
            'topico': '-',
            'keywords': '-',
            'descripcion': '-'
        }

