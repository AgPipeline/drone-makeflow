# Makeflow for Drone Processing Pipeline

## Build the container

```bash
cp jx-args.json.example jx-args.json
docker build --progress=plain -t agpipeline/scif-drone-pipeline:1.3 .
```


## Run the workflow

```bash
mkdir -p test
wget -O test/testimages.tar https://de.cyverse.org/dl/d/84A57A62-B6EB-4826-ADC4-337D4A0ABBEA/images.tar
tar xf test/images.tar --wildcards "*.JPG" -C test/
INPUT_DATA_DIR=$(pwd)/test/images
OUTPUT_DATA_DIR=$(pwd)/test/output
mkdir -p "${OUTPUT_DATA_DIR}"
docker run --rm \
    -v "${INPUT_DATA_DIR}:/scif/data/odm/images" \
    -v "${OUTPUT_DATA_DIR}:/scif/data/soilmask" \
    agpipeline/scif-drone-pipeline:1.3 run makeflow
```