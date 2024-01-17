FROM python:3.10-alpine as base

FROM base as builder

RUN apk add build-base linux-headers
RUN mkdir /install
WORKDIR /install

COPY requirements.txt /requirements.txt

RUN pip install --prefix=/install -r /requirements.txt

FROM base

COPY --from=builder /install /usr/local
COPY entry_point.sh /entry_point.sh

RUN apk add git openssh-client
RUN echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config

RUN mkdir /app

CMD ["sh", "/entry_point.sh"]
