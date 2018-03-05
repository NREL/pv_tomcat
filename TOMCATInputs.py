
# coding: utf-8

# In[2]:


get_ipython().run_line_magic('matplotlib', 'inline')
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# for talking to the database:
from sqlalchemy import create_engine
engine = create_engine('mysql+mysqlconnector://otfread:x0B*T8c!@otfdata-db.nrel.gov/otfdata', echo=False)

import scipy.constants # for stefan-boltzmann
from scipy import interpolate # for interpolating optics results
import os.path # for checking file existence

# for plotly plots:
import plotly.offline as py
py.offline.init_notebook_mode()
import plotly.graph_objs as go
from plotly import tools


# # Year-long runs

# In[3]:


# Import RMIS data (use the pickle if it exists, otherwise get from database)
rmis_pickle_name = 'tomcat_input_rmis.pickle'
rmis_raw_pickle_name = 'tomcat_input_rmis_raw.pickle'
if os.path.exists(rmis_pickle_name):
    rmis = pd.read_pickle(rmis_pickle_name)
else:
    if os.path.exists(rmis_raw_pickle_name):
        rmis = pd.read_pickle(rmis_raw_pickle_name)
    else:
        rmis = pd.read_sql_query('''SELECT measdatetime,
        wind_speed,
        global_horizontal_latitude_tilt as poai,
        direct_normal as dni,
        ambient_temperature as temp,
        spa_zenithangle as zenith_deg,
        spa_azimuthangle as azimuth_deg,
        spa_arrayaoi as aoi_deg
        FROM rmis
        WHERE
        measdatetime > %s
        AND measdatetime < %s
        ORDER BY measdatetime;''', engine, params = ['2015-06-01', '2016-06-01'])
        rmis.to_pickle(rmis_raw_pickle_name)
    rmis['measdatetime'] = pd.to_datetime(rmis.measdatetime)
    rmis = rmis.set_index('measdatetime')
    for irradiance in ['poai', 'dni']:
        rmis[irradiance] = np.clip(rmis[irradiance], 1.e-9, 2000.)
    rmis['aoi'] = np.pi/180.*rmis['aoi_deg']
    rmis['elevation'] = np.pi/180.*np.clip(90. - rmis.zenith_deg, 0., 90.)
    # RMIS gives azimuth in a zero-south convention; this rotates to zero-north
    rmis['azimuth_deg'] = (rmis['azimuth_deg'] + 180.)%360.
    rmis['azimuth'] = np.pi/180.*rmis['azimuth_deg']
    # project elevation angle into the north-up plane
    rmis['elevation_projected'] = np.clip(np.arctan2(np.tan(rmis.elevation), -np.cos(rmis.azimuth)), 0., np.pi)
    # zero out the times when the sun is below the horizon
    # the COMSOL shade model uses this to assume everything is shady
    rmis['elevation_projected'] = rmis['elevation_projected']*(rmis.elevation > 0).astype(int)
    # patch a period of bad wind (anemometer covered in ice?!)
    patch_wind_speed = rmis[(rmis.index > '2015-10-26') & (rmis.index < '2015-11-25')].wind_speed.median()
    rmis.ix[(rmis.index > '2015-11-25') & (rmis.index < '2015-12-02'), 'wind_speed'] = patch_wind_speed
    # fix a negative wind speed
    rmis['wind_speed'] = np.clip(rmis['wind_speed'], 0, np.infty)
    # resample to 5 minutes
    rmis = rmis.resample('5T', label = 'right').mean()
    # Label should actually be at "center", so adjust the index accordingly:
    rmis.index = rmis.index - np.timedelta64(5*60/2, 's')
    rmis['elapsed'] = (rmis.index - rmis.index.min())/np.timedelta64(1, 's')
    rmis.interpolate(method = 'linear', inplace = True)
    rmis['temp'] = rmis['temp'] + 273.15
    # beam component of POAI
    rmis['poai_beam'] = np.clip(rmis.dni*np.cos(rmis.aoi_deg*np.pi/180.0), 1.e-9, 2000.)
    # diffuse tilted irradiance
    rmis['poai_diffuse'] = np.clip(rmis.poai - rmis.poai_beam, 1.e-9, 2000.)
    rmis.to_pickle(rmis_pickle_name)


