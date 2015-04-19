FROM python:3.4-wheezy

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip install -r requirements.txt

COPY . /usr/src/app

ENTRYPOINT ["python3", "bin/ssh_forward_proxy.py"]

