ARG BASE_CONTAINER=xxxx.dkr.ecr.us-east-1.amazonaws.com/repo:latest
FROM $BASE_CONTAINER

USER root

COPY ./dist/*.whl /home/$USER/
RUN chown $USER_UID:$USER_GID /home/$USER/*.whl
#USER $QSRP_USER
WORKDIR $HOME

USER $USER
RUN /bin/bash -c "\
source activate new_env; \
pip install *.whl"