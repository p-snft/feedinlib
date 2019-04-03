import os
from tempfile import mkstemp
import logging
import xarray as xr
import cdsapi

logger = logging.getLogger(__name__)


def _get_cds_data(
        dataset_name='reanalysis-era5-single-levels',
        target_file=None,
        chunks=None,
        cds_client=None,
        **cds_params):
    """Download ERA5 data from the Climate Data Store (CDS)
    Requirements:
        - user account at https://cds.climate.copernicus.eu to use this function
        - cdsapi package installed (https://cds.climate.copernicus.eu/api-how-to)

    :param dataset_name: (str) short name of the dataset of the CDS. To find it, click on a dataset
    found in https://cds.climate.copernicus.eu/cdsapp#!/search?type=dataset and go under the
    ’Download data’ tab, then scroll down the page and click on ’Show API request’, the short
    name is the string on the 6th line after 'c.retrieve('
    :param target_file: (str) name of the file in which downloading the data locally
    :param chunks: (dict)
    :param cds_client: handle to CDS client (if none is provided, then it is created)
    :param cds_params: (dict) parameter to pass to the CDS request
    :return: CDS data in an xarray format
    """

    if cds_client is None:
        cds_client = cdsapi.Client()

    # Default request
    request = {
        'format': 'netcdf',
        'product_type': 'reanalysis',
        'time': [
            '00:00', '01:00', '02:00', '03:00', '04:00', '05:00',
            '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
            '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
            '18:00', '19:00', '20:00', '21:00', '22:00', '23:00'
        ],
    }

    # Add user provided cds parameters to the request dict
    request.update(cds_params)

    assert {'year', 'month', 'variable'}.issubset(request), \
        "Need to specify at least 'variable', 'year' and 'month'"

    # Send the data request to the server
    result = cds_client.retrieve(
        dataset_name,
        request,
    )

    # Create a file in a secure way if a target filename was not provided
    if target_file is None:
        fd, target_file = mkstemp(suffix='.nc')
        os.close(fd)

    logger.info(
        "Downloading request for {} variables to {}".format(len(request['variable']), target_file)
    )

    # Download the data in the target file
    result.download(target_file)

    # Extract the data from the target file
    answer = xr.open_dataset(target_file, chunks=chunks)

    # Now that the data has been extracted the file path is removed if it was not provided
    if target_file is None:
        os.unlink(target_file)

    return answer