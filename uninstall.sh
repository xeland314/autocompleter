#!/bin/bash

# --- Configuración ---
APP_NAME="autocompleter"
INSTALL_DIR="/opt/$APP_NAME"
SERVICE_FILE="${APP_NAME}.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_FILE}"

# Colores para la salida
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Iniciando la desinstalación de la aplicación $APP_NAME...${NC}"

# --- 1. Detener y deshabilitar el servicio systemd ---
echo -e "${YELLOW}1. Deteniendo y deshabilitando el servicio systemd...${NC}"
if sudo systemctl is-active --quiet "$APP_NAME"; then
    sudo systemctl stop "$APP_NAME"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Servicio '$APP_NAME' detenido exitosamente.${NC}"
    else
        echo -e "${RED}Advertencia: No se pudo detener el servicio '$APP_NAME'. Continuando...${NC}"
    fi
else
    echo -e "${YELLOW}Servicio '$APP_NAME' no está activo. Saltando detención.${NC}"
fi

if sudo systemctl is-enabled --quiet "$APP_NAME"; then
    sudo systemctl disable "$APP_NAME"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Servicio '$APP_NAME' deshabilitado exitosamente.${NC}"
    else
        echo -e "${RED}Advertencia: No se pudo deshabilitar el servicio '$APP_NAME'. Continuando...${NC}"
    fi
else
    echo -e "${YELLOW}Servicio '$APP_NAME' no está habilitado. Saltando deshabilitación.${NC}"
fi

# --- 2. Eliminar el archivo del servicio systemd ---
echo -e "${YELLOW}2. Eliminando el archivo de servicio systemd...${NC}"
if [ -f "$SERVICE_PATH" ]; then
    sudo rm -f "$SERVICE_PATH"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Archivo de servicio '$SERVICE_PATH' eliminado exitosamente.${NC}"
    else
        echo -e "${RED}Error: No se pudo eliminar el archivo de servicio '$SERVICE_PATH'. Abortando.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Archivo de servicio '$SERVICE_PATH' no encontrado. Saltando eliminación.${NC}"
fi

# --- 3. Recargar el daemon de systemd ---
echo -e "${YELLOW}3. Recargando el daemon de systemd...${NC}"
sudo systemctl daemon-reload
echo -e "${GREEN}Daemon de systemd recargado.${NC}"

# --- 4. Eliminar el directorio de instalación ---
echo -e "${YELLOW}4. Eliminando el directorio de instalación '$INSTALL_DIR'...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    sudo rm -rf "$INSTALL_DIR"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Directorio '$INSTALL_DIR' y su contenido eliminados exitosamente.${NC}"
    else
        echo -e "${RED}Error: No se pudo eliminar el directorio '$INSTALL_DIR'. Abortando.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Directorio '$INSTALL_DIR' no encontrado. Saltando eliminación.${NC}"
fi

# --- 5. (Opcional) Eliminar el usuario del sistema ---
echo -e "${YELLOW}5. ¿Deseas eliminar el usuario del sistema '${APP_NAME}'?${NC}"
read -p "Esto eliminará el usuario y su grupo, pero no su directorio personal si lo tuviera. (s/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${YELLOW}Eliminando usuario y grupo '${APP_NAME}'...${NC}"
    if id -u "$APP_NAME" >/dev/null 2>&1; then
        sudo userdel "$APP_NAME"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Usuario '$APP_NAME' eliminado exitosamente.${NC}"
        else
            echo -e "${RED}Advertencia: No se pudo eliminar el usuario '$APP_NAME'. Puede que deba eliminarlo manualmente.${NC}"
        fi
    else
        echo -e "${YELLOW}Usuario '$APP_NAME' no existe. Saltando eliminación.${NC}"
    fi
else
    echo -e "${YELLOW}No se eliminará el usuario '${APP_NAME}'.${NC}"
fi

echo -e "${GREEN}¡Desinstalación completada!${NC}"

