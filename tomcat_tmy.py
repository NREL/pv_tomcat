import numpy as np
import pandas as pd
import pvlib
from scipy.interpolate import interp1d
from scipy.integrate import trapz
import csv
import warnings


def tetens(dew_point):
    'Calculate vapor pressure in Pa based on dew_point in Celsius'

    def tetens_single(dew_point):
        if dew_point >= 0:
            Pw = 610.78 * np.exp((17.27 * dew_point) / (dew_point + 237.3))
        elif dew_point < 0:
            Pw = 610.78 * np.exp((21.875 * dew_point) / (dew_point + 265.5))

        return Pw

    f = np.vectorize(tetens_single)
    Pw = f(dew_point)

    return Pw


def sky_temp(dew_point, clearness_index, ambient_temperature):
    '''
    Calculate the sky temperature in Kelvins according to the model from

    Slauch, Ian, Michael Deceglie, Timothy Silverman, and Vivian E. Ferry
    "Spectrally-selective mirrors with combined optical and thermal benefit
    for photovoltaic module thermal management." ACS Photonics (2018)

    Parameters
    ----------
    input temperatures in Celsius

    clearness index = GHI/Extraterrestrial horizontal

    '''

    a = [76.56, 10.59, 4.557, 0.4437]  # coefficients fit in Golden

    # Tetens equation for vapor pressure
    Pw = tetens(dew_point)

    TskyEst = a[0] + a[1] * np.log(Pw) - a[2] * clearness_index + \
        a[3] * (ambient_temperature + 273.15)

    return TskyEst


def ground_temp(ambient_temperature, GHI):
    '''
    Calculate the ground temperature in Kelvins according to the model from

    Slauch, Ian, Michael Deceglie, Timothy Silverman, and Vivian E. Ferry
    "Spectrally-selective mirrors with combined optical and thermal benefit
    for photovoltaic module thermal management." ACS Photonics (2018)

    Parameters
    ----------
    ambient_temperature is in Celsius
    GHI is in w/m^2
    '''
    ground_temperature = ambient_temperature - 1.362 + 1.287e-2 * GHI + 273.15

    return ground_temperature


def projected_sun_elevation(elevation, azimuth, array_azimuth):
    '''
    Calculates the sun's elevation angle, projected into the plane that
    contains the 'up' vector and the module's surface normal. This function
    assumes a fixed-tilt array. This is used by the finite element model to
    calculate the position of the array's own shadow for purposes of the
    ground temperature pattern. Uses sun elevation, azimuth, and the array's
    azimuth, all in radians.
    '''
    projected = np.clip(
        np.arctan2(
            np.tan(elevation), -np.cos(azimuth + (np.pi - array_azimuth))
        ),
        0., np.pi
    )
    return projected


def hemi_ave(theta, y, lower_limit=0, upper_limit=90, step=1):
    '''
    Numerical hemispherical average as for a function y(theta) where theta is
    the zenith in degrees.
    '''

    y_interp = interp1d(theta, y, fill_value='extrapolate')

    theta_grid = np.arange(lower_limit, upper_limit + step / 10.0, step)
    y_grid = y_interp(theta_grid)

    theta_grid = np.deg2rad(theta_grid)

    ave = np.trapz(y_grid * np.sin(theta_grid), theta_grid) / np.trapz(np.sin(theta_grid), theta_grid)

    return ave


