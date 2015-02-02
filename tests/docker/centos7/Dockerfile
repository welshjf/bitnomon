FROM centos:7
MAINTAINER Jacob Welsh <jacob@welshcomputing.com>
RUN yum -y install epel-release

RUN yum -y install PyQt4 numpy rrdtool-python python-pip

RUN useradd -m test
USER test
WORKDIR /home/test
ENV QT_GRAPHICSSYSTEM=native
ADD bitnomon-*-bundle.tar /home/test/
RUN pip install --user --no-index -f bitnomon-*-bundle bitnomon
CMD ["/home/test/.local/bin/bitnomon"]
