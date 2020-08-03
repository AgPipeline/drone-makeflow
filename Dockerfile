FROM ubuntu:18.04 as base
ENV DOCKER_IMAGE agpipeline/scif-drone-pipeline:1.3
ENV DEBIAN_FRONTEND noninteractive
WORKDIR /

#Install dependencies
RUN apt-get update -y \
    && apt-get install --no-install-recommends -y \
    software-properties-common \
    wget \
    python3-gdal \
    gdal-bin   \
    libgdal-dev \
    gcc \
    g++ \
    libsm6 \
    libxext6 \
    libxrender1 \
    libglib2.0-0 \
    liblas-bin \
    docker.io \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Docker
RUN apt-get update -y && \
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


# Install base for running workflows
FROM base as download_miniconda
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /root/miniconda.sh

FROM base as install_miniconda
WORKDIR /root
COPY --from=download_miniconda /root/miniconda.sh .
RUN /bin/bash ~/miniconda.sh -b -p /opt/conda \
    && rm ~/miniconda.sh \
    && /opt/conda/bin/conda clean -tipsy \
    && ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh \
    && echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc \
    && echo "conda activate base" >> ~/.bashrc \
    && find /opt/conda/ -follow -type f -name '*.a' -delete \
    && find /opt/conda/ -follow -type f -name '*.js.map' -delete \
    && /opt/conda/bin/conda clean -afy \
    && echo "Finished installing miniconda!"
ENV PATH /opt/conda/bin:$PATH
WORKDIR /


FROM install_miniconda as base_scif
RUN pip install --upgrade --no-cache-dir scif \
    && echo "Finished install of scif" \
    && pip install --upgrade --no-cache-dir pygdal==2.2.3.5 \
    && echo "Finished install of pygdal"
ENTRYPOINT ["scif"]

ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal

# Install the apps
FROM base_scif as odm_scif
COPY ./scif_app_recipes/opendronemap_v0.9.1_ubuntu16.04.scif  /opt/
RUN scif install /opt/opendronemap_v0.9.1_ubuntu16.04.scif

FROM odm_scif as combined_scif
COPY ./scif_app_recipes/ndcctools_v7.1.2_ubuntu16.04.scif  /opt/
COPY ./scif_app_recipes/soilmask_v0.0.1_ubuntu16.04.scif /opt/
RUN scif install /opt/soilmask_v0.0.1_ubuntu16.04.scif
RUN scif install /opt/ndcctools_v7.1.2_ubuntu16.04.scif

FROM combined_scif as plotclip_scif
COPY ./scif_app_recipes/plotclip_v0.0.1_ubuntu16.04.scif /opt/
RUN scif install /opt/plotclip_v0.0.1_ubuntu16.04.scif

FROM plotclip_scif as canopycover_scif
COPY ./scif_app_recipes/canopycover_v0.0.1_ubuntu16.04.scif /opt/
RUN scif install /opt/canopycover_v0.0.1_ubuntu16.04.scif

FROM canopycover_scif as workflow
COPY workflow.jx short_workflow.jx canopy-cover.jx betydb2geojson.py cyverse_short_workflow.sh generate_geojson.sh prep-canopy-cover.sh /scif/apps/odm_workflow/src/
RUN chmod a+x /scif/apps/odm_workflow/src/*.sh
RUN chmod a+x /scif/apps/odm_workflow/src/betydb2geojson.py
