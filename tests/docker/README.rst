Testing with Docker
===================

Copy the bundle to the desired OS subdirectory, then::

    docker build -t <img-name> <dir>

    docker run -ti --rm --net=host --security-opt label:disable -e DISPLAY \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -v ${XAUTHORITY:-$HOME/.Xauthority}:/home/test/.Xauthority \
        -v $HOME/.bitcoin:/home/test/.bitcoin <img-name>
