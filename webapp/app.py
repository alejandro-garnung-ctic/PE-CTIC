# webapp/app.py
from flask import Flask, render_template, send_file, url_for, request, jsonify
import nbformat
from nbconvert import HTMLExporter
import os
import json
import markdown
import re
from markupsafe import Markup
from notebook_parser import parse_notebook_header

app = Flask(__name__)

# Context processor para hacer logo_exists disponible en todos los templates
@app.context_processor
def inject_logo_exists():
    logo_path = '/app/static/logo.png'
    logo_exists = os.path.exists(logo_path) and os.path.getsize(logo_path) > 0
    return dict(logo_exists=logo_exists)

# Configurar ruta para archivos estáticos (logo)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_file(os.path.join('/app/static', filename))

# Endpoint para servir archivos desde shared y users
@app.route('/files/<path:file_path>')
def serve_file(file_path):
    """Servir archivos desde shared/ o users/"""
    # Asegurar que el path es relativo
    if file_path.startswith('/'):
        file_path = file_path[1:]
    
    # Intentar primero en shared
    shared_path = os.path.join('/app/shared', file_path)
    if os.path.exists(shared_path) and os.path.isfile(shared_path):
        return send_file(shared_path)
    
    # Si no está en shared, buscar en users
    users_path = os.path.join('/app/users', file_path)
    if os.path.exists(users_path) and os.path.isfile(users_path):
        return send_file(users_path)
    
    return "Archivo no encontrado", 404

def convert_notebook_to_html(notebook_path):
    """Convierte notebook a HTML para visualización usando nbconvert"""
    try:
        # Leer el notebook
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        # Obtener el directorio del notebook para resolver rutas relativas
        notebook_dir = os.path.dirname(notebook_path)
        
        # Convertir a HTML usando nbconvert (nbconvert maneja las imágenes base64 automáticamente)
        html_exporter = HTMLExporter()
        html_exporter.template_name = 'classic'
        # Configurar para no escapar caracteres LaTeX incorrectamente
        html_exporter.filters = {
            'markdown2html': lambda source: markdown.markdown(
                source, 
                extensions=['fenced_code', 'tables', 'codehilite', 'nl2br']
            )
        }
        (body, resources) = html_exporter.from_notebook_node(nb)
        
        # Solo procesar rutas relativas de imágenes estáticas en markdown
        # NO tocar las imágenes base64 generadas por Python (nbconvert las maneja correctamente)
        body = fix_image_paths(body, notebook_dir)
        
        return body
    except Exception as e:
        # Fallback: conversión simple
        notebook_dir = os.path.dirname(notebook_path)
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        html_content = ""
        for cell in nb.cells:
            if cell.cell_type == 'markdown':
                # Convertir markdown a HTML
                html = markdown.markdown(cell.source, extensions=['fenced_code', 'tables', 'codehilite'])
                html_content += f"<div class='markdown-cell'>{html}</div>"
            elif cell.cell_type == 'code':
                html_content += f"<div class='code-cell'><pre><code>{cell.source}</code></pre></div>"
            elif cell.cell_type == 'output' and 'text' in cell.get('outputs', [{}])[0]:
                html_content += f"<div class='output-cell'><pre>{cell.outputs[0]['text']}</pre></div>"
        
        # Procesar el HTML para convertir rutas relativas de imágenes
        html_content = fix_image_paths(html_content, notebook_dir)
        
        return html_content