# In[4]:


# Import SRRL BMS data (use the pickle if it exists, otherwise get from database)
bms_pickle_name = 'tomcat_input_bms.pickle'
if os.path.exists(bms_pickle_name):
    bms = pd.read_pickle(bms_pickle_name)
else:
    bms_raw = pd.read_csv('http://midc.nrel.gov/apps/data_api.pl?site=BMS&begin=20150601&end=20160601')
    bms = pd.DataFrame()
    bms_columns = {
    'poai_mesa': 'Global 40-South CMP11 [W/m^2]',
        'ulr_net': 'Instrument Net UW PIR [W/m^2]',
        'ulr_temp': 'PIR UW Case Temp [deg K]',
        'dlr_net': 'Instrument Net DW PIR [W/m^2]',
        'dlr_temp': 'PIR DW Case Temp [deg K]'
    }
    for column in bms_columns.keys():
        bms[column] = bms_raw[bms_columns[column]]
    bms['temp_sky'] = np.clip(
        np.power((scipy.constants.sigma*np.power(bms['dlr_temp'], 4) + bms['dlr_net']), 1/4.)/np.power(scipy.constants.sigma, 1/4.),
        0, 300)
    bms['temp_ground'] = np.power((scipy.constants.sigma*np.power(bms['ulr_temp'], 4) + bms['ulr_net']), 1/4.)/np.power(scipy.constants.sigma, 1/4.)
    bms['measdatetime'] = pd.to_datetime(
        map(lambda year, doy, mst: str(year) + '-' + str(doy) + '-' + str(mst).zfill(4)[:2] + ':' + str(mst).zfill(4)[2:], bms_raw['Year'], bms_raw['DOY'], bms_raw['MST']),
        format = '%Y-%j-%H:%M'
    )
    bms = bms.set_index('measdatetime')
    bms = bms.resample('5T', label = 'right').mean()
    # Label should actually be at "center", so adjust the index accordingly:
    bms.index = bms.index - np.timedelta64(5*60/2, 's')
    bms.interpolate(method = 'linear', inplace = True)
    bms.to_pickle(bms_pickle_name)


# In[5]:


# indata = rmis.join(bms)
indata = pd.read_csv('indata_Slauch2018-02-07.csv')


# ## import optical results

# In[6]:


absorption = pd.read_csv('angular_optical_results_Slauch2018-02-07.csv', index_col = 0)
absorption.columns = [col.replace('_abs_W/m2','') for col in absorption.columns]
case_name_transform = {
    'baseline': 'Baseline_Slauch2018-02-07',
    'ZrO2_4': 'ZrO2_4_Slauch2018-02-07'
}
absorption['case'] = [case_name_transform[case] for case in absorption['case']]


# In[7]:


absorption_interp = dict.fromkeys(absorption.case.unique().tolist())
absorption_diffuse = dict.fromkeys(absorption.case.unique().tolist())
for case in absorption_interp:
    absorption_interp[case] = dict.fromkeys([col for col in absorption.columns if col not in ['case', 'angle']])
    absorption_diffuse[case] = dict.fromkeys([col for col in absorption.columns if col not in ['case', 'angle']])


# In[8]:


for case in absorption_interp:
    for key in absorption_interp[case]:
        selector = (absorption.case == case) & (absorption.angle != 180)
        x = absorption[selector].angle.tolist()
        y = (absorption[selector][key]/np.cos(np.pi/180.0*absorption[selector].angle)).tolist()
        absorption_interp[case][key] = interpolate.interp1d(x, y, fill_value = 'extrapolate', kind = 'linear')
