# Imagen base oficial de Playwright: ya incluye Chromium y todas las
# dependencias de sistema necesarias. La versión del tag DEBE coincidir con
# la versión de playwright fijada en requirements.txt.
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

# Instalar dependencias de Python primero (mejor uso de la caché de capas).
# --trusted-host: evita el fallo de verificación SSL de pip cuando se
# construye detrás de un proxy corporativo con inspección de tráfico.
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host pypi.python.org \
    -r requirements.txt

# Copiar el resto de la aplicación
COPY . .

# Configuración por defecto (sobreescribible con -e en docker run)
ENV HOST=0.0.0.0 \
    PORT=9000 \
    PYTHONUNBUFFERED=1

EXPOSE 9000

# Servidor de producción. --timeout alto porque cada consulta lanza un
# navegador y resuelve el captcha (puede tardar 15-30s).
CMD ["gunicorn", "--bind", "0.0.0.0:9000", "--workers", "2", "--timeout", "120", "app:app"]
