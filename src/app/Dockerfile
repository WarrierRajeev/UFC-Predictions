FROM python:3.6-slim-stretch

RUN apt-get update && apt-get install -y python3-dev gcc \
    && rm -rf /var/lib/apt/lists/*

ADD . /app

COPY requirements.txt /app

COPY app_data /app/app_data

WORKDIR /app

RUN pip install --trusted-host pypi.python.org -r requirements.txt

CMD gunicorn app:app.server --bind 0.0.0.0:$PORT --reload
