FROM python:3.4-wheezy

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip install -r requirements.txt

EXPOSE 22

COPY . /usr/src/app

