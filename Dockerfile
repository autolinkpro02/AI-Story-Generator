FROM ollama/ollama:latest

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip python3-venv bash curl \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app.py /app/app.py
COPY web_app.py /app/web_app.py
COPY regenerate_scene.py /app/regenerate_scene.py
COPY index.html /app/index.html
COPY config.py /app/config.py
COPY script_generator.py /app/script_generator.py
COPY project_manager.py /app/project_manager.py
COPY modules /app/modules
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

ENV OLLAMA_HOST=http://127.0.0.1:11434
ENV OLLAMA_PULL_MODEL=false
EXPOSE 8000 11434

ENTRYPOINT ["/bin/bash", "/app/start.sh"]