FROM python:3.8
WORKDIR /workdir
RUN apt-get -y update && apt-get -y upgrade
RUN apt-get -y install vim less

COPY requirements.txt .
RUN pip install -r requirements.txt

CMD ["gunicorn", "--bind", ":80", "--worker-tmp-dir", "/dev/shm", "--workers=1", "--threads=2", "app:app"]