def generate_input(tmy_file, optics_file, array_tilt=40.0, array_azimuth=180.0, out_file_time_series='TOMCAT_input.csv', out_file_tilt='TOMCAT_tilt.txt'):
    '''
    Generates TOMCAT input based on TMY and optical data

    Parameters
    ----------
    tmy_file: str specifying a TMY3 file
    optics_file: str specifying the optics file
    array_tilt: The tilt of the PV array in degrees. 0 is horizontal
    array_azimuth: The azimuth of the PV array in degrees east of north. 0 is north
    out_file_time_series: str specifying output CSV file name for the time
        series data. If None, no file is written
    out_file_tilt: str specifying output TXT file name for the tilt data.
        If None, no file is written

    Returns
    -------
    Pandas dataframe of finite element model input time series
    '''

    # Parse the TMY file
    with open(tmy_file) as f:
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
    # We care about the sun position halfway through the interval preceeding
    # each time stamp
    sun = pvlib.solarposition.get_solarposition(tmy.index - pd.Timedelta('30 Minutes'), lat, lon,
                                                altitude=elevation,
                                                pressure=100. * tmy['Pressure (mbar)'].mean(),
                                                temperature=tmy['Dry-bulb (C)'].mean())
    aoi = pvlib.irradiance.aoi(array_tilt, array_azimuth, sun.apparent_zenith, sun.azimuth)
    # Get aoi and sun back on the same datetime index as tmy
    sun.index = sun.index + pd.Timedelta('30 Minutes')
    aoi.index = aoi.index + pd.Timedelta('30 Minutes')

    # Calculate poai components
    beam = tmy['DNI (W/m^2)'] * np.cos(np.deg2rad(aoi))
    beam = np.clip(beam, 0, None)
    sky = pvlib.irradiance.isotropic(array_tilt, tmy['DHI (W/m^2)'])
    poai = beam + sky

    # Calculate clearness index
    clearness_index = tmy['GHI (W/m^2)'] / tmy['ETR (W/m^2)']
    clearness_index = clearness_index.replace([np.inf, -np.inf], np.nan)
    clearness_index = clearness_index.fillna(1)

    # Parse the optics file
    optics = pd.read_csv(optics_file)

    if max(optics['angle']) < 85:
        warnings.warn('The maximum angle in optics_file is <85 degrees. TOMCAT requires optical '
                      'data at high angles. An interpolation to 90 degrees will be performed, '
                      'but the results may be unphysical!')

    # We will be extrapolating to 90 but don't want things going negative
    if max(optics['angle']) < 90:
        row = {
            'angle': 90.0,
            'glass_abs_W/m2': 0.0,
            'encapsulant_abs_W/m2': 0.0,
            'cell_abs_W/m2': 0.0,
            'current_factor': 0.0
        }

        optics.append(row, ignore_index=True)

    # Calculate values for diffuse irradiance
    diffuse = {
        'cell_abs_W/m2': hemi_ave(optics['angle'], optics['cell_abs_W/m2']),
        'encapsulant_abs_W/m2': hemi_ave(optics['angle'], optics['encapsulant_abs_W/m2']),
        'glass_abs_W/m2': hemi_ave(optics['angle'], optics['glass_abs_W/m2']),
        'current_factor': hemi_ave(optics['angle'], optics['current_factor'])
    }

    # Interpolations for each column in optics
    # Note the removal of cosine factor
    interp_kwargs = {'fill_value': 'extrapolate', 'kind': 'linear'}
    glass_abs = interp1d(optics['angle'], optics['glass_abs_W/m2'] / np.cos(np.deg2rad(optics['angle'])), **interp_kwargs)
    encapsulant_abs = interp1d(optics['angle'], optics['encapsulant_abs_W/m2'] / np.cos(np.deg2rad(optics['angle'])), **interp_kwargs)
    cell_abs = interp1d(optics['angle'], optics['cell_abs_W/m2'] / np.cos(np.deg2rad(optics['angle'])), **interp_kwargs)
    current_factor = interp1d(optics['angle'], optics['current_factor'] / np.cos(np.deg2rad(optics['angle'])), **interp_kwargs)

    # build the output
    out = pd.DataFrame()

    out['temp'] = tmy['Dry-bulb (C)'] + 273.15
    out['temp_sky'] = sky_temp(tmy['Dew-point (C)'], clearness_index, tmy['Dry-bulb (C)'])
    out['temp_ground'] = ground_temp(tmy['Dry-bulb (C)'], tmy['GHI (W/m^2)'])
    out['poai'] = poai
    out['dni'] = tmy['DNI (W/m^2)']
    out['wind_speed'] = tmy['Wspd (m/s)']
    out['elevation_projected'] = projected_sun_elevation(np.deg2rad(sun['apparent_elevation']), np.deg2rad(sun['azimuth']), np.deg2rad(array_azimuth))

    out['abs_glass'] = glass_abs(aoi) * beam / 1000.0 + diffuse['glass_abs_W/m2'] * sky / 1000.0
    out['abs_cell'] = cell_abs(aoi) * beam / 1000.0 + diffuse['cell_abs_W/m2'] * sky / 1000.0
    out['abs_encapsulant'] = encapsulant_abs(aoi) * beam / 1000.0 + diffuse['encapsulant_abs_W/m2'] * sky / 1000.0
    out['current_factor'] = current_factor(aoi) * beam / poai + diffuse['current_factor'] * sky / poai
    out['current_factor'] = out['current_factor'].fillna(0.0)

    out['elapsed'] = 3600. + (out.index - out.index[0]).astype(np.timedelta64()) / 1.e9
    out.set_index('elapsed', inplace=True)

    if out_file_time_series:
        if type(out_file_time_series) is not str:
            raise TypeError(
                'out_file_time_series must be a string specifying the desired filename for CSV output')
        out.to_csv(out_file_time_series)

    if out_file_tilt:
        if type(out_file_tilt) is not str:
            raise TypeError(
                'out_file_tilt must be a string specifying the desired filename for TXT output')
        with open(out_file_tilt, 'w') as tilt_file:
            tilt_file.write(str(array_tilt))

    return out


