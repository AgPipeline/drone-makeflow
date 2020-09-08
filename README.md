# Makeflow for Drone Processing Pipeline

There are two main workflows in the Docker image built from this repository.

The shorter workflow uses an orthomosaic file, a plot geometry file, and an experiment context file and calculates the canopy cover for each of the plots which is saved into CSV file(s).

The longer workflow is the `odm_workflow`.
It uses image files captured by a drone, a plot geometry file, and an experiment context file and processes the drone image files using OpenDroneMap (ODM).
After ODM has created the orthomosaic, the file is processed to produce plot-level canopy cover CSV file(s).

The [Scientific Filesystem](https://sci-f.github.io/) is used as to provide the entry points for the different tasks available (known as "apps" with the Scientific Filesystem).
These apps are used by the above workflows and can be used to create custom workflows outside of what's provided.

## Running the workflow

This section contains different ways of executing an existing Docker workflow container.

### Terms used

Here are the definition of some of the terms we use with links to additional information

* BETYdb <a name="betydb_def" />
[BETYdb](https://www.betydb.org/) is a database that can be used to store trait and yield data.
It can be used in the processing pipeline as a source of plot geometry for clipping.

* GeoJSON <a name="geojson_def" />
[GeoJSON](https://datatracker.ietf.org/doc/rfc7946/) is a JSON format for specifying geographic shape information.
This is the default format for specifying plot geometries.

* Scientific Filesystem <a name="scif_def" />
We use the [Scientific Filesystem](https://sci-f.github.io/) to organize our applications, provide ease of execution, and to assist in reproducibility.

* Shapefile <a name="shapefile_def" />
In this document we use the term "shapefile" to refer to all the files ending in `.shp`, `.shx`, `.dbf`, and `.prj` that have the same name.
It can be used to specify geographic information and shapes associated with plot geometries.

### Prerequisites

- Docker needs to be installed to run the workflows. [Get Docker](https://docs.docker.com/get-docker/)
- Create an `inputs` folder in the current working directory (or other folder of your choice)
```bash
mkdir -p "${PWD}/inputs"
```
- Create an `outputs` folder in the current working directory (or other folder of your choice)
```bash
mkdir -p "${PWD}/outputs"
```
- Create an output folder.
The `checkpoints` folder will contain the generated workflow checkpoint data allowing easy recovery from an error and helps prevent re-running an already completed workflow.
Removing the workflow checkpoint files will enable a complete re-run of the workflow:
```bash
mkdir -p "${PWD}/checkpoints"
``` 

### Canopy Cover: Orthomosaic and plot boundaries <a name="om_can_shp" />

The following steps are used to generate plot-level canopy cover values for a georeferenced orthomosaic image and plot boundaries using geographic information.
We will first present the steps and then provide an example.

1. Create a folder and copy the orthomosaic into it
2. If using a [shapefile](#shapefile_def) or [GeoJSON](#geojson_def) file, copy those into the same folder as the orthomosaic image
3. Create another folder for the output folders and files
4. Run the docker container's `short_workflow` app specifying the name of the orthomosaic and either the name of the shapefile or geojson file, or the URL of they [BETYdb](#betydb_def) instance to query for plot boundaries

_NOTE_: the orthomosaic must be the file name without any extensions; in other words, leave off the `.tif` when specifying it on the Docker command line.

#### For example: <a name="can_shp_example" />

You can download a sample dataset of files (archived) with names corresponding to those listed here from CyVerse using the following command.
```bash
curl -X GET https://de.cyverse.org/dl/d/3C8A23C0-F77A-4598-ADC4-874EB265F9B0/scif_test_data.tar.gz > scif_test_data.tar.gz
tar xvzf scif_test_data.tar.gz -C "${PWD}/inputs"
```

In this example we're going to assume that the source image is named `orthomosaic.tif`, that we're using a shapefile named `plot_shapes.shp`, and we have an `experiment.yaml` file.

Now we can run the container mounting our source folder, destination folder, checkpoint folder, as well as indicating the name of the orthomosaic file and the name of the shapefile.
You will need to have Docker running at this point.
```bash
docker run --rm -v "${PWD}/inputs:/scif/data/odm_workflow/images" -v "${PWD}/outputs:/output" -v "${PWD}/checkpoints:/scif/data/short_workflow" agdrone/canopycover-workflow:latest run short_workflow orthomosaic plot_shapes.shp
```

Please refer to the [Docker](https://www.docker.com/) documentation for more information on running Docker containers.

_NOTE_: the above `docker` command line contains the oprthomosaic file without its extension (`orthomosaic`).

**Results:**
Upon a successful run the output will contain one sub-folder for each plot.
In the sub-folders for plots that intersected with the orthomosaic, there will be the clipped `.tif` file and two `.csv` files.
This will generate one directory per plot in the `outputs/` folder.
Each plot will contain two key outputs of interest:
1. `orthomosaic_mask.tif`
2. `canopycover.csv` with the canopy cover calculated from the mask file
   * [In the future](https://github.com/AgPipeline/issues-and-projects/issues/210), these CSV files will be aggregated into a single file for each run.
The file with "geostreams" in its name can be uploaded to TERRAREF's Geostreams database.  

### Canopy Cover: OpenDroneMap and plot boundaries <a name="opendm_can_shp" />

The following steps are used when wanting to use OpenDroneMap (ODM) to create the Orthomosaic image that's then used to create the canopy cover values.
As with the [previous example](#om_can_shp) we will be listing the steps and then providing an example.

_NOTE_: the SciF Docker image uses Docker sibling containers to run the OpenDroneMap application.
Please read our section on [Docker Sibling Containers](#docker_sibling_containers) below to learn more about this approach.

1. Create two named Docker volumes to use for processing data; one for input files and one for output files - the same volume can be used for both if desired
2. Copy the source drone images into a folder
3. If using a [shapefile](#shapefile_def) or [GeoJSON](#geojson_def) file, copy those into the same folder as the drone images
4. Copy the experiment metadata file into the same folder as the drone images
5. Copy the folder contents of the drone images folder that was just prepared onto the input named volume
6. Create another folder for the output folders and files
7. Run the docker container's `odm_workflow` app specifying  either the name of the shapefile or geojson file, or the URL of they [BETYdb](#betydb_def) instance to query for plot boundaries, and the two named volumes
8. Copy the resulting files off the output named volume to the local folder
9. Clean up the named volumes

#### For example: <a name="opendm_can_shp_example" />

You can download a sample dataset of files (archived) with names corresponding to those listed here from CyVerse using the following command.
```bash
curl -X GET https://de.cyverse.org/dl/d/7D28E988-67A2-498A-B18C-E0D884FD0C83/scif_odm_test_data.tar.gz > scif_odm_test_data.tar.gz
tar xvzf scif_test_data.tar.gz -C ${PWD}/inputs
```

In this example we're going to assume that we're using a shapefile named `plot_shapes.shp`, that we have our drone images in a folder named `${PWD}/inputs/IMG`, and additional data in the `experiment.yaml` file.

Step 1 requires creating two named Docker volumes to use when processing.
If you already have one or more empty named volumes you can skip this step.
You will need to have Docker running at this point.
```bash
docker volume create my_input
docker volume create my_output
``` 

Step 2 involves moving the drone images to the top location in the folder and then removing the empty folder:
```bash
mv "${PWD}/inputs/IMG/*" "${PWD}/inputs/"
rmdir "${PWD}/inputs/IMG"
```

In step 3 we copy the source files onto the input named volume:
```bash
docker run --rm -v "${PWD}/inputs:/sources" -v my_input:/input --entrypoint bash agdrone/canopycover-workflow:latest -c 'cp /sources/* /input/'
``` 

In step 4 we run the workflow to generate the orothomosaic image using ODM (OrthoDroneMap) and calculate plot-level canopy cover:
```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "${PWD}/inputs:/scif/data/odm_workflow/images" -v my_output:/output -v "${PWD}/checkpoints:/scif/data/odm_workflow" -e INPUT_VOLUME=my_input -e OUTPUT_VOLUME=my_output -e "INPUT_IMAGE_FOLDER=/images" -e "OUTPUT_FOLDER=/output" agdrone/canopycover-workflow:latest run odm_workflow plot_shapes.shp my_input my_output
```
and we wait until it's finished.

In step 5 we copy the results off the named output volume to our local folder:
```bash
docker run --rm -v "${PWD}/outputs:/results" -v my_output:/output --entrypoint bash agdrone/canopycover-workflow:latest -c 'cp -r /output/* /results/'
```
The results of the processing are now in the `${PWD}/outputs` folder.

Finally, in step 6 we clean up the named volumes by deleting everything on them:
```bash
docker run --rm -v my_input:/input -v my_output:/output --entrypoint bash agdrone/canopycover-workflow:latest -c 'rm -r /input/* && rm -r /output/*'
```

### Clean

Cleaning up a workflow run will delete workflow generated files and folders.
Be sure to copy the data you want to a safe place before cleaning.

By adding the `--clean` flag to the end of the command line used to execute the workflow, the artifacts of a previous run will be cleaned up.

**Example:**

The following docker command line will clean up the files generated using the [Canopy Cover: Orthomosaic and Shapefile](#om_can_shp) example above.
```bash
docker run --rm -v "${PWD}/inputs:/scif/data/odm_workflow/images" -v "${PWD}/outputs:/scif/data/soilmask" -v "${PWD}/checkpoints:/scif/data/short_workflow" agdrone/canopycover-workflow:latest run short_workflow orthomosaic plot_shapes.shp --clean
```
Notice the additional parameter at the end of the command line (--clean).

## Build the container

This section describes how the Docker container could be built.
Please refer to the [Docker](https://www.docker.com/) documentation for more information on building Docker containers.

```bash
cp jx-args.json.example jx-args.json
docker build --progress=plain -t agdrone/canopycover-workflow:latest .
```

## A Note On Docker Sibling Containers <a name="docker_sibling_containers" />

The OpenDroneMap workflow uses sibling containers.
This is a technique for having one Docker container start another Docker container to perform some work.
We plan to find a secure alternative for future releases (see [AgPipeline/issues-and-projects#240](https://github.com/AgPipeline/issues-and-projects/issues/240)), primarily because of a potential security risk that makes this approach not suitable for shared cluster computing environments (it is also a concern for containers such as websites and databases that are exposed to the internet, but that is not the case here).
You can just as safely run these workflows on your own computer as you can any trusted Docker container.
However, with sibling containers the second container requires administrator ("root") privileges - please see [Docker documentation](https://docs.docker.com/engine/security/security/) for more details.