for case in absorption_diffuse:
    for key in absorption_diffuse[case]:
        selector = (absorption.case == case) & (absorption.angle == 180)
        absorption_diffuse[case][key] = absorption[selector][key].values[0]


# ## write input files

# In[22]:


out_columns = [
    'temp', 'temp_sky', 'temp_ground',
    'poai', 'dni',
    'wind_speed',
    'elevation_projected',
    'abs_glass', 'abs_encapsulant', 'abs_cell', 'current_factor'
]
for case in absorption_interp.keys():
    absdata = pd.DataFrame(index = indata.index)
    absdata['abs_glass'] = (
        absorption_interp[case]['glass'](indata.aoi_deg)*indata.poai_beam/1000.0
        + absorption_diffuse[case]['glass']*indata.poai_diffuse/1000.0
    )
    absdata['abs_encapsulant'] = (
        absorption_interp[case]['EVA'](indata.aoi_deg)*indata.poai_beam/1000.0
        + absorption_diffuse[case]['EVA']*indata.poai_diffuse/1000.0
    )
    absdata['abs_cell'] = (
        absorption_interp[case]['cell'](indata.aoi_deg)*indata.poai_beam/1000.0
        + absorption_diffuse[case]['cell']*indata.poai_diffuse/1000.0
    )
    absdata['current_factor'] = np.clip((
        absorption_interp[case]['current_derate'](indata.aoi_deg)*indata.poai_beam/indata.poai
        + absorption_diffuse[case]['current_derate']*indata.poai_diffuse/indata.poai
        ), 0, 2)
    indata_out = indata.join(absdata)
    indata_out.set_index('elapsed')[out_columns].to_csv('TOMCATInput_' + case + '.csv')


# ### optionally, plot the data to do a reality check

# In[9]:


case = 'Baseline_Slauch2018-02-07'
absdata = pd.DataFrame(index = indata.index)
absdata['abs_glass'] = (
    absorption_interp[case]['glass'](indata.aoi_deg)*indata.poai_beam/1000.0
    + absorption_diffuse[case]['glass']*indata.poai_diffuse/1000.0
)
absdata['abs_encapsulant'] = (
    absorption_interp[case]['EVA'](indata.aoi_deg)*indata.poai_beam/1000.0
    + absorption_diffuse[case]['EVA']*indata.poai_diffuse/1000.0
)
absdata['abs_cell'] = (
    absorption_interp[case]['cell'](indata.aoi_deg)*indata.poai_beam/1000.0
    + absorption_diffuse[case]['cell']*indata.poai_diffuse/1000.0
)
absdata['current_factor'] = np.clip((
    absorption_interp[case]['current_derate'](indata.aoi_deg)*indata.poai_beam/indata.poai
    + absorption_diffuse[case]['current_derate']*indata.poai_diffuse/indata.poai
    ), 0, 2)
indata_out = indata.join(absdata)


trace1 = [
    go.Scatter(x=indata_out.index, y=indata_out.poai, name='poai'),
    go.Scatter(x=indata_out.index, y=indata_out.dni, name='dni')
]
trace2 = [
    go.Scatter(x=indata_out.index, y=indata_out.elevation_projected*180./np.pi*(rmis.elevation > 0).astype(int), name='elevation_projected'),
    go.Scatter(x=indata_out.index, y=indata_out.elevation*180./np.pi, name='elevation')
]
trace3 = [
    go.Scatter(x=indata_out.index, y=indata_out.abs_glass, name='abs_glass'),
    go.Scatter(x=indata_out.index, y=indata_out.abs_encapsulant, name='abs_encapsulant'),
    go.Scatter(x=indata_out.index, y=indata_out.abs_cell, name='abs_cell'),
    go.Scatter(x=indata_out.index, y=indata_out.current_factor*indata_out.poai, name='current_factor*poai')
]
trace4 = [
    go.Scatter(x=indata_out.index, y=indata_out.temp, name='temp'),
    go.Scatter(x=indata_out.index, y=indata_out.temp_sky, name='temp_sky'),
    go.Scatter(x=indata_out.index, y=indata_out.temp_ground, name='temp_ground')
]
trace5 = [
    go.Scatter(x=indata_out.index, y=indata_out.wind_speed, name='wind_speed')
]



