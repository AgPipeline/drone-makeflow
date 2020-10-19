# Makeflow for Drone Processing Pipeline

The [Scientific Filesystem](https://sci-f.github.io/) is used as to provide the entry points for the different tasks available (known as "apps" with the Scientific Filesystem).
These apps are used to create workflows.

## Table of contents
- [Terminology used](#terminology)
- [Running the apps](#run_apps)
    - [Prerequisites](#prerequisites)
    - [Configuration JSON file](#config_json)
    - [Generating GeoJSON plot geometries](#geojson_plots)
        - [BETYdb to GeoJson](#betydb_geojson)
        - [Shapefile to GeoJson](#shapefile_geojson)
    - [Soilmask images](#soilmask)
    - [Plotclip images](#plotclip)
    - [Find files and write JSON](#files2json)
    - [Canopy Cover calculation](#canopycover)
    - [Merge CSV files](#merge_csv)
    - [Clean](#workflow_clean)
- [Build The Container](#build)
- [A Note On Docker Sibling Containers](#docker_sibling_containers)
- [Acceptance Testing](#acceptance_testing)
    - [PyLint and PyTest](#pylint_pytest)
    - [shellcheck and shfmt](#shellcheck_shfmt)
    - [Docker Testing](#test_docker)

## Terminology used <a name="terminology" />

Here are the definition of some of the terms we use with links to additional information

* apps <a name="def_apps" />
This term refers to the entry points in a (Scientific Filesystem)[#def_scif] solution.

* BETYdb <a name="def_betydb" />
[BETYdb](https://www.betydb.org/) is a database that can be used to store trait and yield data.
It can be used in the processing pipeline as a source of plot geometry for clipping.

* GeoJSON <a name="def_geojson" />
[GeoJSON](https://datatracker.ietf.org/doc/rfc7946/) is a JSON format for specifying geographic shape information.
This is the default format for specifying plot geometries.

* Makeflow <a name="def_makeflow" />
We use [Makeflow](https://cctools.readthedocs.io/en/latest/man_pages/makeflow/) to run the apps defined with Scientific Filesystem.
This tool enables error recovery, automatic retries, distributed computing, and many other features.

* Scientific Filesystem <a name="def_scif" />
We use the [Scientific Filesystem](https://sci-f.github.io/) to organize our applications, provide ease of execution, and to assist in reproducibility.

* Shapefile <a name="def_shapefile" />
In this document we use the term "shapefile" to refer to all the files ending in `.shp`, `.shx`, `.dbf`, and `.prj` that have the same name.
It can be used to specify geographic information and shapes associated with plot geometries.

## Running the apps <a name="run_apps" />

This section contains information on running the different apps in existing Docker workflow container.
By tying these different applications together, flexible workflows can be created and distributed.

To determine what apps are available, try the following command:
```bash
docker run --rm agdrone/canopycover-workflow:latest apps
```
The different components of the command line are:
- `docker run --rm` tells Docker to run an image and remove the resulting container automatically after the run
- `agdrone/canopycover-workflow:latest` is the Docker image to run
- `apps` the command that lists the available apps

### Prerequisites <a name="prerequisites" />

- Docker needs to be installed to run the apps. How to [get Docker](https://docs.docker.com/get-docker/)
- Create an `inputs` folder in the current working directory (or other folder of your choice) to hold input files
```bash
mkdir -p "${PWD}/inputs"
```
- Create an `outputs` folder in the current working directory (or other folder of your choice) to hold the results
```bash
mkdir -p "${PWD}/outputs"
```
- Create an `checkpoints` folder.
The checkpoints folder will contain the generated workflow checkpoint data allowing easy error recovery and helps prevent re-running an already completed workflow.
Removing the workflow checkpoint files will enable a complete re-run of the workflow
```bash
mkdir -p "${PWD}/checkpoints"
``` 

### Configuration JSON file <a name="config_json" />

Most of the apps described in this document need additional information to perform; such as the source image name.
This information is provided through a JSON file that is made available to a running container.

Each of the apps described provide the keys they expect to find, along with a description of the associated value.

We recommend naming the configuration JSON files something that is related to the intent; such as the workflow that they are a part of.

### Generating GeoJSON plot geometries <a name="geojson_plots" />

Plot geometries are needed when clipping source files to where they intersect the plots.
The plot geometries need to be in [GeoJSON](https://tools.ietf.org/html/rfc7946) format.
Apps are provided to convert shapefiles and BETYdb URLs to the GeoJSON format.

#### BETYdb to GeoJson <a name="betydb_geojson" />

This app retrieves the plots from a BETYdb instance and saves them to a file in the GeoJSON format.

**JSON configuration** \
There are two JSON key/value pairs needed by this app.
- BETYDB_URL: the URL of the BETYdb instance to query for plot geometries
- PLOT_GEOMETRY_FILE: the path to write the plot geometry file to, including the file name

For example:
```json
{
  "BETYDB_URL": "https://terraref.ncsa.illinois.edu/bety",
  "PLOT_GEOMETRY_FILE": "/output/plots.geojson"
}
```

**Sample command line** \
```bash
docker run --rm -v ${PWD}/outputs:/output -v ${PWD}/my-jx-args.json:/scif/apps/src/jx-args.json agdrone/canopycover-workflow:latest run betydb2geojson
```

The different components of the command line are:
- `docker run --rm` tells Docker to run an image and remove the resulting container automatically after the run (`--rm`)
- `-v ${PWD}/outputs:/output` mounts the [previously created](#prerequisites) outputs folder to the `/output` location on the running image
- `-v ${PWD}/my-jx-args.json:/scif/apps/src/jx-args.json` mounts the JSON configuration file so that it's available to the app
- `agdrone/canopycover-workflow:latest` is the Docker image to run
- `run betydb2geojson` the command that runs the app

Please notice that the `/output` folder on the command line corresponds with the `PLOT_GEOMETRY_FILE` starting path value in the configuration JSON

#### Shapefile to GeoJson <a name="shapefile_geojson" />

This app loads plot geometries from a shapefile and saves them to a file in the GeoJSON format.

**JSON configuration** \
There are two JSON key/value pairs needed by this app.
- PLOT_SHAPEFILE: the path to the shapefile to load and save as GeoJSON
- PLOT_GEOMETRY_FILE: the path to write the plot geometry file to, including the file name

For example:
```json
{
  "PLOT_SHAPEFILE": "/input/plot_shapes.shp",
  "PLOT_GEOMETRY_FILE": "/output/plots.geojson"
}
```

**Sample command line** \
```bash
docker run --rm -v ${PWD}/inputs:/input -v ${PWD}/outputs:/output -v ${PWD}/my-jx-args.json:/scif/apps/src/jx-args.json agdrone/canopycover-workflow:latest run shp2geojson
```

The different components of the command line are:
- `docker run --rm` tells Docker to run an image and remove the resulting container automatically after the run (`--rm`)
- `-v ${PWD}/inputs:/input` mounts the [previously created](#prerequisites) inputs folder to the `/input` location on the running image
- `-v ${PWD}/outputs:/output` mounts the [previously created](#prerequisites) outputs folder to the `/output` location on the running image
- `-v ${PWD}/my-jx-args.json:/scif/apps/src/jx-args.json` mounts the JSON configuration file so that it's available to the app
- `agdrone/canopycover-workflow:latest` is the Docker image to run
- `run shp2geojson` the command that runs the app

Please notice the following:
- the `/input` folder on the command line corresponds with the `PLOT_SHAPEFILE` starting path value in the configuration JSON; this is where the app expects to find the shapefile to load and convert
- the `/output` folder on the command line corresponds with the `PLOT_GEOMETRY_FILE` starting path value in the configuration JSON

### Soilmask images <a name="soilmask" />

This app masks out soil from an image.

**JSON configuration** \
There are JSON key/value pairs for this app
- SOILMASK_SOURCE_FILE: the path to the image to mask the soil from
- SOILMASK_MASK_FILE: the name of the mask file to write. Will be written to the path defined in SOILMASK_WORKING_FOLDER if a path is not specified
- SOILMASK_WORKING_FOLDER: the path to where the results of processing should be placed 
- SOILMASK_OPTIONS: any options to be passed to the script

The following JSON example would have the soilmask app write the mask to a file named `orthomosaic_masked.tif` in the `/output/` folder of the running Docker image:
```json
{
  "SOILMASK_SOURCE_FILE": "/input/orthomosaic.tif",
  "SOILMASK_MASK_FILE": "orthomosaic_masked.tif",
  "SOILMASK_WORKING_FOLDER": "/output",
  "SOILMASK_OPTIONS": ""
}
```

The following options are available to be specified on the SOILMASK_OPTIONS JSON entry:
- `--metadata METADATA` this option indicates a metadata YAML or JSON file to use when processing 
- `--help` displays the soilmask help information without any file processing

**Sample command line** \
```bash
docker run --rm -v ${PWD}/test/inputs:/input -v ${PWD}/test/output:/output -v ${PWD}/chris-jx-args.json:/scif/apps/src/jx-args.json agdrone/canopycover-workflow:latest run soilmask
```

The different components of the command line are:
- `docker run --rm` tells Docker to run an image and remove the resulting container automatically after the run (`--rm`)
- `-v ${PWD}/inputs:/input` mounts the [previously created](#prerequisites) inputs folder to the `/input` location on the running image
- `-v ${PWD}/outputs:/output` mounts the [previously created](#prerequisites) outputs folder to the `/output` location on the running image
- `-v ${PWD}/my-jx-args.json:/scif/apps/src/jx-args.json` mounts the JSON configuration file so that it's available to the app
- `agdrone/canopycover-workflow:latest` is the Docker image to run
- `run soilmask` the command that runs the app

Please notice the following:
- the `/input` folder on the command line corresponds with the `SOILMASK_SOURCE_FILE` path value in the configuration JSON; this is where the app expects to find the source image
- the `/output` folder on the command line corresponds with the `SOILMASK_WORKING_FOLDER` path value in the configuration JSON; this is where the masked image is stored

### Plotclip images <a name="plotclip" />

This app clips georeferenced images to plot boundaries.

**JSON configuration** \
There are JSON key/value pairs for this app
- PLOTCLIP_SOURCE_FILE: the path to the image to clip
- PLOTCLIP_PLOTGEOMETRY_FILE: the path to the GeoJSON file containing the plot boundaries; see also [BETYdb to GeoJson](#betydb_geojson)and [Shapefile to GeoJson](#shapefile_geojson)
- PLOTCLIP_WORKING_FOLDER: the path to where the results of processing should be placed; each plot clip is placed in a folder corresponding to the plot name
- PLOTCLIP_OPTIONS: any options to be passed to the script

The following JSON example would have the plot clips written to the `/output/` folder of the running Docker image:
```json
{
  "PLOTCLIP_SOURCE_FILE": "/input/orthomosaic_mask.tif",
  "PLOTCLIP_PLOTGEOMETRY_FILE": "/input/plots.geojson",
  "PLOTCLIP_WORKING_FOLDER": "/output",
  "PLOTCLIP_OPTIONS": ""
}
```

The following options are available to be specified on the PLOTCLIP_OPTIONS JSON entry:
- `--metadata METADATA` this option indicates a metadata YAML or JSON file to use when processing 
- `--keep_empty_folders` specifying this option will create a folder with the plot name even if the plot doesn't intersect the image
- `--plot_column PLOT_COLUMN` specifies the column name ("properties" sub-key with GeoJSON) to use as the plot name 
- `--help` displays the plotclip help information without any file processing

**Sample command line** \
```bash
docker run --rm -v ${PWD}/test/inputs:/input -v ${PWD}/test/output:/output -v ${PWD}/chris-jx-args.json:/scif/apps/src/jx-args.json agdrone/canopycover-workflow:latest run plotclip
```

The different components of the command line are:
- `docker run --rm` tells Docker to run an image and remove the resulting container automatically after the run (`--rm`)
- `-v ${PWD}/inputs:/input` mounts the [previously created](#prerequisites) inputs folder to the `/input` location on the running image
- `-v ${PWD}/outputs:/output` mounts the [previously created](#prerequisites) outputs folder to the `/output` location on the running image
- `-v ${PWD}/my-jx-args.json:/scif/apps/src/jx-args.json` mounts the JSON configuration file so that it's available to the app
- `agdrone/canopycover-workflow:latest` is the Docker image to run
- `run plotclip` the command that runs the app

Please notice the following:
- the `/input` folder on the command line corresponds with the `PLOTCLIP_SOURCE_FILE` path value in the configuration JSON; this is where the app expects to find the source image
- the `/output` folder on the command line corresponds with the `PLOTCLIP_WORKING_FOLDER` path value in the configuration JSON; this is where the plot image clips are saved

### Find files and write JSON <a name="files2json" />

This app locates files with a specific name and writes a JSON file that can then be used to process those files.
Makeflow is a deterministic scheduler, meaning that when it's run it needs to "know" everything about a job; such as which files are input.
Apps like [Plotclip](#plotclip) are non-deterministic in that there isn't a way ahead of time of knowing which plots intersect an image (unless complete plot coverage is guaranteed, which doesn't always happen).
Even in cases where the output of a step is deterministic, it may still be handy to use this app to build up a JSON file.

The source top-level folder is shallowly searched, only immediate sub-folders are searched, and the top folder is ignored.

**JSON configuration** \
There are JSON key/value pairs for this app
- FILES2JSON_SEARCH_NAME: the complete name of the file to find
- FILES2JSON_SEARCH_FOLDER: the starting path to begin searching in
- FILES2JSON_JSON_FILE: the path to the found file's JSON is written to

The following JSON example would have the JSON file written to the `/output/files.json` file of the running Docker image:
```json
{
  "FILES2JSON_SEARCH_NAME": "orthomosaic_mask.tif",
  "FILES2JSON_SEARCH_FOLDER": "/input",
  "FILES2JSON_JSON_FILE": "/output/files.json"
}
```

**Sample command line** \
```bash
docker run --rm -v ${PWD}/inputs:/input -v ${PWD}/output:/output -v ${PWD}/my-jx-args.json:/scif/apps/src/jx-args.json agdrone/canopycover-workflow:latest run find_files2json
```

The different components of the command line are:
- `docker run --rm` tells Docker to run an image and remove the resulting container automatically after the run (`--rm`)
- `-v ${PWD}/inputs:/input` mounts the [previously created](#prerequisites) inputs folder to the `/input` location on the running image
- `-v ${PWD}/outputs:/output` mounts the [previously created](#prerequisites) outputs folder to the `/output` location on the running image
- `-v ${PWD}/my-jx-args.json:/scif/apps/src/jx-args.json` mounts the JSON configuration file so that it's available to the app
- `agdrone/canopycover-workflow:latest` is the Docker image to run
- `run find_files2json` the command that runs the app

Please notice the following:
- the `/input` folder on the command line corresponds with the `FILES2JSON_SEARCH_FOLDER` path value in the configuration JSON; this is where the app will start its search
- the `/output` folder on the command line is included as part of the `FILES2JSON_JSON_FILE` path value in the configuration JSON; this is the folder where the found file's JSON are saved

### Canopy Cover calculation <a name="canopycover" />

This app calculates the canopy cover of [soilmasked](#soilmask) images and writes the CSV files next to the source image (in the same folder).

**JSON configuration** \
There are JSON key/value pairs for this app
- CANOPYCOVER_OPTIONS: any options to be passed to the script

The following JSON example shows how to define runtime options when running this app:
```json
{
  "CANOPYCOVER_OPTIONS": ""
}
```

The following options are available to be specified on the CANOPYCOVER_OPTIONS JSON entry:
- `--metadata METADATA` this option indicates a metadata YAML or JSON file to use when processing 
- `--help` displays the canopy cover help information without any file processing. This is useful for finding options which affect the output

**Sample command line** \
```bash
docker run --rm -v ${PWD}/test/inputs:/input -v ${PWD}/test/output:/output -v ${PWD}/chris-jx-args.json:/scif/apps/src/jx-args.json -v ${PWD}/canopy_cover_files.json:/scif/apps/src/canopy_cover_files.json agdrone/canopycover-workflow:latest run canopycover
```

The different components of the command line are:
- `docker run --rm` tells Docker to run an image and remove the resulting container automatically after the run (`--rm`)
- `-v ${PWD}/inputs:/input` mounts the [previously created](#prerequisites) inputs folder to the `/input` location on the running image
- `-v ${PWD}/my-jx-args.json:/scif/apps/src/jx-args.json` mounts the JSON configuration file so that it's available to the app
- `-v ${PWD}/canopy_cover_files.json:/scif/apps/src/canopy_cover_files.json` mounts the JSON file containing information on the files to process so that it's available to the app; also see [Find files and write JSON](#files2json)
- `agdrone/canopycover-workflow:latest` is the Docker image to run
- `run canopycover` the command that runs the app

Please notice the following:
- the `/input` folder on the command line corresponds to where the files to be processed are expected to be found and where the CSV files are written to

### Merge CSV files <a name="merge_csv" />

This app recursively merges same-named CSV files to a destination folder.
If the folder contains multiple, differently named, CSV files, there will be one resulting merged CSV file for each unique CSV file name.
All the source CSV files are left intact.

**JSON configuration** \
There are JSON key/value pairs for this app
- MERGECSV_SOURCE: the path to the top-level folder containing CSV files to merge
- MERGECSV_TARGET: the path where the merged CSV file is written
- MERGECSV_OPTIONS: any options to be passed to the script

For example:
```json
{
  "MERGECSV_SOURCE": "/input",
  "MERGECSV_TARGET": "/output",
  "MERGECSV_OPTIONS": ""
}
```

The following options are available to be specified on the MERGECSV_OPTIONS JSON entry:
- `--no_header` this option indicates that the source CSV files do not have header lines
- `--header_count <value>` indicates the number of header lines to expect in the CSV files; defaults to 1 header line
- `--filter <file name filter>` one or more comma-separated filters of files to process; files not matching a filter aren't processed
- `--ignore <file name filter>` one or more comma-separated filters of files to skip; files matching a filter are ignored
- `--help` displays the help information without any file processing

By combining filtering options and header options, it's possible to precisely target the CSV files to process.

The filters work by matching up the file name found on disk with the names specified with the filter to determine if a file should be processed.
Only the body and extension of a file name is compared, the path to the file is ignored when filtering.

**Sample command line** \
```bash
docker run --rm -v ${PWD}/inputs:/input -v ${PWD}/outputs:/output -v ${PWD}/my-jx-args.json:/scif/apps/src/jx-args.json agdrone/canopycover-workflow:latest run merge_csv
```

The different components of the command line are:
- `docker run --rm` tells Docker to run an image and remove the resulting container automatically after the run (`--rm`)
- `-v ${PWD}/inputs:/input` mounts the [previously created](#prerequisites) inputs folder to the `/input` location on the running image
- `-v ${PWD}/outputs:/output` mounts the [previously created](#prerequisites) outputs folder to the `/output` location on the running image
- `-v ${PWD}/my-jx-args.json:/scif/apps/src/jx-args.json` mounts the JSON configuration file so that it's available to the app
- `agdrone/canopycover-workflow:latest` is the Docker image to run
- `run merge_csv` the command that runs the app

Please notice the following:
- the `/input` folder on the command line corresponds with the `MERGECSV_SOURCE` path value in the configuration JSON; this is where the app expects to find the CSV files to merge
- the `/output` folder on the command line corresponds with the `MERGECSV_TARGET` path value in the configuration JSON; this is where the merged CSV files are stored

### Clean runs <a name="workflow_clean" />

Cleaning up a workflow run will delete workflow generated files and folders.
Be sure to copy the data you want to a safe place before cleaning.

By adding the `--clean` flag to the end of the command line used to execute the workflow, the artifacts of a previous run will be cleaned up.

It's recommended, but not necessary, to run the clean app between processing runs by either running this command or through other means.

**Example:**

The following docker command line will clean up the files generated using the [Canopy Cover: Orthomosaic and Shapefile](#om_can_shp) example above.
```bash
docker run --rm -v ${PWD}/outputs:/output -v ${PWD}/my-jx-args.json:/scif/apps/src/jx-args.json agdrone/canopycover-workflow:latest run betydb2geojson --clean
```
Notice the additional parameter at the end of the command line (--clean).

## Build The Container <a name="build" />

This section describes how the Docker container could be built.
Please refer to the [Docker](https://www.docker.com/) documentation for more information on building Docker containers.

```bash
cp jx-args.json.example jx-args.json
docker build --progress=plain -t agdrone/canopycover-workflow:latest .
```

## Monitoring the Workflow <a name="monitoring" />

To monitor the running workflows, you will need to be using the checkpoints folder as described in the [Prerequisites](#prerequisites) section.

[Makeflow](#def_makeflow) has [monitoring tools](https://cctools.readthedocs.io/en/latest/man_pages/) available that can be used to follow the progress of the workflows.
The [makeflow_monitor](https://cctools.readthedocs.io/en/latest/man_pages/makeflow_monitor/) tool can be a good starting point.

## A Note On Docker Sibling Containers <a name="docker_sibling_containers" />

The OpenDroneMap workflow uses sibling containers.
This is a technique for having one Docker container start another Docker container to perform some work.
We plan to find a secure alternative for future releases (see [AgPipeline/issues-and-projects#240](https://github.com/AgPipeline/issues-and-projects/issues/240)), primarily because of a potential security risk that makes this approach not suitable for shared cluster computing environments (it is also a concern for containers such as websites and databases that are exposed to the internet, but that is not the case here).
You can just as safely run these workflows on your own computer as you can any trusted Docker container.
However, with sibling containers the second container requires administrator ("root") privileges - please see [Docker documentation](https://docs.docker.com/engine/security/security/) for more details.

## Acceptance Testing <a name="acceptance_testing" />

There are automated test suites that are run via [GitHub Actions](https://docs.github.com/en/actions).
In this section we provide details on these tests so that they can be run locally as well.

These tests are run when a [Pull Request](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests) or [push](https://docs.github.com/en/github/using-git/pushing-commits-to-a-remote-repository) occurs on the `develop` or `master` branches.
There may be other instances when these tests are automatically run, but these are considered the mandatory events and branches.

### PyLint and PyTest <a name="pylint_pytest" />

These tests are run against any Python scripts that are in the repository.

[PyLint](https://www.pylint.org/) is used to both check that Python code conforms to the recommended coding style, and checks for syntax errors.
The default behavior of PyLint is modified by the `pylint.rc` file in the [Organization-info](https://github.com/AgPipeline/Organization-info) repository.
Please also refer to our [Coding Standards](https://github.com/AgPipeline/Organization-info#python) for information on how we use [pylint](https://www.pylint.org/).

The following command can be used to fetch the `pylint.rc` file:
```bash
wget https://raw.githubusercontent.com/AgPipeline/Organization-info/master/pylint.rc
```

Assuming the `pylint.rc` file is in the current folder, the following command can be used against the `betydb2geojson.py` file:
```bash
# Assumes Python3.7+ is default Python version
python -m pylint --rcfile ./pylint.rc betydb2geojson.py
```

[PyTest](https://docs.pytest.org/en/stable/) is used to run Unit and Integration Testing.
The following command can be used to run the test suite:
```bash
# Assumes Python3.7+ is default Python version
python -m pytest -rpP
```

If [pytest-cov](https://pytest-cov.readthedocs.io/en/latest/) is installed, it can be used to generate a code coverage report as part of running PyTest.
The code coverage report shows how much of the code has been tested; it doesn't indicate **how well** that code has been tested.
The modified PyTest command line including coverage is:
```bash
# Assumes Python3.7+ is default Python version
python -m pytest --cov=. -rpP
```

### shellcheck and shfmt <a name="shellcheck_shfmt" />

These tests are run against shell scripts within the repository.
It's expected that shell scripts will conform to these tools (no reported issues).

[shellcheck](https://www.shellcheck.net/) is used to enforce modern script coding.
The following command runs `shellcheck` against the "prep-canopy-cover.sh" bash shell script:
```bash
shellcheck prep-canopy-cover.sh
``` 

[shfmt](https://github.com/mvdan/sh#shfmt) is used to ensure scripts conform to Google's shell script [style guide](https://google.github.io/styleguide/shellguide.html).
The following command runs `shfmt` against the "prep-canopy-cover.sh" bash shell script:
```bash
shfmt -i 2 -ci -w prep-canopy-cover.sh
``` 

### Docker Testing <a name="test_docker" />

The Docker testing Workflow replicate the examples in this document to ensure they continue to work.
