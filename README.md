# PE-CTIC - Entorno Colaborativo Python

Entorno colaborativo simple para análisis de datos y desarrollo Python con JupyterLab, sistema de usuarios múltiples y visualización web de notebooks.

El entorno ya está **lanzado y disponible** en: https://pe-ctic.test.ctic.es/pe-ctic/.

## 🚀 Inicio Rápido

### 1. Inicializar el Proyecto (Solo la Primera Vez)

```bash
# Dar permisos de ejecución
chmod +x init_project.sh

# Ejecutar inicialización
./init_project.sh
```

### 2. Iniciar el Entorno

```bash
# Construir e iniciar los contenedores
docker compose up -d

# Ver que todo está corriendo
docker compose ps
```

### 3. Acceder al Sistema

1. Abre tu navegador
2. Ve a: **https://pe-ctic.test.ctic.es/pe-ctic/** (o `http://192.168.2.88/pe-ctic/` si tienes DNS y estás en la red interna)
3. **Login con usuario/contraseña** (debes crear usuarios primero, ver sección [Gestión de Usuarios](#-gestión-de-usuarios))
4. Se redirige automáticamente a JupyterLab en `/lab`
5. ¡Listo! Ya puedes crear y editar notebooks

**Para cerrar sesión**: Desde JupyterLab, ve a `File` → `Log Out` o accede directamente al endpoint `/logout`

---

## 🔐 Acceso al Sistema

### Rutas Disponibles

- **`chomsky/pe-ctic/`** → Login de autenticación
- **`chomsky/lab`** → JupyterLab (requiere login)
- **`chomsky/pe-ctic/webapp/`** → Webapp pública para visualizar notebooks compartidos
- **`chomsky/`** → 404 (no hay página raíz)

### Flujo de Trabajo

1. **Login**: `chomsky/pe-ctic/` → Introduce usuario/contraseña
2. **Redirección automática**: Te lleva a JupyterLab (`/lab`) con sesión activa
3. **Trabajar**: Crea scripts/notebooks en `shared/` o `users/{username}/`
4. **Visualizar**: Ve a `chomsky/pe-ctic/webapp/` para ver notebooks compartidos
5. **Logout**: Desde JupyterLab, `File` → `Log Out` o accede a `chomsky/logout`

---

## 📁 Estructura del Proyecto

```
PE-CTIC/
├── auth/                      # 🔐 Servicio de autenticación
│   ├── Dockerfile
│   ├── app.py                # Aplicación Flask de autenticación
│   └── users_data/           # Datos de usuarios y tokens
│
├── jupyterlab/                # ⚙️ Configuración de JupyterLab
│   ├── Dockerfile
│   └── jupyter_lab_config.py
│
├── webapp/                    # 🌐 Aplicación web para visualizar notebooks
│   ├── Dockerfile
│   ├── app.py
│   ├── static/               # Logo y archivos estáticos
│   └── templates/
│
├── shared/                    # ⭐ RECURSOS COMPARTIDOS
│   ├── data/                 # Datos compartidos (CSV, JSON, etc.)
│   ├── scripts/              # Scripts Python compartidos
│   └── notebooks/            # Notebooks compartidos (aparecen en webapp)
│
├── users/                     # 📁 TRABAJO INDIVIDUAL
│   └── [nombre_usuario]/     # Directorios personales (uno por usuario)
│
├── nginx/                     # 🌐 Proxy reverso y enrutamiento
│   ├── Dockerfile
│   └── nginx.conf
│
├── docker-compose.yml
├── init_project.sh
└── README.md
```

### ¿Dónde Poner las Cosas?

| Qué quieres hacer | Dónde ponerlo | ¿Quién puede verlo? |
|------------------|---------------|---------------------|
| **Datos para compartir** | `shared/data/` | Todos |
| **Scripts para compartir** | `shared/scripts/` | Todos |
| **Notebooks para compartir** | `shared/notebooks/` | Todos (aparecen en webapp) |
| **Trabajo personal** | `users/tu_nombre/` | Lectura: todos, Escritura: todos (colaborativo) |

---

## 👤 Gestión de Usuarios

### Añadir Usuario

Los usuarios se registran desde la línea de comandos. No hay usuario por defecto.

```bash
# Añadir usuario
docker compose exec auth python manage_users.py add -u agarnung -p mi_contraseña

# Listar usuarios
docker compose exec auth python manage_users.py list

# Cambiar contraseña
docker compose exec auth python manage_users.py change-password -u agarnung -p nueva_contraseña

# Eliminar usuario
docker compose exec auth python manage_users.py remove -u nombre_usuario
```

**Nota**: La carpeta del usuario se crea automáticamente en `users/{username}/` al registrarlo, junto con un archivo `BIENVENIDO.txt` con instrucciones.

Para eliminar carpetas personales de usuarios: `docker compose exec auth rm -rf /app/users/nombre_usuario/`

### ⚠️ Sistema de Usuarios

**Todos los notebooks se ejecutan como usuario `jovyan`** (usuario común del contenedor). **NO hay aislamiento real entre usuarios** - es un sistema de **colaboración abierta**.

- ✅ Autenticación: Solo usuarios registrados pueden acceder
- ✅ Organización: Cada usuario tiene su carpeta (se crea automáticamente)
- ⚠️ **Cualquier usuario puede modificar archivos de otros** (todos ejecutan como `jovyan`)

---

## 💻 Cómo Trabajar

### Trabajar con Datos Compartidos

```python
# Cargar datos compartidos
import pandas as pd
df = pd.read_csv('/home/shared/data/synthetic_alsa_data.csv')

# Usar scripts compartidos
import sys
sys.path.insert(0, '/home/shared/scripts')
from test_minimal import test_minimal
test_minimal()
```

### Crear Notebooks

1. En JupyterLab, click en "New" → "Notebook"
2. Añade la cabecera de metadatos al inicio (ver formato abajo)
3. Escribe Python, Markdown, LaTeX
4. Ejecuta celdas con Shift+Enter
5. **Guarda en `shared/notebooks/`** para que aparezca en la webapp

**Formato de metadatos** (añadir al inicio del notebook):
```python
# ------------------------------------------------------------------
# Metadata del Notebook
#
# Título: {Tu título}
# Autor: {tu_usuario}
# Fecha: {dd/mm/yyyy}
# Tema: {número}
# Tópico: {tópico}
# Keywords: {keyword1, keyword2}
# Descripción: {Descripción breve}
# ------------------------------------------------------------------
```

⚠️ **Importante**: Evita espacios y caracteres especiales en nombres de archivos y rutas. Usa guiones bajos (_) o guiones (-) en lugar de espacios.

### Explorar la Estructura

En el panel izquierdo de JupyterLab verás:
- **Home** (`/home/jovyan`) - Tu directorio de trabajo
- **shared** (enlace simbólico) - Recursos compartidos
- **users** (enlace simbólico) - Directorios de usuarios

---

## 🐛 Solución de Problemas

### Reiniciar servicios
```bash
docker compose restart [servicio]  # Reiniciar un servicio específico
docker compose down && docker compose up -d  # Reiniciar todo
```

### Ver logs
```bash
docker compose logs [servicio]  # Ver logs de un servicio
docker compose logs -f  # Seguir logs en tiempo real
```

### Problemas comunes

- **No puedo acceder a JupyterLab**: Accede a través de `chomsky/pe-ctic/` (no directamente a `/lab`)
- **Permisos**: Ejecuta `./fix_permissions.sh` si hay problemas de permisos
- **Servicios no inician**: Verifica con `docker compose ps`

---

## 📝 Notas Importantes

- **Autenticación**: Solo usuarios registrados pueden acceder a JupyterLab
- **Webapp**: Pública (sin autenticación) para visualizar notebooks compartidos
- **Colaboración**: Todos los usuarios pueden ver y modificar archivos en `shared/` y `users/`
- **Metadatos**: Los notebooks en `shared/notebooks/` con metadatos aparecen automáticamente en la webapp
- **Logo**: Se encuentra en `webapp/static/logo.png`

---

**PE-CTIC** - _Píldoras de Estadística de CTIC_ - Entorno colaborativo de estadística aplicada con Python