fig = tools.make_subplots(rows = 5, cols = 1, specs = [[{}], [{}], [{}], [{}], [{}]],
    shared_xaxes = True, shared_yaxes = False,
    vertical_spacing = 0.01)
# layout = go.Layout(xaxis = dict(range = [10.9e6, 11e6]))
# fig['layout'].update(layout)
for trace in trace1:
    fig.append_trace(trace, 1, 1)
for trace in trace2:
    fig.append_trace(trace, 2, 1)
for trace in trace3:
    fig.append_trace(trace, 3, 1)
for trace in trace4:
    fig.append_trace(trace, 4, 1)
for trace in trace5:
    fig.append_trace(trace, 5, 1)

# py.offline.iplot(fig)


# # create/compile/run the models

# In[25]:


from subprocess import call
from string import Template
import datetime
import shutil


# In[28]:


template_file = open('TOMCATModel_Template.java')
template_in = Template(template_file.read())
template_file.close()
model_dir = '../TOMCATModel'
batch_file = open(os.path.join(model_dir, 'TOMCATBatch_' + datetime.datetime.now().isoformat().replace(':', '-').replace('.', '-').replace('T', '_') + '.sh'), 'w')
batch_file.write('#!/bin/bash\n')
for case in absorption_interp.keys():
    template_dict = {
        'runlabel': case,
        'fullpath': os.path.dirname(os.path.abspath(os.path.join(model_dir, case + '/TOMCATModel.java'))),
        'absolutefile': os.path.abspath(os.path.join(model_dir, case + '/TOMCATModel.java')),
    }
    source_out = template_in.substitute(template_dict)
    if not os.path.exists(template_dict['fullpath']):
        os.makedirs(template_dict['fullpath'])
    shutil.copy2('TOMCATInput_' + case + '.csv', os.path.join(template_dict['fullpath'], template_dict['fullpath']))
    with open(template_dict['absolutefile'], 'w') as file_out:
        file_out.write(source_out)
#     call('/Applications/COMSOL53/Multiphysics/bin/comsol compile -jdkroot `/usr/libexec/java_home` ' + template_dict['absolutefile'], shell = True)
    call('/Applications/COMSOL53/Multiphysics/bin/comsol compile -jdkroot /Library/Java/JavaVirtualMachines/jdk1.8.0_162.jdk/Contents/Home/ ' + template_dict['absolutefile'], shell = True)
    batch_file.write('/Applications/COMSOL53/Multiphysics/bin/comsol batch -inputfile ' + template_dict['absolutefile'].replace('.java', '.class') + '\n')
batch_file.close()


# # sub-year runs for POOMA validation

# In[2]:


# Import RMIS data (use the pickle if it exists, otherwise get from database)
rmis_pickle_name = 'tomcat_partialyear_input_rmis.pickle'
rmis_raw_pickle_name = 'tomcat_partialyear_input_rmis_raw.pickle'
if os.path.exists(rmis_pickle_name):
    rmis = pd.read_pickle(rmis_pickle_name)