def fix_image_paths(html_content, notebook_dir):
    """Convierte rutas relativas de imágenes estáticas a rutas absolutas para la webapp
    NO modifica imágenes base64 generadas por Python (nbconvert las maneja automáticamente)
    """
    # Determinar si el notebook está en shared o users
    is_shared = '/app/shared' in notebook_dir
    is_users = '/app/users' in notebook_dir
    
    # Obtener el directorio base y la ruta relativa
    if is_shared:
        base_path = '/app/shared'
        rel_dir = os.path.relpath(notebook_dir, '/app/shared')
    elif is_users:
        base_path = '/app/users'
        rel_dir = os.path.relpath(notebook_dir, '/app/users')
    else:
        base_path = None
        rel_dir = ''
    
    # Patrón para encontrar rutas de imágenes en HTML (src="...")
    def replace_image_path(match):
        img_path = match.group(1)
        
        # NO tocar imágenes base64 (nbconvert las maneja automáticamente)
        if img_path.startswith('data:image'):
            return match.group(0)
        
        # Si ya es una URL HTTP/HTTPS, no hacer nada
        if img_path.startswith('http://') or img_path.startswith('https://'):
            return match.group(0)
        
        # Si ya es una ruta web de la aplicación, no hacer nada
        if img_path.startswith('/pe-ctic/webapp/'):
            return match.group(0)
        
        # Si es una ruta absoluta del sistema de archivos
        if img_path.startswith('/'):
            # Convertir rutas absolutas del sistema de archivos a rutas web
            if '/home/jovyan/shared/' in img_path or '/home/shared/' in img_path or img_path.startswith('/home/jovyan/shared/') or img_path.startswith('/home/shared/'):
                # Es una ruta de shared
                rel_path = img_path.replace('/home/jovyan/shared/', '').replace('/home/shared/', '').lstrip('/')
                return f'src="/pe-ctic/webapp/files/{rel_path}"'
            elif '/home/jovyan/users/' in img_path or '/home/users/' in img_path or img_path.startswith('/home/jovyan/users/') or img_path.startswith('/home/users/'):
                # Es una ruta de users
                rel_path = img_path.replace('/home/jovyan/users/', '').replace('/home/users/', '').lstrip('/')
                return f'src="/pe-ctic/webapp/files/{rel_path}"'
            # Si no es de shared/users, dejar como está
            return match.group(0)
        
        # Es una ruta relativa, resolverla
        if base_path and rel_dir:
            # Resolver la ruta relativa desde el directorio del notebook
            resolved_path = os.path.normpath(os.path.join(base_path, rel_dir, img_path))
            
            # Verificar que la ruta resuelta esté dentro de shared o users
            if resolved_path.startswith('/app/shared/'):
                rel_path = resolved_path.replace('/app/shared/', '')
                # Verificar que el archivo existe
                if os.path.exists(resolved_path):
                    return f'src="/pe-ctic/webapp/files/{rel_path}"'
            elif resolved_path.startswith('/app/users/'):
                rel_path = resolved_path.replace('/app/users/', '')
                # Verificar que el archivo existe
                if os.path.exists(resolved_path):
                    return f'src="/pe-ctic/webapp/files/{rel_path}"'
            # Si la ruta resuelta sale de shared/users, intentar buscar en ambos
            else:
                # Intentar buscar en shared
                shared_path = os.path.normpath(os.path.join('/app/shared', img_path.lstrip('/')))
                if os.path.exists(shared_path):
                    rel_path = shared_path.replace('/app/shared/', '')
                    return f'src="/pe-ctic/webapp/files/{rel_path}"'
                # Intentar buscar en users
                users_path = os.path.normpath(os.path.join('/app/users', img_path.lstrip('/')))
                if os.path.exists(users_path):
                    rel_path = users_path.replace('/app/users/', '')
                    return f'src="/pe-ctic/webapp/files/{rel_path}"'
        
        # Si no se puede resolver, intentar directamente (puede que el usuario haya puesto la ruta correcta)
        # Limpiar la ruta de ../ y ./
        clean_path = os.path.normpath(img_path).replace('\\', '/').lstrip('/')
        return f'src="/pe-ctic/webapp/files/{clean_path}"'
    
    # Reemplazar rutas en atributos src de imágenes
    html_content = re.sub(r'src="([^"]+)"', replace_image_path, html_content)
    
    # También reemplazar en atributos srcset si existen
    html_content = re.sub(r'srcset="([^"]+)"', replace_image_path, html_content)
    
    return html_content

