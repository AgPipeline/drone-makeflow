#!/usr/bin/env python3
"""Python script for converting BETYdb plot outlines to GeoJSON format
"""

import os
import argparse
import logging
import json
import requests
from osgeo import ogr

ENV_BETYDB_URL_NAME = 'BETYDB_URL'
ENV_BETYDB_KEY_NAME = 'BETYDB_KEY'


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Adds arguments to the command line parser
    Arguments:
        parser: instance of argparse.ArgumentParser to add to
    Return:
        No return is defined
    """
    parser.add_argument("--betydb_url", help='the URL of BETYdb instance to query (defaults to ' + ENV_BETYDB_URL_NAME +\
                                             ' environment variable)')
    parser.add_argument("--betydb_key", help='the BETYdb key to use when querying (defaults to ' + ENV_BETYDB_KEY_NAME +\
                                             ' environment variable)')
    parser.add_argument("output_file", help='the output file to write GeoJSON to')


def query_betydb_experiments(betydb_url: str = None, betydb_key: str = None) -> str:
    """Queries BETYdb for experiment information
    Arguments:
        betydb_url: the url to query
        betydb_key: the key to use when querying
    Return:
        The JSON containing the names of the found plots as the keys with their associated geometry in WKT format as the value
    Exceptions:
        A RuntimeError is raised if the needed BETYdb access information is not available.
        Other exceptions may be thrown by the requests.get() or requests.raise_for_status() call
    Notes:
        If either of the parameters are None or not defined (evaluates to False), the environment is queried for that value.
        It's an error to not have the url or key parameters undefined and not have environment variable equivalents defined
    """
    # Fill in missing values if we can
    if not betydb_url:
        betydb_url = os.getenv(ENV_BETYDB_URL_NAME, None)
    if not betydb_key:
        betydb_key = os.getenv(ENV_BETYDB_KEY_NAME, None)
    if not betydb_url or not betydb_key:
        raise RuntimeError("Unable to resolve BETYdb URL and key. Please ensure they're defined and try again.")

    # Make the call to get the experiment data
    url = betydb_url.rstrip('/') + '/api/v1/experiments'
    params = {'key': betydb_key, 'associations_mode': 'full_info', 'limit': 'none'}

    req = requests.get(url, params=params, validate=False)
    req.raise_for_status()
    return req.json()


def get_experiment_site_geometries(experiments_json: str) -> dict:
    """Returns all the found sites by name with their associated geometries as Well Known Text (WKT)
    Arguments:
        experiments_json: the JSON containing the experiment data retrieved from BETYdb
    Return:
        A dict with the found site names (plot names) as the keys with the WKT geometry as the values
    Exceptions:
        Raises RuntimeError if an expected key is not found in the passed in JSON
        Other exceptions can be raised by misconfigured JSON
    """
    plots = {}

    # Try loading the JSON
    all_json = json.loads(experiments_json)
    if 'data' not in all_json:
        raise RuntimeError('Missing top-level "data" key from JSON: "%s"' % experiments_json)

    # Find all the sites in all the returned experiments
    for one_exp in all_json['data']:
        if 'experiment' in one_exp and 'sites' in one_exp['experiment']:
            for one_site in one_exp['experiment']['sites']:
                if 'site' in one_site and 'geometry' in one_site['site'] and 'sitename' in one_site['site']:
                    plots[one_site['site']['sitename']] = one_site['site']['geometry']

    return plots


def sites_to_geojson(sites: dict) -> dict:
    """Converts the site geometries to GeoJSON format
    Arguments:
        sites: the dict of site names with their geometries in WKT (Well Known Text) format
    Return:
        Returns a dict with the geometries converted into GeoJSON format as a dict. The sites parameter is not altered
    Exceptions:
        Exceptions may be raised from OGR and OSR library calls
    """
    plots_geo = {}

    # Loop through converting the geometry format. We leave off CRS information since it's in WGS 84 lat-lon format
    # (which is the assumed CRS of GeoJSON)
    for site_name in sites:
        geom = ogr.CreateGeometryFromWkt(sites[site_name])
        plots_geo[site_name] = json.loads(geom.ExportToJson())

    return plots_geo


def write_geojson(out_file, geojson_plots: dict) -> None:
    """Writes out the GeoJSON to the specified output file
    Arguments:
        out_file: where to write GeoJSON to (supports .write() as a file-like object)
        geojson_plots: a dictionary of plot names and their associated geometry
    Notes:
        To reduce the memory footprint of writing the GeoJSON, the plots are written one at a time
    """
    preamble = '{"type": "FeatureCollection","name": "BETYdb Sites","features": ['
    postfix = ']}'

    out_file.write(preamble)
    for plot_name in geojson_plots:
        out_file.write()
    out_file.write(postfix)


def convert() -> None:
    """Performs the BETYdb to GeoJSON conversion
    Return:
        No return is defined
    """
    # Get the command line parameters
    parser = argparse.ArgumentParser(description="BETYdb plots to GeoJSON")
    add_arguments(parser)

    args = parser.parse_args()
    if not args.output_file:
        raise RuntimeError("An output file must be specified to receive the GeoJSON plot information")

    # Get the list of sites (plots) from the JSON returned
    experiments_json = query_betydb_experiments(args.betydb_url, args.betydb_key)
    sites = get_experiment_site_geometries(experiments_json)
    if not sites:
        raise RuntimeError("No plots were found in the data returned from BETYdb")

    # Format each of the plots to their GeoJSON equivalents
    geojson_plots = sites_to_geojson(sites)

    # Write out the GeoJSON
    with open(args.output_file,'w') as out_file:
        write_geojson(out_file, geojson_plots)


if __name__ == "__main__":
    convert()