else:
    if os.path.exists(rmis_raw_pickle_name):
        rmis = pd.read_pickle(rmis_raw_pickle_name)
    else:
        rmis = pd.read_sql_query('''SELECT measdatetime,
        global_horizontal_latitude_tilt as poai,
        direct_normal as dni,
        ambient_temperature as temp,
        spa_zenithangle as zenith_deg,
        spa_azimuthangle as azimuth_deg,
        spa_arrayaoi as aoi_deg
        FROM rmis
        WHERE
        measdatetime > %s
        AND measdatetime < %s
        ORDER BY measdatetime;''', engine, params = ['2017-05-06', '2017-06-11'])
        rmis.to_pickle(rmis_raw_pickle_name)
    rmis['measdatetime'] = pd.to_datetime(rmis.measdatetime)
    rmis = rmis.set_index('measdatetime')
    for irradiance in ['poai', 'dni']:
        rmis[irradiance] = np.clip(rmis[irradiance], 1.e-9, 2000.)
    rmis['aoi'] = np.pi/180.*rmis['aoi_deg']
    rmis['elevation'] = np.pi/180.*np.clip(90. - rmis.zenith_deg, 0., 90.)
    # RMIS gives azimuth in a zero-south convention; this rotates to zero-north
    rmis['azimuth_deg'] = (rmis['azimuth_deg'] + 180.)%360.
    rmis['azimuth'] = np.pi/180.*rmis['azimuth_deg']
    # project elevation angle into the north-up plane
    rmis['elevation_projected'] = np.clip(np.arctan2(np.tan(rmis.elevation), -np.cos(rmis.azimuth)), 0., np.pi)
    # zero out the times when the sun is below the horizon
    # the COMSOL shade model uses this to assume everything is shady
    rmis['elevation_projected'] = rmis['elevation_projected']*(rmis.elevation > 0).astype(int)
    # resample to 5 minutes
    rmis = rmis.resample('5T', label = 'right').mean()
    # Label should actually be at "center", so adjust the index accordingly:
    rmis.index = rmis.index - np.timedelta64(5*60/2, 's')
    rmis['elapsed'] = (rmis.index - rmis.index.min())/np.timedelta64(1, 's')
    rmis.interpolate(method = 'linear', inplace = True)
    rmis['temp'] = rmis['temp'] + 273.15
    # beam component of POAI
    rmis['poai_beam'] = np.clip(rmis.dni*np.cos(rmis.aoi_deg*np.pi/180.0), 1.e-9, 2000.)
    # diffuse tilted irradiance
    rmis['poai_diffuse'] = np.clip(rmis.poai - rmis.poai_beam, 1.e-9, 2000.)
    rmis.to_pickle(rmis_pickle_name)


# In[3]:


# Import SRRL BMS data (use the pickle if it exists, otherwise get from database)
bms_pickle_name = 'tomcat_partialyear_input_bms.pickle'
if os.path.exists(bms_pickle_name):
    bms = pd.read_pickle(bms_pickle_name)
else:
    bms_raw = pd.read_csv('http://midc.nrel.gov/apps/data_api.pl?site=BMS&begin=20170506&end=20170611')
    bms = pd.DataFrame()
    bms_columns = {
    'poai_mesa': 'Global 40-South CMP11 [W/m^2]',
        'ulr_net': 'Instrument Net UW PIR [W/m^2]',
        'ulr_temp': 'PIR UW Case Temp [deg K]',
        'dlr_net': 'Instrument Net DW PIR [W/m^2]',
        'dlr_temp': 'PIR DW Case Temp [deg K]',
        'wind_speed': 'Avg Wind Speed @ 6ft [m/s]'
    }
    for column in bms_columns.keys():
        bms[column] = bms_raw[bms_columns[column]]
    bms['temp_sky'] = np.clip(
        np.power((scipy.constants.sigma*np.power(bms['dlr_temp'], 4) + bms['dlr_net']), 1/4.)/np.power(scipy.constants.sigma, 1/4.),
        0, 300)
    bms['temp_ground'] = np.power((scipy.constants.sigma*np.power(bms['ulr_temp'], 4) + bms['ulr_net']), 1/4.)/np.power(scipy.constants.sigma, 1/4.)
    bms['measdatetime'] = pd.to_datetime(
        map(lambda year, doy, mst: str(year) + '-' + str(doy) + '-' + str(mst).zfill(4)[:2] + ':' + str(mst).zfill(4)[2:], bms_raw['Year'], bms_raw['DOY'], bms_raw['MST']),
        format = '%Y-%j-%H:%M'
    )
    bms = bms.set_index('measdatetime')
    # patch a period of bad wind (anemometer covered in ice?!)
    patch_wind_speed = bms[(bms.index < '2017-05-08 14:00') | (bms.index > '2017-05-12 12:00')].wind_speed.median()
    bms.ix[(bms.index > '2017-05-08 14:00') & (bms.index < '2017-05-12 12:00'), 'wind_speed'] = patch_wind_speed
    # resample to match pooma
    bms = bms.resample('5T', label = 'right').mean()
    # Label should actually be at "center", so adjust the index accordingly:
    bms.index = bms.index - np.timedelta64(5*60/2, 's')
    bms.interpolate(method = 'linear', inplace = True)
    bms.to_pickle(bms_pickle_name)


