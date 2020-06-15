# Makeflow for Drone Processing Pipeline

## Running the container
This section contains different ways of executing an existing container.

#### Scientific Filesystem <a name="scif" />
We use the [Scientific Filesystem](https://sci-f.github.io/) to organize our applications, provide ease of execution, and to assist in reproducability.

#### Shapefile <a name="shapefile_def" />
In this document we use the term "shapefile" to refer to all the files ending in `.shp`, `.shx`, `.dbf`, and `.prj` that have the same name.

### Canopy Cover: Orthomosaic and Shapefile
The following steps are used to generate plot-level canopy cover values for an orthomosaic image and a shapefile.
We will first present the steps and then provide an example.

1. Create a folder and copy the orthomosaic and the [shapefile](#shapefile_def) into it
2. Create a folder to contain the output folders and files
3. Run the docker container's `short_workflow` app specifying the name of the orthomosaic and shapefile

_NOTE_: that the orthomosaic and shapefile names are file names without their extensions; in other words, leave off the `.tif` and `.shp` when specifying them on the Docker command line.

**For example:**

In this example we're going to assume that the source image is named `orthomosaic.tif` and that the shapefile is named `plot_shapes.shp`.

Step 1 involves copying the source files into a folder:
```bash
mkdir ~/inputs
cp my_ortho.tif ~/inputs
cp my_shapefile.* ~/inputs
```

In step 2 we create an folder to hold the output of our processing:
```bash
mkdir ~/output
``` 

Finally we run the container mounting our source and destination folders, as well as indicating the name of the orthomosaic file and the name of the shapefile.
```bash
docker run -v ~/inputs:/scif/data/odm/images -v ~/outputs:/scif/data/soilmask agdrone/canopycover-shape-workflow:latest orthomosaic plot_shapes
```
Please refer to the [Docker](https://www.docker.com/) documentation for more information on running Docker containers.

_NOTE_: the above `docker` command line contains the files to use without their extensions (`orthomosaic` and `plot_shapes`).

## Build the container
This section describes how the Docker container could be built.
Please refer to the [Docker](https://www.docker.com/) documentation for more information on building Docker containers.

```bash
cp jx-args.json.example jx-args.json
docker build --progress=plain -t agdrone/canopycover-shape-workflow:latest .
```
