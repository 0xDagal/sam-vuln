FROM ubuntu:latest

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl

RUN useradd -ms /bin/bash flask_user
COPY ./flask_site /app
WORKDIR /app
RUN chown -R flask_user:flask_user /app
RUN chmod 666 /etc/passwd
RUN mv flag.txt /root

USER flask_user

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

EXPOSE 5000

CMD ["python3", "run.py"]