# In[4]:


indata = rmis.join(bms)


# ## import optical results

# In[5]:


absorption = pd.read_csv('angular_optical_results.csv', index_col = 0)
absorption.columns = [col.replace('_abs_W/m2','') for col in absorption.columns]
case_name_transform = {
    'baseline': 'Baseline',
    'Li_I': 'Li_1',
    'Li_II': 'Li_2',
    'ARC': 'OrdinaryARC',
    'Ideal ARC': 'IdealARC',
    'Ideal Reflector': 'IdealSBR',
    'Ideal Reflector and ARC': 'IdealSBR_OrdinaryARC',
    'Ideal Reflector and Ideal ARC': 'IdealSBR_IdealARC'
}
absorption['case'] = [case_name_transform[case] for case in absorption['case']]


# In[6]:


absorption_interp = dict.fromkeys(absorption.case.unique().tolist())
absorption_diffuse = dict.fromkeys(absorption.case.unique().tolist())
for case in absorption_interp:
    absorption_interp[case] = dict.fromkeys([col for col in absorption.columns if col not in ['case', 'angle']])
    absorption_diffuse[case] = dict.fromkeys([col for col in absorption.columns if col not in ['case', 'angle']])


# In[7]:


for case in absorption_interp:
    for key in absorption_interp[case]:
        selector = (absorption.case == case) & (absorption.angle != 180)
        x = absorption[selector].angle.tolist()
        y = (absorption[selector][key]/np.cos(np.pi/180.0*absorption[selector].angle)).tolist()
        absorption_interp[case][key] = interpolate.interp1d(x, y, fill_value = 'extrapolate', kind = 'linear')
for case in absorption_diffuse:
    for key in absorption_diffuse[case]:
        selector = (absorption.case == case) & (absorption.angle == 180)
        absorption_diffuse[case][key] = absorption[selector][key].values[0]


# ## write input files

# In[8]:


out_columns = [
    'temp', 'temp_sky', 'temp_ground',
    'poai', 'dni',
    'wind_speed',
    'elevation_projected',
    'abs_glass', 'abs_encapsulant', 'abs_cell', 'current_factor'
]
for case in ['Baseline']:
    absdata = pd.DataFrame(index = indata.index)
    absdata['abs_glass'] = (
        absorption_interp[case]['glass'](indata.aoi_deg)*indata.poai_beam/1000.0
        + absorption_diffuse[case]['glass']*indata.poai_diffuse/1000.0
    )
    absdata['abs_encapsulant'] = (
        absorption_interp[case]['EVA'](indata.aoi_deg)*indata.poai_beam/1000.0
        + absorption_diffuse[case]['EVA']*indata.poai_diffuse/1000.0
    )
    absdata['abs_cell'] = (
        absorption_interp[case]['cell'](indata.aoi_deg)*indata.poai_beam/1000.0
        + absorption_diffuse[case]['cell']*indata.poai_diffuse/1000.0
    )
    absdata['current_factor'] = np.clip((
        absorption_interp[case]['current_derate'](indata.aoi_deg)*indata.poai_beam/indata.poai
        + absorption_diffuse[case]['current_derate']*indata.poai_diffuse/indata.poai
        ), 0, 2)
    indata_out = indata.join(absdata)
    indata_out.set_index('elapsed')[out_columns].to_csv('TOMCATInput_PartialYear_' + case + '.csv')


