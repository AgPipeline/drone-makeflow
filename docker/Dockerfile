FROM ubuntu:18.04
LABEL maintainer="Chris Schnaufer <schnaufer@email.arizona.edu>"

# Build environment values
ARG arg_cctools_url=https://github.com/cooperative-computing-lab/cctools.git
ENV cctools_url=$arg_cctools_url

ARG arg_cctools_branch=master
ENV cctools_branch=$arg_cctools_branch

ENV DEBIAN_FRONTEND=noninteractive

# Install any users
RUN useradd -u 49044 workflow \
    && mkdir /home/workflow

RUN chown -R workflow /home/workflow \
    && chgrp -R workflow /home/workflow

COPY docker/requirements.txt docker/packages.txt /home/workflow/

# Package installation
RUN [ -s /home/workflow/packages.txt ] && \
    (echo 'Installing packages' && \
        apt-get update && \
        cat /home/workflow/packages.txt | xargs apt-get install -y --no-install-recommends && \
        rm /home/workflow/packages.txt && \
        apt-get autoremove -y && \
        apt-get clean && \
        rm -rf /var/lib/apt/lists/*) || \
    (echo 'No packages to install' && \
        rm /home/workflow/packages.txt)

# Python installation
RUN [ -s /home/workflow/requirements.txt ] && \
    (echo "Install python modules" && \
    python3 -m pip install -U --no-cache-dir pip && \
    python3 -m pip install --no-cache-dir setuptools && \
    python3 -m pip install --no-cache-dir -r /home/workflow/requirements.txt && \
    rm /home/workflow/requirements.txt) || \
    (echo "No python modules to install" && \
    rm /home/workflow/requirements.txt)

# Install cctools from source
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        gcc \
        g++ \
        make \
        zlib1g-dev && \
    git clone $cctools_url --branch $cctools_branch --single-branch "/home/workflow/cctools-source" && \
    cd /home/workflow/cctools-source && \
    ./configure --without-system-doc  --prefix /home/workflow/cctools && \
    make && \
    make install && \
    rm -rf /home/workflow/cctools-source && \
    chown -R workflow /home/workflow/cctools && \
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

# Finish setting up
WORKDIR /home/workflow
COPY *.py *.jx *.sh docker/*.sh /home/workflow/
RUN chown workflow /home/workflow/* && chmod a+x /home/workflow/*.sh

USER workflow
ENTRYPOINT ["/home/workflow/entrypoint.sh"]

# Setup environment variables to be passed into the container.
ENV PATH="/home/workflow/cctools/bin:${PATH}"
