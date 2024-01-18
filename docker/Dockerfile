FROM python:3.11-bullseye as base

FROM base as builder

RUN mkdir /install
WORKDIR /install

COPY requirements.txt /requirements.txt

RUN pip install --prefix=/install -r /requirements.txt

FROM base

COPY --from=builder /install /usr/local
COPY entry_point.sh /entry_point.sh

RUN apt update && apt install -y git openssh-client ffmpeg libsm6 libxext6
RUN echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config

RUN mkdir /app

CMD ["sh", "/entry_point.sh"]
