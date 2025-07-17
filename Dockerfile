FROM nvidia/cuda:12.9.1-cudnn-devel-ubuntu22.04

ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive


RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    ffmpeg \
    libpq-dev \
    gcc \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*


ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/local/cuda/targets/x86_64-linux/lib:$LD_LIBRARY_PATH

RUN wget https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh -O /usr/bin/wait-for-it.sh \
    && chmod +x /usr/bin/wait-for-it.sh


WORKDIR /app


COPY req_2_final.txt .

RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

RUN pip3 install --no-cache-dir -r req_2_final.txt


COPY . /app


EXPOSE 8000

# The command to run the application is now in docker-compose.yml
# CMD ["sh", "-c", "python3 init_db.py && waitress-serve --listen=0.0.0.0:8000 app1:app"]





