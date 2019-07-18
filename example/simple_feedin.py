from feedinlib import Photovoltaic, WindPowerPlant
from feedinlib.models import WindpowerlibTurbineCluster
import pandas as pd
import matplotlib.pyplot as plt


# ######## set up weather dataframes (temporary) #########

# set up weather dataframe for windpowerlib
weather_df_wind = pd.read_csv(
    'weather.csv', index_col=0,
    date_parser=lambda idx: pd.to_datetime(idx, utc=True))
# change type of index to datetime and set time zone
weather_df_wind.index = pd.to_datetime(weather_df_wind.index).tz_convert(
    'Europe/Berlin')
data_height = {
    'pressure': 0,
    'temperature': 2,
    'wind_speed': 10,
    'roughness_length': 0}
weather_df_wind = weather_df_wind[['v_wind', 'temp_air', 'z0', 'pressure']]
weather_df_wind.columns = [['wind_speed', 'temperature', 'roughness_length',
                            'pressure'],
                           [data_height['wind_speed'],
                            data_height['temperature'],
                            data_height['roughness_length'],
                            data_height['pressure']]]

# set up weather dataframe for pvlib
weather_df_pv = pd.read_csv(
    'weather.csv', index_col=0,
    date_parser=lambda idx: pd.to_datetime(idx, utc=True))
# change type of index to datetime and set time zone
weather_df_pv.index = pd.to_datetime(weather_df_pv.index).tz_convert(
    'Europe/Berlin')
weather_df_pv['temp_air'] = weather_df_pv.temp_air - 273.15
weather_df_pv['ghi'] = weather_df_pv.dirhi + weather_df_pv.dhi
weather_df_pv.rename(columns={'v_wind': 'wind_speed'}, inplace=True)

# # ######## single PV system #########
#
# # specify pv system
# yingli210 = {
#     'module_name': 'Yingli_YL210__2008__E__',
#     'inverter_name': 'ABB__PVI_3_0_OUTD_S_US_Z__277V__277V__CEC_2018_',
#     'azimuth': 180,
#     'tilt': 30,
#     'albedo': 0.2,
#     'modules_per_string': 4}
#
# # instantiate feedinlib Photovoltaic object
# yingli_module = Photovoltaic(**yingli210)
#
# # calculate feedin
# feedin = yingli_module.feedin(
#     weather=weather_df_pv[['wind_speed', 'temp_air', 'dhi', 'ghi']],
#     location=(52, 13), scaling='peak_power', scaling_value=10)
#
# # plot
# feedin.fillna(0).plot(title='PV feedin')
# plt.xlabel('Time')
# plt.ylabel('Power in W')
# plt.show()
#
# # ######## single wind turbine #########
#
# # specify wind turbine
# enerconE126 = {
#     'turbine_type': 'E-82/3000',  # turbine name as in register
#     'hub_height': 135,  # in m
#     'power_curve': True,
#     'nominal_power': True
#     }
#
# # instantiate feedinlib WindPowerPlant object
# e126 = WindPowerPlant(**enerconE126)
#
# # calculate feedin
# feedin = e126.feedin(weather=weather_df_wind,
#                      location=(52, 13))
# feedin_scaled = e126.feedin(weather=weather_df_wind,
#                             location=(52, 13),
#                             scaling='capacity', scaling_value=5e6)
#
# feedin_scaled.fillna(0).plot(legend=True, label='single turbine',
#                              title='Wind turbine feedin')
# feedin.fillna(0).plot(legend=True, label='scaled to 5 MW')
# plt.xlabel('Time')
# plt.ylabel('Power in W')
# plt.show()

# ######## wind cluster #########

# specify (and instantiate) wind turbines
enerconE126 = {
    'turbine_type': 'E-82/3000',  # turbine name as in register
    'hub_height': 135,  # in m
    'power_curve': True
    }
e126 = WindPowerPlant(**enerconE126)

vestasV90 = {
    'turbine_type': 'V90/2000',  # turbine name as in register
    'hub_height': 120,  # in m
    'power_curve': True
    }
v90 = WindPowerPlant(**vestasV90)

# two ways to initialize windfarms
# initialize windfarm using WindPowerPlant objects
farm1 = {'wind_turbine_fleet': [{'wind_turbine': e126,
                                'number_of_turbines': 6},
                               {'wind_turbine': v90,
                                'number_of_turbines': 3}
                               ]
         }
windfarm1 = WindPowerPlant(**farm1, model=WindpowerlibTurbineCluster)

# initialize windfarm using dicts to specify turbines
farm2 = {'wind_turbine_fleet': [{'wind_turbine': enerconE126,
                                'number_of_turbines': 2},
                               {'wind_turbine': vestasV90,
                                'number_of_turbines': 1}
                               ]
        }
windfarm2 = WindPowerPlant(**{'wind_farms': [farm1]},
                           model=WindpowerlibTurbineCluster)
# initialize wind cluster
cluster = {'wind_farms': [windfarm1, farm2]}
windcluster = WindPowerPlant(**cluster, model=WindpowerlibTurbineCluster)

feedin1 = windfarm1.feedin(weather=weather_df_wind, location=(52, 13))
feedin2 = windfarm2.feedin(weather=weather_df_wind, location=(52, 13))
feedin3 = windcluster.feedin(weather=weather_df_wind, location=(52, 13))

feedin1.fillna(0).plot(legend=True, label='Windfarm 1',
                       title='Wind cluster feedin')
feedin2.fillna(0).plot(legend=True, label='Windfarm 2')
feedin3.fillna(0).plot(legend=True, label='Wind cluster')
plt.xlabel('Time')
plt.ylabel('Power in W')
plt.show()
