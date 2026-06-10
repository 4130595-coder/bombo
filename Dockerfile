FROM python:3.11-slim

# Install Chrome + noVNC + VNC server
RUN apt-get update && apt-get install -y \
    chromium \
    x11vnc \
    xvfb \
    novnc \
    websockify \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

EXPOSE 8080

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
CMD ["/usr/bin/supervisord"]
