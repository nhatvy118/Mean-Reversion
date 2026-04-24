FROM --platform=linux/amd64 python:3.10

RUN apt-get update && apt-get install -y \
    build-essential \
    swig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --upgrade pip wheel
RUN pip install -r requirements.txt
RUN pip install paperbroker_client-0.2.4-py3-none-any.64a14680f78f.whl

CMD ["python"]
