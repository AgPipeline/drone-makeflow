FROM ubuntu:18.04
LABEL maintainer="Chris Schnaufer <schnaufer@email.arizona.edu>"

# Build environment values
ARG arg_cctools_url=https://github.com/cooperative-computing-lab/cctools.git
ENV cctools_url=$arg_cctools_url

ARG arg_cctools_branch=master
ENV cctools_branch=$arg_cctools_branch

ENV DEBIAN_FRONTEND=noninteractive

# Install any users
RUN useradd -u 49044 extractor \
    && mkdir /home/extractor \
    && mkdir /home/extractor/sites

RUN chown -R extractor /home/extractor \
    && chgrp -R extractor /home/extractor

COPY requirements.txt packages.txt /home/extractor/

RUN [ -s /home/extractor/packages.txt ] && \
    (echo 'Installing packages' && \
        apt-get update && \
        cat /home/extractor/packages.txt | xargs apt-get install -y --no-install-recommends && \
        rm /home/extractor/packages.txt && \
        apt-get autoremove -y && \
        apt-get clean && \
        rm -rf /var/lib/apt/lists/*) || \
    (echo 'No packages to install' && \
        rm /home/extractor/packages.txt)

RUN [ -s /home/extractor/requirements.txt ] && \
    (echo "Install python modules" && \
    python3 -m pip install -U --no-cache-dir pip && \
    python3 -m pip install --no-cache-dir setuptools && \
    python3 -m pip install --no-cache-dir -r /home/extractor/requirements.txt && \
    rm /home/extractor/requirements.txt) || \
    (echo "No python modules to install" && \
    rm /home/extractor/requirements.txt)

# Install GDAL
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgdal-dev \
        gcc \
        g++ \
        python3-dev && \
    python3 -m pip install --upgrade --no-cache-dir \
        pygdal==2.2.3.5 && \
    apt-get remove -y \
        libgdal-dev \
        gcc \
        g++ \
        python3-dev && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install cctools from source
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        gcc \
        g++ \
        make \
        zlib1g-dev && \
    git clone $cctools_url --branch $cctools_branch --single-branch "/home/extractor/cctools-source" && \
    cd /home/extractor/cctools-source && \
    ./configure --without-system-doc  --prefix /home/extractor/cctools && \
    make && \
    make install && \
    rm -rf /home/extractor/cctools-source && \
    chown -R extractor /home/extractor/cctools && \
    apt-get remove -y \
        git \
        gcc \
        g++ \
        make \
        zlib1g-dev && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Docker
RUN apt-get update && \
    apt-get install -y --reinstall systemd && \
    apt-get remove -y docker docker-engine docker.io containerd runc && \
    apt-get install -y --no-install-recommends \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg-agent \
        software-properties-common && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - && \
    apt-key fingerprint 0EBFCD88 && \
    add-apt-repository \
        "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) \
        stable" && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        docker-ce \
        docker-ce-cli \
        containerd.io && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY *.py *.jx *.json *.sh /home/extractor/
RUN chown -R extractor /home/extractor/ && chgrp -R extractor /home/extractor/ && chmod a+x /home/extractor/*.sh

USER extractor
ENTRYPOINT ["/home/extractor/entrypoint.sh"]
CMD ["extractor"]

# Setup environment variables. These are passed into the container. You can change
# these to your setup. If RABBITMQ_URI is not set, it will try and use the rabbitmq
# server that is linked into the container. MAIN_SCRIPT is set to the script to be
# executed by entrypoint.sh
ENV RABBITMQ_EXCHANGE="terra" \
    RABBITMQ_VHOST="%2F" \
    RABBITMQ_QUEUE="drone.makeflow" \
    MAIN_SCRIPT="drone_makeflow.py" \
    PATH="/home/extractor/cctools/bin:${PATH}"
