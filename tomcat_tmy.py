import numpy as np
import pandas as pd
import pvlib
from scipy.interpolate import interp1d
import csv


def sky_temp(dew_point, clearness_index, ambient_temperature):
    '''
    Calculate the sky temperature in Kelvins according to the model from

    Slauch, Ian, Michael Deceglie, Timothy Silverman, and Vivian E. Ferry
    "Spectrally-selective mirrors with combined optical and thermal benefit
    for photovoltaic module thermal management." ACS Photonics (2018)

    Paramaters
    ----------
    input temperatures in celcius

    clearness index = GHI/Extraterrestrial horizontal

    '''
    a = [123.1415, 11.3444, 4.2073, 0.4447]  # coeffeciencts fit in Golden

    # Tetens equation for vapor pressure
    Pw = 6.1078 * np.exp((17.27 * dew_point) / (dew_point + 237.3))

    TskyEst = a[0] + a[1] * np.log(Pw) - a[2] * clearness_index + \
        a[3] * (ambient_temperature + 273.15)

    return TskyEst


def ground_temp(ambient_temperature, GHI):
    '''
    Calculate the ground temperature in Kelvins according to the model from

    Slauch, Ian, Michael Deceglie, Timothy Silverman, and Vivian E. Ferry
    "Spectrally-selective mirrors with combined optical and thermal benefit
    for photovoltaic module thermal management." ACS Photonics (2018)

    Paramaters
    ----------
    ambient_temperature is in celcius
    GHI is in w/m^2
    '''
    ground_temperature = ambient_temperature - 1.362 + 1.287e-2 * GHI + 273.15

    return ground_temperature


def projected_sun_elevation(elevation, azimuth):
    '''
    Calculates sun projected elevation in radians from
    sun elevation and azimuth, both in radians
    '''
    projected = np.clip(np.arctan2(
        np.tan(elevation), -np.cos(azimuth)), 0., np.pi)
    return projected


def hemi_ave(theta, y, lower_limit=0, upper_limit=90, step=1):
    '''
    Numerical hemispherical avarage as for a function y(theta) where theta is
    the zenith in degrees.
    '''

    y_interp = interp1d(theta, y, fill_value='extrapolate')

    theta_grid = np.arange(lower_limit, upper_limit + step / 10.0, step)
    y_grid = y_interp(theta_grid)

    theta_grid = np.deg2rad(theta_grid)

    ave = np.trapz(y_grid * np.sin(theta_grid), theta_grid) / np.trapz(np.sin(theta_grid), theta_grid)

    return ave


def generate_input(tmy_file, optics_file, array_tilt=40.0, array_azimuth=180.0, out_file=None):
    '''
    Generates TOMCAT input based on TMY and optical data

    Paramaters
    ----------
    tmy_file: str specifying the TMY file
    optics_file: str specifying the optics file
    array_tilt: The tilt of the PV array in degrees. 0 is horizontal
    array_azimuth: The azimuth of the PV array in degrees. 0 is north
    out_file (optional): str specifying output file. If None, no file
        is written

    Returns
    -------
    Pandas dataframe of finitie element model output
    '''

    # Parse the TMY file
    with open(tmy_file, newline='') as f:
        reader = csv.reader(f)
        tmy_meta = next(reader)

    lat = float(tmy_meta[4])
    lon = float(tmy_meta[5])
    elevation = float(tmy_meta[6])
    tz = float(tmy_meta[3])

    tmy = pd.read_csv(tmy_file, header=1)

    # presume everything happened in 2017, a non leap year
    tmy.index = pd.DatetimeIndex(
        start='01/01/2017 01:00:00', end='01/01/2018 00:00:00', freq='H')

    # Convert to UTC
    tmy.index = tmy.index - pd.Timedelta(tz, unit='h')
    tmy.index = tmy.index.tz_localize('UTC')

    # Calculate sun position
    sun = pvlib.solarposition.get_solarposition(tmy.index, lat, lon, altitude=elevation)
    aoi = pvlib.irradiance.aoi(array_tilt, array_azimuth, sun.apparent_zenith, sun.azimuth)

    # Calculate poai components
    beam = tmy['DNI (W/m^2)'] * np.cos(np.pi / 180.0 * aoi)
    beam = np.clip(beam, 0, None)
    sky = pvlib.irradiance.isotropic(array_tilt, tmy['DHI (W/m^2)'])
    poai = beam + sky

    # Calculate clearness index
    clearness_index = tmy['GHI (W/m^2)'] / tmy['ETR (W/m^2)']
    clearness_index = clearness_index.fillna(1)

    # Parse the optics file
    optics = pd.read_csv(optics_file)

    # Calculate values for diffuse irradiance
    diffuse = {
        'cell_abs_W/m2': hemi_ave(optics['angle'], optics['cell_abs_W/m2']),
        'encapsulant_abs_W/m2': hemi_ave(optics['angle'], optics['encapsulant_abs_W/m2']),
        'glass_abs_W/m2': hemi_ave(optics['angle'], optics['glass_abs_W/m2']),
        'current_derate': hemi_ave(optics['angle'], optics['current_derate'])
    }

    # Interpolations for each column in optics
    # Note the removal of cosine factor
    interp_kwargs = {'fill_value': 'extrapolate', 'kind': 'linear'}
    glass_abs = interp1d(optics['angle'], optics['glass_abs_W/m2'] / np.cos(np.deg2rad(optics['angle'])), **interp_kwargs)
    encapsulant_abs = interp1d(optics['angle'], optics['encapsulant_abs_W/m2'] / np.cos(np.deg2rad(optics['angle'])), **interp_kwargs)
    cell_abs = interp1d(optics['angle'], optics['cell_abs_W/m2'] / np.cos(np.deg2rad(optics['angle'])), **interp_kwargs)
    current_derate = interp1d(optics['angle'], optics['current_derate'] / np.cos(np.deg2rad(optics['angle'])), **interp_kwargs)

    # build the output
    out = pd.DataFrame()

    out['temp'] = tmy['Dry-bulb (C)'] + 273.15
    out['temp_sky'] = sky_temp(tmy['Dew-point (C)'], clearness_index, tmy['Dry-bulb (C)'])
    out['temp_ground'] = ground_temp(tmy['Dry-bulb (C)'], tmy['GHI (W/m^2)'])
    out['poai'] = poai
    out['dni'] = tmy['DNI (W/m^2)']
    out['wind_speed'] = tmy['Wspd (m/s)']
    out['elevation_projected'] = projected_sun_elevation(sun['apparent_elevation'] * np.pi / 180.0, sun['azimuth'] * np.pi / 180.0)

    out['abs_glass'] = glass_abs(aoi) * beam / 1000.0 + diffuse['glass_abs_W/m2'] * sky / 1000.0
    out['abs_cell'] = cell_abs(aoi) * beam / 1000.0 + diffuse['cell_abs_W/m2'] * sky / 1000.0
    out['abs_encapsulant'] = encapsulant_abs(aoi) * beam / 1000.0 + diffuse['encapsulant_abs_W/m2'] * sky / 1000.0
    out['current_factor'] = current_derate(aoi) * beam / poai + diffuse['current_derate'] * sky / poai
    out['current_factor'] = out['current_factor'].fillna(0.0)

    out['elapsed'] = (out.index - out.index[0]).astype(np.timedelta64()) / 1e9
    out.set_index('elapsed', inplace=True)

    if out_file:
        if type(out_file) is not str:
            raise TypeError(
                'out_file must be a string specifying the desired output filename')
        out.to_csv(out_file)

    return out
