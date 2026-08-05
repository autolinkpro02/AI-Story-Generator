FROM ollama/ollama:latest

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends python3 python3-pip curl \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

COPY app.py /app/app.py
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

ENV OLLAMA_HOST=http://127.0.0.1:11434
EXPOSE 8000 11434

CMD ["/bin/bash", "/app/start.sh"]