@app.route('/')
def index():
    """Página principal con listado de notebooks"""
    notebooks = []
    
    # Escanear notebooks en shared
    shared_notebooks_dir = '/app/shared/notebooks'
    if os.path.exists(shared_notebooks_dir):
        for root, dirs, files in os.walk(shared_notebooks_dir):
            # Excluir directorios de checkpoints
            if '.ipynb_checkpoints' in root:
                continue
                
            for file in files:
                # Excluir checkpoints y archivos ocultos
                if file.endswith('.ipynb') and not file.startswith('.') and 'checkpoint' not in file:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, '/app/shared')
                    
                    # Obtener información del archivo
                    stat_info = os.stat(full_path)
                    modified_time = stat_info.st_mtime
                    
                    # Obtener usuario propietario desde metadata del notebook
                    owner_name = "Desconocido"
                    
                    # Intentar leer metadata del notebook
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            nb_data = json.load(f)
                            if 'metadata' in nb_data and 'pe_ctic' in nb_data['metadata']:
                                owner_name = nb_data['metadata']['pe_ctic'].get('created_by', 
                                    nb_data['metadata']['pe_ctic'].get('last_modified_by', 'Desconocido'))
                    except:
                        pass
                    
                    # Si no hay metadata, usar UID como fallback
                    if owner_name == "Desconocido":
                        owner_uid = stat_info.st_uid
                        uid_map = {
                            1000: 'jovyan',
                            0: 'root',
                            1005: 'agarnung'
                        }
                        owner_name = uid_map.get(owner_uid, f"Usuario {owner_uid}")
                    
                    # Extraer metadata de la cabecera del notebook
                    header_metadata = parse_notebook_header(full_path)
                    
                    # Formatear fecha
                    from datetime import datetime
                    modified_date = datetime.fromtimestamp(modified_time)
                    
                    notebooks.append({
                        'title': header_metadata.get('titulo', file.replace('.ipynb', '')),
                        'filename': file.replace('.ipynb', ''),
                        'path': rel_path,
                        'full_path': full_path,
                        'type': 'shared',
                        'modified': modified_time,
                        'modified_date': modified_date,
                        'owner': owner_name,
                        'autor': header_metadata.get('autor', '-'),
                        'fecha': header_metadata.get('fecha', '-'),
                        'tema': header_metadata.get('tema', '-'),
                        'topico': header_metadata.get('topico', '-'),
                        'keywords': header_metadata.get('keywords', '-'),
                        'descripcion': header_metadata.get('descripcion', '-')
                    })
    
    # Ordenar por fecha de modificación (más recientes primero)
    notebooks.sort(key=lambda x: x['modified'], reverse=True)
    
    # Extraer valores únicos para los filtros
    autores = sorted(set([nb['autor'] for nb in notebooks if nb['autor'] != '-']))
    temas = sorted(set([nb['tema'] for nb in notebooks if nb['tema'] != '-']))
    keywords_all = []
    for nb in notebooks:
        if nb['keywords'] != '-':
            # Separar keywords por comas
            kw_list = [k.strip() for k in nb['keywords'].split(',')]
            keywords_all.extend(kw_list)
    keywords = sorted(set([k for k in keywords_all if k]))
    
    # Verificar si existe el logo y no está vacío
    logo_path = '/app/static/logo.png'
    logo_exists = os.path.exists(logo_path) and os.path.getsize(logo_path) > 0
    
    return render_template('index.html', 
                          notebooks=notebooks, 
                          logo_exists=logo_exists,
                          autores=autores,
                          temas=temas,
                          keywords=keywords)