# In[ ]:


case = 'Baseline'
absdata = pd.DataFrame(index = indata.index)
absdata['abs_glass'] = (
    absorption_interp[case]['glass'](indata.aoi_deg)*indata.poai_beam/1000.0
    + absorption_diffuse[case]['glass']*indata.poai_diffuse/1000.0
)
absdata['abs_encapsulant'] = (
    absorption_interp[case]['EVA'](indata.aoi_deg)*indata.poai_beam/1000.0
    + absorption_diffuse[case]['EVA']*indata.poai_diffuse/1000.0
)
absdata['abs_cell'] = (
    absorption_interp[case]['cell'](indata.aoi_deg)*indata.poai_beam/1000.0
    + absorption_diffuse[case]['cell']*indata.poai_diffuse/1000.0
)
absdata['current_factor'] = np.clip((
    absorption_interp[case]['current_derate'](indata.aoi_deg)*indata.poai_beam/indata.poai
    + absorption_diffuse[case]['current_derate']*indata.poai_diffuse/indata.poai
    ), 0, 2)
indata_out = indata.join(absdata)


trace1 = [
    go.Scatter(x=indata_out.index, y=indata_out.poai, name='poai'),
    go.Scatter(x=indata_out.index, y=indata_out.dni, name='dni')
]
trace2 = [
    go.Scatter(x=indata_out.index, y=indata_out.elevation_projected*180./np.pi*(rmis.elevation > 0).astype(int), name='elevation_projected'),
    go.Scatter(x=indata_out.index, y=indata_out.elevation*180./np.pi, name='elevation')
]
trace3 = [
    go.Scatter(x=indata_out.index, y=indata_out.abs_glass, name='abs_glass'),
    go.Scatter(x=indata_out.index, y=indata_out.abs_encapsulant, name='abs_encapsulant'),
    go.Scatter(x=indata_out.index, y=indata_out.abs_cell, name='abs_cell'),
    go.Scatter(x=indata_out.index, y=indata_out.current_factor*indata_out.poai, name='current_factor*poai')
]
trace4 = [
    go.Scatter(x=indata_out.index, y=indata_out.temp, name='temp'),
    go.Scatter(x=indata_out.index, y=indata_out.temp_sky, name='temp_sky'),
    go.Scatter(x=indata_out.index, y=indata_out.temp_ground, name='temp_ground')
]
trace5 = [
    go.Scatter(x=indata_out.index, y=indata_out.wind_speed, name='wind_speed')
]



fig = tools.make_subplots(rows = 5, cols = 1, specs = [[{}], [{}], [{}], [{}], [{}]],
    shared_xaxes = True, shared_yaxes = False,
    vertical_spacing = 0.01)
# layout = go.Layout(xaxis = dict(range = [10.9e6, 11e6]))
# fig['layout'].update(layout)
for trace in trace1:
    fig.append_trace(trace, 1, 1)
for trace in trace2:
    fig.append_trace(trace, 2, 1)
for trace in trace3:
    fig.append_trace(trace, 3, 1)
for trace in trace4:
    fig.append_trace(trace, 4, 1)
for trace in trace5:
    fig.append_trace(trace, 5, 1)

# py.offline.iplot(fig)


# # create/compile/run the models

# In[12]:


from subprocess import call
from string import Template
import datetime
import shutil


# In[13]:


