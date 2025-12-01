# Guía de Instalación

## Requisitos del Sistema

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Acceso a internet para descarga de dependencias
- Cuenta de Telegram con un bot creado mediante [@BotFather](https://t.me/BotFather)

## Pasos de Instalación

### 1. Clonar el Repositorio

```bash
git clone <url-del-repositorio>
cd a1
```

Si no tienes git instalado, puedes descargar el código como archivo ZIP desde GitHub.

### 2. Crear Entorno Virtual (Recomendado)

```bash
python -m venv venv
```

#### Activar el entorno virtual:

- **Linux/Mac**:
  ```bash
  source venv/bin/activate
  ```

- **Windows**:
  ```bash
  venv\Scripts\activate
  ```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

1. **Copiar archivo de ejemplo**:
   ```bash
   cp .env.example .env
   ```

2. **Editar archivo `.env`**:
   ```bash
   nano .env  # o usar cualquier editor de texto
   ```

3. **Configurar las variables**:
   - `BOT_TOKEN`: Obtener de [@BotFather](https://t.me/BotFather) en Telegram
   - `ADMIN_IDS`: IDs de usuarios que tendrán acceso de administrador

### 5. Obtener Token de Bot de Telegram

1. Abrir Telegram y buscar `@BotFather`
2. Enviar `/newbot` y seguir las instrucciones
3. Guardar el token proporcionado
4. Opcionalmente, configurar el nombre de usuario del bot con `/setusernamer`

### 6. Identificar IDs de Administradores

Los IDs de administradores se pueden obtener de varias maneras:
- Desde el menú de administración del bot
- Usando un bot de información como `@userinfobot`
- Consultando logs del bot si los usuarios interactúan

Formato de `ADMIN_IDS`:
- Array JSON: `[123456789, 987654321]`
- Separado por comas: `123456789,987654321`

## Configuración de Canales

### 1. Crear Canales de Telegram

- Crear los canales VIP y/o gratuito en Telegram
- Asegurarse de tener permisos de administrador

### 2. Añadir el Bot como Administrador

- Ir a la configuración del canal
- Añadir al bot como administrador
- Dar permisos necesarios (enviar mensajes, gestionar mensajes)

## Iniciar el Bot

### Modo Desarrollo

```bash
python main.py
```

### Modo Producción (Recomendado para servidores)

```bash
# Usando screen para mantener el proceso en segundo plano
screen -S telegram_bot python main.py

# O usando nohup
nohup python main.py &
```

## Verificar Instalación

1. Iniciar el bot con `python main.py`
2. Verificar que no hay errores en la consola
3. Enviar `/start` al bot en Telegram
4. Confirmar que responde adecuadamente

## Solución de Problemas Comunes

### Error de Token de Bot
- Verificar que el token esté correctamente copiado en `.env`
- Confirmar que el bot no esté deshabilitado

### Error de Conexión a Base de Datos
- Verificar permisos de escritura en el directorio
- Confirmar que SQLite está disponible en el sistema

### Error de Permisos de Administrador
- Asegurarse que los IDs en `ADMIN_IDS` sean correctos
- Verificar que el bot tenga permisos en los canales configurados

### Problemas con Reacciones o Enlaces
- Confirmar que el bot tiene permisos para crear enlaces de invitación
- Verificar que los canales estén correctamente configurados

## Actualización del Bot

```bash
# Obtener los últimos cambios
git pull origin main

# Actualizar dependencias (si cambian)
pip install -r requirements.txt --upgrade
```

## Copias de Seguridad

El bot usa SQLite por defecto, por lo que la base de datos es un solo archivo:
- `bot.db` - Archivo de base de datos (si se usa SQLite por defecto)
- Hacer copias regulares de este archivo para respaldo