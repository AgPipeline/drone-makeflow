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
We use the [Scientific Filesystem](https://sci-f.github.io/) to organize our applications, provide ease of execution, and to assist in reproducability.

* Shapefile <a name="shapefile_def" />
In this document we use the term "shapefile" to refer to all the files ending in `.shp`, `.shx`, `.dbf`, and `.prj` that have the same name.
It can be used to specify geographic information and shapes associated with plot geometries.

### Canopy Cover: Orthomosaic and plot boundaries <a name="can_om_shp" />
The following steps are used to generate plot-level canopy cover values for a georeferenced orthomosaic image and plot boundaries using geographic information.
We will first present the steps and then provide an example.

1. Create a folder and copy the orthomosaic into it
2. If using a [shapefile](#shapefile) or [GeoJSON](#geojson) file, copy those into the same folder as the orthomosaic image
3. Create another folder for the output folders and files
4. Run the docker container's `short_workflow` app specifying the name of the orthomosaic and either the name of the shapefile or geojson file, or the URL of they [BETYdb](#betydb) instance to query for plot boundaries

_NOTE_: that the orthomosaic must be the file name without any extensions; in other words, leave off the `.tif` when specifying it on the Docker command line.

**For example:**
The files mentioned in this section can be [downloaded](https://drive.google.com/file/d/1U-P4J2OcrNOkaLi6xCUblXOFet7V6raf/view?usp=sharing)

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

Step 1 involves copying the source files into a folder:
```bash
mkdir ~/inputs
cp orthomosaic.tif ~/inputs
cp plot_shapes.* ~/inputs
cp experiment.yaml ~/inputs
```

In step 2 we create an folder to hold the output of our processing:
```bash
mkdir ~/output
``` 

Finally we run the container mounting our source and destination folders, as well as indicating the name of the orthomosaic file and the name of the shapefile.
```bash
docker run --rm -v ~/inputs:/scif/data/odm/images -v ~/outputs:/output agdrone/canopycover-workflow:latest run short_workflow orthomosaic plot_shapes.shp
```
Please refer to the [Docker](https://www.docker.com/) documentation for more information on running Docker containers.

_NOTE_: the above `docker` command line contains the oprthomosaic file without its extension (`orthomosaic`).

**Results:**
Upon a successful run the output will contain one sub-folder for each plot.
In the sub-folders for plots that intersected with the orthomosaic, there will be the clipped `.tif` file and two `.csv` files.
The CSV files both contain much of the same information.
The file with "geostreams" in its name can be uploaded to TERRAREF's Geostreams database.  

### Clean
By executing the [scif](#scif) app named `clean` it's possible to clean up the output folder and other generated files.
It's recommended, but not necessary, to run the clean app between processing runs by either running this command or through other means.

**Example:**

This docker command line will clean up the output files generated using the [Canopy Cover: Orthomosaic and Shapefile](#can_om_shp) example above.
```bash
docker run --rm -v ~/inputs:/scif/data/odm/images -v ~/outputs:/scif/data/soilmask agdrone/canopycover-shape-workflow:latest run clean
```

## Build the container
This section describes how the Docker container could be built.
Please refer to the [Docker](https://www.docker.com/) documentation for more information on building Docker containers.

```bash
cp jx-args.json.example jx-args.json
docker build --progress=plain -t agdrone/canopycover-shape-workflow:latest .
```