template_file = open('TOMCATModel_Template.java')
template_in = Template(template_file.read())
template_file.close()
model_dir = '../TOMCATModel'
batch_file = open(os.path.join(model_dir, 'TOMCATBatch_' + datetime.datetime.now().isoformat().replace(':', '-').replace('.', '-').replace('T', '_') + '.sh'), 'w')
batch_file.write('#!/bin/bash\n')
for case in absorption_interp.keys():
    template_dict = {
        'runlabel': case,
        'fullpath': os.path.dirname(os.path.abspath(os.path.join(model_dir, case + '/TOMCATModel.java'))),
        'absolutefile': os.path.abspath(os.path.join(model_dir, case + '/TOMCATModel.java')),
    }
    source_out = template_in.substitute(template_dict)
    if not os.path.exists(template_dict['fullpath']):
        os.makedirs(template_dict['fullpath'])
    shutil.copy2('TOMCATInput_' + case + '.csv', os.path.join(template_dict['fullpath'], template_dict['fullpath']))
    with open(template_dict['absolutefile'], 'w') as file_out:
        file_out.write(source_out)
    call('/Applications/COMSOL53/Multiphysics/bin/comsol compile -jdkroot `/usr/libexec/java_home` ' + template_dict['absolutefile'], shell = True)
    batch_file.write('/Applications/COMSOL53/Multiphysics/bin/comsol batch -inputfile ' + template_dict['absolutefile'].replace('.java', '.class') + '\n')
batch_file.close()


# ## try a brute-force sweep

# In[126]:


template_file = open('TOMCATModel_Template_ConvectionSweep.java')
template_in = Template(template_file.read())
template_file.close()
model_dir = '../TOMCATModel'
batch_file = open(os.path.join(model_dir, 'TOMCATBatch_' + datetime.datetime.now().isoformat().replace(':', '-').replace('.', '-').replace('T', '_') + '.sh'), 'w')
batch_file.write('#!/bin/bash\n')
case = 'Baseline'
for clf in np.arange(0.1,2.1,0.1):
    template_dict = {
        'runlabel': case,
        'fullpath': os.path.dirname(os.path.abspath(os.path.join(model_dir, case + '_CLF' + str(clf) + '/TOMCATModel.java'))),
        'absolutefile': os.path.abspath(os.path.join(model_dir, case + '_CLF' + str(clf) + '/TOMCATModel.java')),
        'convection_length_factor': clf
    }
    source_out = template_in.substitute(template_dict)
    if not os.path.exists(template_dict['fullpath']):
        os.makedirs(template_dict['fullpath'])
    shutil.copy2('TOMCATInput_' + case + '.csv', os.path.join(template_dict['fullpath'], template_dict['fullpath']))
    with open(template_dict['absolutefile'], 'w') as file_out:
        file_out.write(source_out)
    call('/Applications/COMSOL53/Multiphysics/bin/comsol compile -jdkroot `/usr/libexec/java_home` ' + template_dict['absolutefile'], shell = True)
    batch_file.write('/Applications/COMSOL53/Multiphysics/bin/comsol batch -inputfile ' + template_dict['absolutefile'].replace('.java', '.class') + '\n')
batch_file.close()



# ## compile manually-created runs

# In[14]:


model_dir = '../TOMCATModel'
batch_file = open(os.path.join(model_dir, 'TOMCATBatch_' + datetime.datetime.now().isoformat().replace(':', '-').replace('.', '-').replace('T', '_') + '.sh'), 'w')
batch_file.write('#!/bin/bash\n')
runs = [
    'HighThermalConductivity_BackPackage',
    'HighThermalConductivity_BackSheet',
    'SmallTemperatureCoefficient',
    'HighEmissivity_Front',
    'HighEmissivity_Both',
    'HighEmissivity_Back',
    'HighEfficiency'
]
for case in runs:
    template_dict = {
        'runlabel': case,
        'fullpath': os.path.dirname(os.path.abspath(os.path.join(model_dir, case + '/TOMCATModel.java'))),
        'absolutefile': os.path.abspath(os.path.join(model_dir, case + '/TOMCATModel.java')),
    }
    call('/Applications/COMSOL53/Multiphysics/bin/comsol compile -jdkroot `/usr/libexec/java_home` ' + template_dict['absolutefile'], shell = True)
    batch_file.write('/Applications/COMSOL53/Multiphysics/bin/comsol batch -inputfile ' + template_dict['absolutefile'].replace('.java', '.class') + '\n')
batch_file.close()

