FROM python:3.12-slim-bookworm


RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app


RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu


COPY reqfinal.txt .
RUN pip install --no-cache-dir -r reqfinal.txt

COPY . .

EXPOSE 5000


CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "app1:app"]