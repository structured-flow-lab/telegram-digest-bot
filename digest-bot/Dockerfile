FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

# data/ holds the SQLite DB and the Telethon session file — mount as a
# persistent volume at runtime, do not bake any data into the image.
VOLUME ["/app/data"]

CMD ["python", "app/main.py"]