@app.route('/notebook/<path:notebook_path>')
def view_notebook(notebook_path):
    """Visualizar un notebook específico"""
    # Asegurar que el path es relativo a shared
    if notebook_path.startswith('/'):
        notebook_path = notebook_path[1:]
    
    full_path = os.path.join('/app/shared', notebook_path)
    
    if os.path.exists(full_path) and full_path.endswith('.ipynb'):
        html_content = convert_notebook_to_html(full_path)
        notebook_name = os.path.basename(notebook_path).replace('.ipynb', '')
        logo_path = '/app/static/logo.png'
        logo_exists = os.path.exists(logo_path) and os.path.getsize(logo_path) > 0
        
        # Extraer metadata del notebook
        metadata = parse_notebook_header(full_path)
        
        return render_template('notebook.html', 
                             content=Markup(html_content), 
                             notebook_name=notebook_name, 
                             logo_exists=logo_exists,
                             metadata=metadata)
    return "Notebook no encontrado", 404

@app.route('/api/notebooks')
def api_notebooks():
    """API para obtener notebooks con filtros"""
    # Obtener parámetros de filtro
    filtro_autor = request.args.get('autor', '').strip()
    filtro_tema = request.args.get('tema', '').strip()
    filtro_keyword = request.args.get('keyword', '').strip()
    filtro_fecha = request.args.get('fecha', '').strip()
    busqueda = request.args.get('search', '').strip().lower()
    
    notebooks = []
    
    # Escanear notebooks (mismo código que index)
    shared_notebooks_dir = '/app/shared/notebooks'
    if os.path.exists(shared_notebooks_dir):
        for root, dirs, files in os.walk(shared_notebooks_dir):
            if '.ipynb_checkpoints' in root:
                continue
                
            for file in files:
                if file.endswith('.ipynb') and not file.startswith('.') and 'checkpoint' not in file:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, '/app/shared')
                    
                    stat_info = os.stat(full_path)
                    modified_time = stat_info.st_mtime
                    
                    owner_name = "Desconocido"
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            nb_data = json.load(f)
                            if 'metadata' in nb_data and 'pe_ctic' in nb_data['metadata']:
                                owner_name = nb_data['metadata']['pe_ctic'].get('created_by', 
                                    nb_data['metadata']['pe_ctic'].get('last_modified_by', 'Desconocido'))
                    except:
                        pass
                    
                    if owner_name == "Desconocido":
                        owner_uid = stat_info.st_uid
                        uid_map = {1000: 'jovyan', 0: 'root', 1005: 'agarnung'}
                        owner_name = uid_map.get(owner_uid, f"Usuario {owner_uid}")
                    
                    header_metadata = parse_notebook_header(full_path)
                    
                    from datetime import datetime
                    modified_date = datetime.fromtimestamp(modified_time)
                    
                    notebook_data = {
                        'title': header_metadata.get('titulo', file.replace('.ipynb', '')),
                        'filename': file.replace('.ipynb', ''),
                        'path': rel_path,
                        'full_path': full_path,
                        'type': 'shared',
                        'modified': modified_time,
                        'modified_date': modified_date.strftime('%d/%m/%Y %H:%M'),
                        'owner': owner_name,
                        'autor': header_metadata.get('autor', '-'),
                        'fecha': header_metadata.get('fecha', '-'),
                        'tema': header_metadata.get('tema', '-'),
                        'topico': header_metadata.get('topico', '-'),
                        'keywords': header_metadata.get('keywords', '-'),
                        'descripcion': header_metadata.get('descripcion', '-')
                    }
                    
                    # Aplicar filtros
                    if filtro_autor and notebook_data['autor'] != filtro_autor:
                        continue
                    if filtro_tema and notebook_data['tema'] != filtro_tema:
                        continue
                    if filtro_keyword:
                        keywords_list = [k.strip().lower() for k in notebook_data['keywords'].split(',')]
                        if filtro_keyword.lower() not in keywords_list:
                            continue
                    if filtro_fecha and notebook_data['fecha'] != filtro_fecha:
                        continue
                    if busqueda:
                        search_text = f"{notebook_data['title']} {notebook_data['descripcion']} {notebook_data['topico']}".lower()
                        if busqueda not in search_text:
                            continue
                    
                    notebooks.append(notebook_data)
    
    notebooks.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify(notebooks)

@app.route('/notebooks')
def notebooks_list():
    """Redirigir a la lista de notebooks"""
    return index()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
