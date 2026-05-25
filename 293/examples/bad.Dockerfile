FROM ubuntu:20.04

MAINTAINER developer@example.com

RUN apt-get update

RUN apt-get install -y python3
RUN apt-get install -y python3-pip
RUN apt-get install -y git
RUN apt-get install -y curl

WORKDIR /app

ADD . /app

COPY requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt

RUN pip install --upgrade pip

COPY src /app/src

RUN echo "Build complete"

RUN echo "Cleaning up..."

CMD ["python3", "app.py"]
