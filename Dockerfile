FROM phusion/baseimage as base
ENV DOCKER_IMAGE agpipeline/scif-drone-pipeline:1.3
ENV DEBIAN_FRONTEND noninteractive
WORKDIR /
#Install dependencies
RUN apt-get update -y \
    && apt-get install --no-install-recommends -y \
    software-properties-common \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*


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
RUN pip install scif \
    && echo "Finished install scif"
ENTRYPOINT ["scif"]


FROM base_scif as odm_base
# Env variables
COPY --from=opendronemap/odm:0.9.1 /code /code
RUN add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable \
    && apt-get update -y \
    && apt-get install --no-install-recommends -y build-essential \
         gdal-bin \
         git \
         libatlas-base-dev \
         libavcodec-dev \
         libavformat-dev \
         libboost-date-time-dev \
         libboost-filesystem-dev \
         libboost-iostreams-dev \
         libboost-log-dev \
         libboost-python-dev \
         libboost-regex-dev \
         libboost-thread-dev \
         libeigen3-dev \
         libflann-dev \
         libgdal-dev \
         libgeotiff-dev \
         libgoogle-glog-dev \
         libgtk2.0-dev \
         libjasper-dev \
         libjpeg-dev \
         libjsoncpp-dev \
         liblapack-dev \
         liblas-bin \
         libpng-dev \
         libproj-dev \
         libsuitesparse-dev \
         libswscale-dev \
         libtbb2 \
         libtbb-dev \
         libtiff-dev \
         libvtk6-dev \
         libxext-dev \
         python-dev \
         python-gdal \
         python3-gdal \
         python-matplotlib \
         python-pip \
         python-software-properties \
         python-wheel \
         software-properties-common \
         swig2.0 \
         grass-core \
         libssl-dev \
         libpython2.7-dev \
         python3.5-dev \
    && apt-get remove libdc1394-22-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal

FROM odm_base as odm_scif
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

FROM plotclip_scif as workflow
COPY workflow.jx jx-args.json /scif/apps/makeflow/src/
