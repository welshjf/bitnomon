FROM debian:7
MAINTAINER Jacob Welsh <jacob@welshcomputing.com>

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y python-qt4 python-numpy python-rrdtool python-pip

RUN useradd -m test
USER test
WORKDIR /home/test
ENV QT_GRAPHICSSYSTEM=native
ADD bitnomon-*-bundle.tar /home/test/
RUN pip install --user --no-index -f bitnomon-*-bundle bitnomon
CMD ["/home/test/.local/bin/bitnomon"]
