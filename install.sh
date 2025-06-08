#!/bin/bash

# --- Configuración ---
APP_NAME="autocompleter"
INSTALL_DIR="/opt/$APP_NAME"
SERVICE_FILE="${APP_NAME}.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_FILE}"
PYTHON_VERSION="python3" # Puedes cambiar a python si python3 no es el comando principal
UV_COMMAND="uv"
VENV_DIR=".venv"

# Colores para la salida
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Iniciando la instalación de la aplicación $APP_NAME...${NC}"

# --- 1. Verificar y crear usuario de sistema ---
echo -e "${YELLOW}1. Verificando/Creando usuario de sistema '${APP_NAME}'...${NC}"
if ! id -u "$APP_NAME" >/dev/null 2>&1; then
    sudo useradd --system --no-create-home "$APP_NAME"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Usuario '$APP_NAME' creado exitosamente.${NC}"
    else
        echo -e "${RED}Error al crear el usuario '$APP_NAME'. Abortando.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Usuario '$APP_NAME' ya existe.${NC}"
fi

# --- 2. Crear directorio de instalación y copiar archivos ---
echo -e "${YELLOW}2. Creando directorio de instalación y copiando archivos...${NC}"
sudo mkdir -p "$INSTALL_DIR"
if [ $? -ne 0 ]; then
    echo -e "${RED}Error al crear el directorio '$INSTALL_DIR'. Abortando.${NC}"
    exit 1
fi

# Asegurarse de copiar todos los archivos relevantes
sudo cp main.py "$INSTALL_DIR/"
sudo cp pyproject.toml "$INSTALL_DIR/"
sudo cp -r static/ "$INSTALL_DIR/"
sudo cp rate_limiter.py "$INSTALL_DIR/"
sudo cp nominatim_client.py "$INSTALL_DIR/"
sudo cp cache.py "$INSTALL_DIR/"
sudo cp scoring_model.py "$INSTALL_DIR/"
sudo cp "$SERVICE_FILE" "$INSTALL_DIR/" # Copia el archivo de servicio también aquí temporalmente

# Asignar propiedad al usuario del sistema para que pueda crear el venv
sudo chown -R "$APP_NAME":"$APP_NAME" "$INSTALL_DIR"
echo -e "${GREEN}Archivos copiados y permisos configurados en '$INSTALL_DIR'.${NC}"

# --- 3. Navegar al directorio de la aplicación ---
# Necesario para que venv/uv venv funcione correctamente
cd "$INSTALL_DIR" || { echo -e "${RED}Error: No se pudo cambiar al directorio '$INSTALL_DIR'. Abortando.${NC}"; exit 1; }

# --- 4. Configurar el entorno virtual y dependencias ---
echo -e "${YELLOW}4. Configurando entorno virtual e instalando dependencias...${NC}"
UV_PATH=$(command -v "$UV_COMMAND" 2>/dev/null) # Obtiene la ruta de uv para el usuario actual
USE_UV=false

echo -e "${YELLOW}Instalando redis${NC}"
sudo apt update && sudo apt install redis-server -y

if [ -n "$UV_PATH" ]; then
    # Intenta verificar si el usuario del servicio puede ejecutar 'uv'.
    # Si 'uv' está en ~/.local/bin, es muy probable que falle.
    if sudo -u "$APP_NAME" test -x "$UV_PATH"; then
        echo -e "${YELLOW}El usuario '${APP_NAME}' tiene permisos para ejecutar '$UV_COMMAND'.${NC}"
        USE_UV=true
    else
        echo -e "${YELLOW}El usuario '${APP_NAME}' NO tiene permisos para ejecutar '$UV_COMMAND' desde '$UV_PATH'.${NC}"
        echo -e "${YELLOW}Se procederá con la creación del entorno virtual utilizando 'venv' de Python.${NC}"
    fi
fi

if [ "$USE_UV" = true ]; then
    echo -e "${YELLOW}Usando '$UV_COMMAND' para el entorno virtual e instalación.${NC}"
    sudo -u "$APP_NAME" "$UV_PATH" venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error al crear el entorno virtual con '$UV_PATH venv'. Abortando.${NC}"
        exit 1
    fi
    # Para uv pip install -e ., asegúrate de que el --python apunte al venv recién creado
    sudo -u "$APP_NAME" "$UV_PATH" pip install -e . --python "$INSTALL_DIR/$VENV_DIR/bin/$PYTHON_VERSION"
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error al instalar dependencias con '$UV_PATH pip install -e .'. Abortando.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Entorno virtual y dependencias instaladas exitosamente con UV.${NC}"
else
    echo -e "${YELLOW}Usando '$PYTHON_VERSION -m venv' para el entorno virtual e instalación.${NC}"
    sudo -u "$APP_NAME" "$PYTHON_VERSION" -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error al crear el entorno virtual con '$PYTHON_VERSION -m venv'. Abortando.${NC}"
        exit 1
    fi
    # Asegurarse de usar pip del entorno virtual recién creado
    sudo -u "$APP_NAME" "$INSTALL_DIR/$VENV_DIR/bin/pip" install -e .
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error al instalar dependencias con 'pip install -e .'. Abortando.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Entorno virtual y dependencias instaladas exitosamente con venv.${NC}"
fi

# --- 5. Configurar el servicio systemd ---
echo -e "${YELLOW}5. Copiando y configurando el servicio systemd...${NC}"
# Mover el archivo de servicio a su destino final
sudo mv "${APP_NAME}.service" "$SERVICE_PATH"
if [ $? -ne 0 ]; then
    echo -e "${RED}Error al mover el archivo de servicio a '$SERVICE_PATH'. Abortando.${NC}"
    exit 1
fi

sudo systemctl daemon-reload
sudo systemctl enable "$APP_NAME"
sudo systemctl start "$APP_NAME"

echo -e "${GREEN}Servicio '$APP_NAME' configurado, habilitado e iniciado.${NC}"
echo -e "${YELLOW}Verificando estado del servicio...${NC}"
systemctl status "$APP_NAME" --no-pager

echo -e "${GREEN}¡Instalación completada!${NC}"
echo "La aplicación debería estar disponible en http://localhost:8089"
echo "Para verificar el estado del servicio en el futuro: sudo systemctl status $APP_NAME"
echo "Para detener el servicio: sudo systemctl stop $APP_NAME"
echo "Para iniciar el servicio: sudo systemctl start $APP_NAME"
echo "Para reiniciar el servicio: sudo systemctl restart $APP_NAME"
