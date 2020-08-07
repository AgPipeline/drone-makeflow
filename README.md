# Makeflow for Drone Processing Pipeline

## Running the container

This section contains different ways of executing an existing container.

### Terms

Here are the definition of some of the terms we use with links to additional information

* BETYdb <a name="betydb" />
[BETYdb](https://www.betydb.org/) is a database that can be used to store trait and yield data.
It can be used in the processing pipeline as a source of plot geometry for clipping.

* GeoJSON <a name="geojson" />
[GeoJSON](https://datatracker.ietf.org/doc/rfc7946/) is a JSON format for specifying geographic shape information.
This is the default format for specifying plot geometries.

* Scientific Filesystem <a name="scif" />
We use the [Scientific Filesystem](https://sci-f.github.io/) to organize our applications, provide ease of execution, and to assist in reproducibility.

* Shapefile <a name="shapefile_def" />
In this document we use the term "shapefile" to refer to all the files ending in `.shp`, `.shx`, `.dbf`, and `.prj` that have the same name.
It can be used to specify geographic information and shapes associated with plot geometries.

### Canopy Cover: Orthomosaic and plot boundaries <a name="om_can_shp" />

The following steps are used to generate plot-level canopy cover values for a georeferenced orthomosaic image and plot boundaries using geographic information.
We will first present the steps and then provide an example.

1. Create a folder and copy the orthomosaic into it
2. If using a [shapefile](#shapefile) or [GeoJSON](#geojson) file, copy those into the same folder as the orthomosaic image
3. Create another folder for the output folders and files
4. Run the docker container's `short_workflow` app specifying the name of the orthomosaic and either the name of the shapefile or geojson file, or the URL of they [BETYdb](#betydb) instance to query for plot boundaries

_NOTE_: that the orthomosaic must be the file name without any extensions; in other words, leave off the `.tif` when specifying it on the Docker command line.


#### For example: <a name="can_shp_example" />

You can download a sample dataset of files (archived) with names corresponding to those listed here from CyVerse using the following command.
Be sure to replace **<username** and **<password>** with your CyVerse username and password.
```bash
curl -X GET -u '<username>:<password>>' https://data.cyverse.org/dav/iplant/projects/aes/cct/diag/sample-data/scif_test_data.tar.gz > scif_test_data.tar.gz
gunzip scif_test_data.tar.gz
tar -xf scif_test_data.tar
```


In this example we're going to assume that the source image is named `orthomosaic.tif` and that we're using a shapefile named `plot_shapes.shp`.

We will need one other file for this example, the `experiment.yaml` file containing some additional information.
Copy the following content into the experiment.yaml file:
```text
%YAML 1.1
---
pipeline:
    studyName: 'S7_20181011'
    season: 'S7_20181011'
    germplasmName: Sorghum bicolor
    collectingSite: Maricopa
    observationTimeStamp: '2018-10-11T13:01:02-08:00'
```

First we copy all the source files into a folder:
```bash
mkdir /inputs
cp orthomosaic.tif /inputs
cp plot_shapes.* /inputs
cp experiment.yaml /inputs
```

Next we create an folder to hold the output of our processing:
```bash
mkdir /output
``` 

Finally we run the container mounting our source and destination folders, as well as indicating the name of the orthomosaic file and the name of the shapefile.
```bash
docker run --rm -v    d/inputs:/scif/data/odm/images -v /outputs:/output agdrone/canopycover-workflow:latest run short_workflow orthomosaic plot_shapes.shp
```
Please refer to the [Docker](https://www.docker.com/) documentation for more information on running Docker containers.

_NOTE_: the above `docker` command line contains the oprthomosaic file without its extension (`orthomosaic`).

**Results:**
Upon a successful run the output will contain one sub-folder for each plot.
In the sub-folders for plots that intersected with the orthomosaic, there will be the clipped `.tif` file and two `.csv` files.
The CSV files both contain much of the same information.
The file with "geostreams" in its name can be uploaded to TERRAREF's Geostreams database.  

### Canopy Cover: OpenDroneMap and plot boundaries <a name="opendm_can_shp" />

The following steps are used when wanting to use OpenDroneMap (ODM) to create the Orthomosaic image that's then used to create the canopy cover values.
As with the [previous example](#om_can_shp) we will be listing the steps and then providing an example.

_NOTE_: the SciF Docker image uses Docker sibling containers to run the OpenDroneMap application.
Please read our section on [Docker Sibling Containers](#docker_sibling_containers) below to be informed of potential risks with this approach.

1. Create two named Docker volumes to use for processing data; one for input files and one for output files - the same volume can be used for both if desired
2. Copy the source drone images into a folder
3. If using a [shapefile](#shapefile) or [GeoJSON](#geojson) file, copy those into the same folder as the drone images
4. Copy the experiment metadata file into the same folder as the drone images
5. Copy the folder contents of the drone images folder that was just prepared onto the input named volume
6. Create another folder for the output folders and files
7. Run the docker container's `odm_workflow` app specifying  either the name of the shapefile or geojson file, or the URL of they [BETYdb](#betydb) instance to query for plot boundaries, and the two named volumes
8. Copy the resulting files off the output named volume to the local folder
9. Clean up the named volumes

#### For example: <a name="opendm_can_shp_example" />

You can download a sample dataset of files (archived) with names corresponding to those listed here from CyVerse using the following command.
Be sure to replace **<username** and **<password>** with your CyVerse username and password.
```bash
curl -X GET -u '<username>:<password>>' https://data.cyverse.org/dav/iplant/projects/aes/cct/diag/sample-data/scif_odm_test_data.tar.gz > scif_odm_test_data.tar.gz
gunzip scif_odm_test_data.tar.gz
tar -xf scif_odm_test_data.tar
```

In this example we're going to assume that we're using a shapefile named `plot_shapes.shp`, and that we have our drone images in a folder named `/IMG`.

We will need one other file for this example, the `experiment.yaml` file containing some additional information.
Copy the following content into the experiment.yaml file:
```text
%YAML 1.1
---
pipeline:
    studyName: 'S7_20181011'
    season: 'S7_20181011'
    germplasmName: Sorghum bicolor
    collectingSite: Maricopa
    observationTimeStamp: '2018-10-11T13:01:02-08:00'
```

Step 1 requires creating two named Docker volumes to use when processing.
If you already have one or more empty named volumes you can skip this step.
```bash
docker volume create my_input
docker volume create my_output
``` 

Step 2 involves copying the drone images into a folder:
```bash
mkdir -p /inputs
cp /IMG/* /inputs/
```

Step 3 copies the optional shapefile files into the same folder as the drone images:
```bash
cp /plot_shapes.* /inputs/
``` 

In step 4 we copy the experiment.yaml file into the same folder as the drone images:
```bash
cp experiment.yaml /inputs/
``` 

In step 5 we copy the source files onto the input named volume:
```bash
docker run --rm -v /inputs:/sources -v my_input:/input --entrypoint bash agdrone/canopycover-workflow:latest -c 'cp /sources/* /input/'
``` 

In step 6 we create a local folder to hold the output from processing:
```bash
mkdir -p /output
```

In step 7 we run the workflow to generate the orothomosaic image using ODM (OrthoDroneMap) and calculate plot-level canopy cover:
```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v /inputs:/scif/data/odm/images -v scif_output:/output -e INPUT_VOLUME=my_input -e OUTPUT_VOLUME=my_output -e "INPUT_IMAGE_FOLDER=/images" -e "OUTPUT_FOLDER=/output" agdrone/canopycover-workflow:latest run odm_workflow plot_shapes.shp my_input my_output
```
and we wait until it's finished.

In step 8 we copy the results off the named output volume to our local folder:
```bash
docker run --rm -v /output:/results -v my_output:/output --entrypoint bash agdrone/canopycover-workflow:latest -c 'cp -r /output/* /results/'
```
The results of the processing are now in the `/output` folder.

Finally, in step 9 we clean up the named volumes by deleting everything on them:
```bash
docker run --rm -v my_input:/input -v my_output:/output --entrypoint bash agdrone/canopycover-workflow:latest -c 'rm -r /input/* && rm -r /output/*'
```

### Clean

By executing the [scif](#scif) app named `clean` it's possible to clean up the output folder and other generated files.
It's recommended, but not necessary, to run the clean app between processing runs by either running this command or through other means.

**Example:**

This docker command line will clean up the output files generated using the [Canopy Cover: Orthomosaic and Shapefile](#om_can_shp) example above.
```bash
docker run --rm -v /inputs:/scif/data/odm/images -v /outputs:/scif/data/soilmask agdrone/canopycover-shape-workflow:latest run clean
```

## Build the container

This section describes how the Docker container could be built.
Please refer to the [Docker](https://www.docker.com/) documentation for more information on building Docker containers.

```bash
cp jx-args.json.example jx-args.json
docker build --progress=plain -t agdrone/canopycover-shape-workflow:latest .
```

## Docker Sibling Containers

Sibling containers is a technique for having one Docker container start another Docker container to perform some work.
There are a variety of instances where using sibling containers can be desirable, but typically it's used when there's an existing Docker image available and a determination has been made that using other approaches is not desirable or, perhaps, possible.

The following links provide additional information on sibling containers:
* https://medium.com/@andreacolangelo/sibling-docker-container-2e664858f87a
* https://www.develves.net/blogs/asd/2016-05-27-alternative-to-docker-in-docker/

**Security Risk**

One of the consequences of using sibling containers is that the second container needs to be started with the `root` user due to technical considerations.
Because of this need, using sibling containers can be considered a security risk.
The severity of this risk dependent upon the execution environment and what systems the siblings have access to.