def total_abs(spectral_abs, spectral_power):
    '''Return the total absorption based on spectrally resolve absorption and power,
    both inputs are pandas series with wavelength index'''
    power_absorbed = spectral_power * spectral_abs
    total_power_absorbed = trapz(power_absorbed, power_absorbed.index)
    return total_power_absorbed


def parse_pvl(pvl_file, glass_columns, front_encapsulant_columns, cell_columns, photocurrent_columns,
              normal_incidence_current_factor=1, out_file='optics.csv', iqe_file='IQE.csv', iqe_header_rows=2,
              angle_col='Source #1 zenith(°)'):
    '''
    Generates optics file appropriate for generate_input() based on PVLighthouse results from SunSolve v3.5.3.
    Changes to SunSolve output in future versions may cause problems. input based on TMY and optical data

    Parameters
    ----------
    pvl_file: string specifying a SunSolve result file containing spectral- and angle-resolved RAT data.
    glass_columns: list of strings specifying the columns to include in glass absorption
    front_encapsulant_columns: list of strings specifying the columns to include in front encapsulant absorption
    cell_columns: list of strings specifying the columns to include in cell absorption
    photocurrent_columns: list of strings specifying the columns where absorption is interpreted to generate photocurrent
    normal_incidence_current_factor: (numeric) The current factor for normal incidence
    out_file: string specifying the file name for the optics file to be written. If None, no file is written
    iqe_file: string specifying an IQE file to be used when calculating photocurrent. The IQE file must have columns of
              (wavelength(nm), IQE)
    iqe_header_rows: Integer passed to pandas.read_csv(header=) for parsing iqe_file
    angle_col: string specifying the column containing the angle of incidence

    Returns
    -------
    Pandas dataframe corresponding to the optics file for generate_input()
    '''

    # Read the pvl results file
    optics_results = pd.read_csv(pvl_file)
    optics_results.set_index('Wavelength (nm)', inplace=True)

    # Parse the IQE file
    iqe = pd.read_csv(iqe_file, header=iqe_header_rows)
    iqe.columns = ['wl', 'iqe']
    iqe = iqe.set_index('wl')
    iqe = iqe.sort_index()
    iqe_interp = interp1d(iqe.index, iqe.iqe, fill_value='extrapolate')

    # Incorporate IQE into the main results df
    optics_results['iqe'] = iqe_interp(optics_results.index)

    # get angles and ensure they include 0
    angles = optics_results[angle_col].unique()
    if 0 not in angles:
        raise ValueError('Results for normal incidence must be included.')

    # handle normal incidence photocurrent first
    angle = 0
    df = optics_results[optics_results[angle_col] == angle]
    photocurrent_abs = df[photocurrent_columns].sum(axis=1)
    photocurrent = df['iqe'] * \
        df['Photon flux in WL bin (A cm-2)'] * photocurrent_abs
    normal_photocurrent = photocurrent.sum()

    # Generate optics parameters for each angle
    results = []
    for angle in angles:
        result_dict = {}

        df = optics_results[optics_results[angle_col] == angle]

        glass_abs = df[glass_columns].sum(axis=1)
        front_encapsulant_abs = df[front_encapsulant_columns].sum(axis=1)
        cell_abs = df[cell_columns].sum(axis=1)
        photocurrent_abs = df[photocurrent_columns].sum(axis=1)

        total_glass_abs = total_abs(
            glass_abs, df['Spectral intensity (W m-2 nm-1)'])
        total_cell_abs = total_abs(cell_abs, df['Spectral intensity (W m-2 nm-1)'])
        total_front_encapsulant_abs = total_abs(
            front_encapsulant_abs, df['Spectral intensity (W m-2 nm-1)'])

        photocurrent = df['iqe'] * df['Photon flux in WL bin (A cm-2)'] * photocurrent_abs
        photocurrent = photocurrent.sum()

        current_factor = normal_incidence_current_factor * photocurrent / normal_photocurrent

        result_dict['angle'] = angle
        result_dict['glass_abs_W/m2'] = total_glass_abs
        result_dict['encapsulant_abs_W/m2'] = total_front_encapsulant_abs
        result_dict['cell_abs_W/m2'] = total_cell_abs
        result_dict['current_factor'] = current_factor

        results.append(result_dict)
    out = pd.DataFrame(results)
    out = out[['angle', 'glass_abs_W/m2', 'encapsulant_abs_W/m2',
               'cell_abs_W/m2', 'current_factor']]

    if out_file:
        out.to_csv(out_file, index=False)
    return out
