FROM ubuntu:12.04
MAINTAINER Jacob Welsh <jacob@welshcomputing.com>

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y python-qt4 python-numpy python-rrdtool python-pip

# useradd broken because SELinux
RUN echo test:x:1000:1000::/home/test:/bin/bash >> /etc/passwd && \
    echo test:x:1000: >> /etc/group && \
    mkdir /home/test && \
    chown test:test /home/test
USER test
WORKDIR /home/test
ENV QT_GRAPHICSSYSTEM=native
ADD bitnomon-*-bundle.tar /home/test/
RUN cd bitnomon-*-bundle && pip install --user --no-index appdirs* bitnomon*
CMD ["/home/test/.local/bin/bitnomon"]
