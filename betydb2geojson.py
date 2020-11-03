#!/usr/bin/env python3
"""Python script for converting BETYdb plot outlines to GeoJSON format
"""

import os
import argparse
import json
import sys
import requests
from osgeo import ogr

ENV_BETYDB_URL_NAME = 'BETYDB_URL'


def get_arguments() -> argparse.Namespace:
    """Adds arguments to the command line parser
    Return:
        Returns the parsed arguments
    """
    parser = argparse.ArgumentParser(description="BETYdb plots to GeoJSON",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-u', '--betydb_url',
                        help='the URL of BETYdb instance to query (defaults to ' + ENV_BETYDB_URL_NAME +
                        ' environment variable)', metavar='str', type=str, default=os.getenv('BETYDB_URL'))
    parser.add_argument('-f', '--filter', help='partial or full string filter for sitename values returned',
                        metavar='str', type=str, default='')
    parser.add_argument('-o', '--outfile', help='the output file to write GeoJSON to', metavar='FILE',
                        type=argparse.FileType('wt'),
                        default='out.txt')

    args = parser.parse_args()

    if not args.betydb_url:
        parser.error('--betydb_url is required')

    return args


def query_betydb_experiments(betydb_url: str = None) -> dict:
    """Queries BETYdb for experiment information
    Arguments:
        betydb_url: the url to query
    Return:
        The dict containing the names of the found plots as the keys with their associated geometry
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
    if not betydb_url:
        raise RuntimeError("Unable to resolve BETYdb URL. Please ensure it's defined and try again.")

    # Make the call to get the experiment data
    url = betydb_url.rstrip('/') + '/api/v1/experiments'
    params = {'associations_mode': 'full_info', 'limit': 'none'}

    req = requests.get(url, params=params)
    req.raise_for_status()
    return req.json()


def get_experiment_site_geometries(experiments_json: dict, site_filter: str = None) -> dict:
    """Returns all the found sites by name with their associated geometries as Well Known Text (WKT)
    Arguments:
        experiments_json: the JSON containing the experiment data retrieved from BETYdb
        site_filter: optional filter string to apply on sitenames
    Return:
        A dict with the found site names (plot names) as the keys with the geometry as the values
    Exceptions:
        Raises RuntimeError if an expected key is not found in the passed in JSON
        Other exceptions can be raised by misconfigured JSON
    """
    plots = {}

    # Try loading the JSON
    if 'data' not in experiments_json:
        raise RuntimeError('Missing top-level "data" key from JSON: "%s"' % str(experiments_json))

    # Find all the sites in all the returned experiments
    for one_exp in experiments_json['data']:
        if 'experiment' in one_exp and 'sites' in one_exp['experiment']:
            for one_site in one_exp['experiment']['sites']:
                if 'site' in one_site and 'geometry' in one_site['site'] and 'sitename' in one_site['site']:
                    # Check if there's a filter
                    if not site_filter or site_filter in one_site['site']['sitename']:
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
    entry = {'type': 'Feature',
             'properties': {
                 'id': '',
                 'observationUnitName': ''
             },
             'geometry': None
             }

    # Loop through the plots and write them out
    separator = ''
    plot_idx = 1
    out_file.write(preamble)
    for plot_name in geojson_plots:
        entry['properties']['id'] = str(plot_idx)
        entry['properties']['observationUnitName'] = plot_name
        entry['geometry'] = geojson_plots[plot_name]
        out_file.write(separator + json.dumps(entry))
        separator = ','
        plot_idx += 1
    out_file.write(postfix)


def convert() -> None:
    """Performs the BETYdb to GeoJSON conversion
    Return:
        No return is defined
    """
    # Get the command line parameters
    args = get_arguments()

    if not args.outfile:
        raise RuntimeError("An output file must be specified to receive the GeoJSON plot information")

    # Get the list of sites (plots) from the JSON returned
    experiments_json = query_betydb_experiments(args.betydb_url)
    sites = get_experiment_site_geometries(experiments_json, args.filter)
    if not sites:
        raise RuntimeError("No plots were found in the data returned from BETYdb")

    # Format each of the plots to their GeoJSON equivalents
    geojson_plots = sites_to_geojson(sites)

    # Write out the GeoJSON
    write_geojson(args.outfile, geojson_plots)


if __name__ == "__main__":
    convert()
    sys.exit()
