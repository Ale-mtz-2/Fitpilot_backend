# FitPilot Backend - README

## Descripción
FitPilot Backend es una API desarrollada con FastAPI que utiliza GraphQL para la gestión de usuarios y autenticación. La aplicación utiliza PostgreSQL como base de datos y incluye funcionalidades de autenticación JWT y hashing de contraseñas.

## Arquitectura del Proyecto
```
Fitpilot_backend/
├── main.py                    # Punto de entrada de la aplicación FastAPI
├── auth/                      # Módulos de autenticación
│   ├── hashing.py            # Funciones para hash de contraseñas
│   └── jwt.py                # Manejo de tokens JWT
├── crud/                      # Operaciones CRUD
│   ├── authCrud.py           # CRUD de autenticación
│   └── usersCrud.py          # CRUD de usuarios
├── db/                        # Configuración de base de datos
│   └── postgresql.py         # Configuración de PostgreSQL
├── graphql/                   # Schema y resolvers GraphQL
│   ├── schema.py             # Schema principal
│   ├── auth/                 # GraphQL auth mutations/queries
│   └── users/                # GraphQL user mutations/queries
└── models/                    # Modelos de datos
    ├── usersModel.py         # Modelo de usuarios
    └── sessionModel.py       # Modelo de sesiones
```

## Dependencias Requeridas

### Dependencias Principales

Las siguientes dependencias son necesarias para ejecutar el proyecto:

```bash
# Framework principal
fastapi

# Servidor ASGI para producción
uvicorn[standard]

# GraphQL
strawberry-graphql[fastapi]

# Base de datos
sqlalchemy
asyncpg
psycopg2-binary

# Autenticación y seguridad
python-jose[cryptography]
bcrypt
python-multipart

# Utilidades
python-decouple  # Para variables de entorno (recomendado)
```

## Instalación

### 1. Prerrequisitos

- **Python 3.8+** (recomendado 3.10 o superior)
- **PostgreSQL 12+** instalado y en funcionamiento

### 2. Configuración del entorno virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows PowerShell:
.\venv\Scripts\Activate.ps1

# En Windows CMD:
venv\Scripts\activate

# En Linux/macOS:
source venv/bin/activate
```

### 3. Instalación de dependencias

```bash
# Instalar todas las dependencias
pip install fastapi uvicorn[standard] strawberry-graphql[fastapi] sqlalchemy asyncpg psycopg2-binary python-jose[cryptography] bcrypt python-multipart
```

### 4. Configuración de la base de datos

#### Configurar PostgreSQL:

1. **Crear base de datos:**
```sql
CREATE DATABASE defaultdb;
CREATE USER appuser WITH PASSWORD 'secret123';
GRANT ALL PRIVILEGES ON DATABASE defaultdb TO appuser;
```

2. **Crear schema:**
```sql
-- Conectarse a la base de datos defaultdb
\c defaultdb

-- Crear schema app
CREATE SCHEMA app;
GRANT ALL ON SCHEMA app TO appuser;
```

#### Configurar variables de entorno (Recomendado):

Crea un archivo `.env` en la raíz del proyecto:

```env
DATABASE_URL=postgresql+asyncpg://appuser:secret123@localhost:5432/defaultdb
SECRET_KEY_ACCESS_TOKEN=tu-clave-secreta-muy-segura
SECRET_KEY_REFRESH_TOKEN=tu-clave-refresh-muy-segura
ACCESS_TOKEN_EXPIRE_MINUTES=15
ACCESS_TOKEN_EXPIRE_DAYS=7
```

### 5. Ejecutar la aplicación

```bash
# Desarrollo
uvicorn main:app --reload

# Producción
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoints Disponibles

### REST API
- `GET /` - Endpoint de prueba
- `GET /users` - Listar usuarios

### GraphQL
- `POST /graphql` - Endpoint GraphQL
- `GET /graphql` - GraphQL Playground (solo en desarrollo)

### Ejemplo de consulta GraphQL:

```graphql
query {
  hello
}

mutation {
  # Mutations disponibles para autenticación y usuarios
}
```

## Configuración de CORS

La aplicación está configurada para permitir todas las conexiones CORS. Para producción, modifica la configuración en `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Especifica tus dominios
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Estructura de Autenticación

El sistema utiliza JWT con dos tipos de tokens:
- **Access Token**: Duración de 15 minutos
- **Refresh Token**: Duración de 7 días

Las contraseñas se hashean usando bcrypt para mayor seguridad.

## Variables de Entorno Recomendadas

```env
# Base de datos
DATABASE_URL=postgresql+asyncpg://usuario:contraseña@host:puerto/basededatos

# JWT Secrets (cambiar por valores seguros)
SECRET_KEY_ACCESS_TOKEN=clave-muy-segura-para-access-token
SECRET_KEY_REFRESH_TOKEN=clave-muy-segura-para-refresh-token

# Configuración de tokens
ACCESS_TOKEN_EXPIRE_MINUTES=15
ACCESS_TOKEN_EXPIRE_DAYS=7

# Entorno
ENVIRONMENT=development
```

## Comandos Útiles

```bash
# Instalar dependencias desde requirements.txt (si existe)
pip install -r requirements.txt

# Generar requirements.txt
pip freeze > requirements.txt

# Ejecutar con recarga automática
uvicorn main:app --reload --port 8000

# Ejecutar en modo debug
uvicorn main:app --reload --log-level debug
```

## Solución de Problemas Comunes

### Error de conexión a PostgreSQL
- Verificar que PostgreSQL esté ejecutándose
- Comprobar credenciales en `db/postgresql.py`
- Asegurarse de que la base de datos y usuario existan

### Error de importación de módulos
- Verificar que el entorno virtual esté activado
- Instalar dependencias faltantes
- Comprobar la estructura de carpetas

### Problemas con JWT
- Verificar que las claves secretas estén configuradas
- Comprobar la zona horaria en `auth/jwt.py`

## Notas de Desarrollo

- El proyecto usa SQLAlchemy con AsyncSession para operaciones asíncronas
- Los modelos están en el schema "app" de PostgreSQL
- La aplicación está configurada para timezone "America/Mexico_City"
- GraphQL schema se construye con Strawberry

## Contribución

Para contribuir al proyecto:
1. Fork el repositorio
2. Crear una rama para tu feature
3. Hacer commit de tus cambios
4. Crear un Pull Request

## Licencia

[Especificar licencia del proyecto]