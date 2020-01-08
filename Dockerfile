FROM python:3
MAINTAINER SatNOGS project <dev@satnogs.org>

WORKDIR /workdir/

RUN groupadd -r satnogs \
	&& useradd -r -g satnogs satnogs \
	&& install -d -m 755 -o satnogs -g satnogs /var/run/celery

RUN apt-get update \
	&& apt-get -y install ruby-sass \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt /usr/local/src/satnogs-network/
RUN pip install \
	--no-cache-dir \
	--no-deps \
	--force-reinstall \
	-r /usr/local/src/satnogs-network/requirements.txt

COPY . /usr/local/src/satnogs-network/
RUN pip install \
	--no-cache-dir \
	--no-deps \
	--force-reinstall \
	/usr/local/src/satnogs-network
RUN install -m 755 /usr/local/src/satnogs-network/bin/djangoctl.sh /usr/local/bin/

RUN rm -rf /usr/local/src/satnogs-network

ENV DJANGO_SETTINGS_MODULE network.settings

EXPOSE 8000
