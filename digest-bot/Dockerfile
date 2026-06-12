FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

# data/ holds the SQLite DB and the Telethon session file — mount a Railway
# Volume at /app/data at runtime, do not bake any data into the image.
CMD ["python", "app/main.py"]
