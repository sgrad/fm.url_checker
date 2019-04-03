FROM python:3-alpine3.7
LABEL maintainer="Stefan Gradinar <email@nospam.com>"
ENV PYTHONPATH=/server/apps/fm.url_checker
RUN mkdir -p /server/apps/ometria.fm.url_checker /server/env
WORKDIR /server/apps/fm.url_checker
# -- Install pipenv
RUN set -ex && pip install pipenv --upgrade
# -- Adding Pipfiles
COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock

RUN set -ex \
	&& apk add --update --no-cache --virtual .buildDeps \
        linux-headers \
        musl-dev \
        build-base \
        git \
        gcc \
        libffi-dev \
	&& apk add --update --no-cache postgresql-dev libxml2 libxml2-dev libxslt-dev \
    # Check stack-fix.c for details
    && pipenv install --deploy --system \
    && apk del --purge .buildDeps \
    && rm -rf /root/.cache/* \
    && rm -rf /var/cache/apk/*
COPY . /server/apps/fm.url_checker
