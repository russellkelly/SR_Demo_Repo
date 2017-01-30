FROM ubuntu:14.04

MAINTAINER Russell Kelly (russell@arista.net)

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update
RUN apt-get install -qy --no-install-recommends wget python git
RUN apt-get install -qy openssh-server
RUN apt-get install -qy openssh-client
RUN apt-get install -qy python-pip
RUN apt-get install -qy python-dev
RUN apt-get install -qy libxml2-dev
RUN apt-get install -qy libxslt-dev
RUN apt-get install -qy libssl-dev
RUN apt-get install -qy libffi-dev
RUN apt-get install -qy sudo
RUN apt-get install -qy vim
RUN apt-get install -qy telnet
RUN apt-get install -qy curl
RUN apt-get install -qy shellinabox
RUN apt-get clean
RUN pip install flask
RUN pip install pyeapi
RUN pip install jsonrpc
RUN pip install git+https://github.com/Juniper/py-junos-eznc.git

RUN useradd -m demo && echo "demo:demo" | chpasswd && adduser demo sudo

USER root

RUN mkdir /home/demos/sr-demo
ENV HOME /home/demos/sr-demo
WORKDIR /home/demos/sr-demo

RUN git clone https://github.com/Exa-Networks/exabgp.git
WORKDIR /home/demos/sr-demo/exabgp
RUN git checkout master
RUN chmod +x setup.py
RUN sudo ./setup.py install
WORKDIR /home/demos/sr-demo


EXPOSE 179
EXPOSE 5000
EXPOSE 5001
EXPOSE 4200

COPY exabgp.env /usr/local/etc/exabgp/exabgp.env

USER demo
