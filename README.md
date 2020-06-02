# Makeflow for Drone Processing Pipeline

## Build the container

```bash
cp jx-args.json.example jx-args.json
docker build --progress=plain -t agpipeline/scif-drone-pipeline:1.3 .
```

## Run the workflow with existing Orthomosaic image
```bash
INPUT_DATA_DIR=$(pwd)/test/images
OUTPUT_DATA_DIR=$(pwd)/test/output
mkdir -p "${INPUT_DATA_DIR}"
mkdir -p "${OUTPUT_DATA_DIR}"
wget -O test/testimages.tar https://de.cyverse.org/dl/d/84A57A62-B6EB-4826-ADC4-337D4A0ABBEA/images.tar
tar xf test/images.tar -C test/
docker run --rm \
    -v "${INPUT_DATA_DIR}:/scif/data/odm/images" \
    -v "${OUTPUT_DATA_DIR}:/scif/data/soilmask" \
    agpipeline/scif-drone-pipeline:1.3 run short_makeflow
```

## Run the workflow with OpenDroneMap
This workflow requires the use of two named Docker volumes; one for input and one for output.

The first step is to setup the Docker volumes to use.
The names used here can be changed to suit your needs.
```bash
docker volume create data_input
docker volume create data_output
```

Next setup the local folders with the source data
```bash
INPUT_DATA_DIR=$(pwd)/test/images
OUTPUT_DATA_DIR=$(pwd)/test/output
mkdir -p "${INPUT_DATA_DIR}"
mkdir -p "${OUTPUT_DATA_DIR}"
wget -O test/testimages.tar https://de.cyverse.org/dl/d/84A57A62-B6EB-4826-ADC4-337D4A0ABBEA/images.tar
tar xf test/images.tar --wildcards "*.JPG" -C test/
```
Run the docker image
```bash
docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \x
    -v "data_input:/scif/data/odm/images" \
    -v "data_output:/scif/data/soilmask" \
    -v "${INPUT_DATA_DIR}:/input" \
    -v "${OUTPUT_DATA_DIR}:/output" \
    agpipeline/scif-drone-pipeline:1.3 run makeflow
```
