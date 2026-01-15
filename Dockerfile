FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Бесконечный цикл с рестартом
CMD ["bash", "-c", "while true; do echo 'Starting bot...'; python main.py; echo 'Bot crashed, restarting in 5 seconds...'; sleep 5; done"]
