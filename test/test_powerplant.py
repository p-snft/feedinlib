from feedinlib import WindPowerPlant, Photovoltaic
from feedinlib.models import WindpowerlibTurbine, Pvlib, \
    WindpowerlibTurbineCluster
import pandas as pd
import math


def test_weather_pvlib():
    """
    returns a test weather object to use in pvlib tests
    """
    return pd.DataFrame(data={'wind_speed': [5.0],
                              'temp_air': [10.0],
                              'dhi': [150.0],
                              'ghi': [300]},
                        index=pd.date_range('1/1/1970 12:00',
                                            periods=1, tz='UTC'))


def test_weather_windpowerlib():
    """
    returns a test weather object to use in windpowerlib tests
    """
    return pd.DataFrame(data={('wind_speed', 10): [5.0],
                              ('temperature', 2): [270.0],
                              ('roughness_length', 0): [0.15],
                              ('pressure', 0): [98400.0]},
                        index=pd.date_range('1/1/1970 12:00',
                                            periods=1, tz='UTC'))


def test_pv_system():
    """
    returns a test pv system
    """
    return {'module_name': 'Yingli_YL210__2008__E__',
            'inverter_name': 'ABB__MICRO_0_25_I_OUTD_US_208_208V__CEC_2014_',
            'azimuth': 180,
            'tilt': 30,
            'albedo': 0.2}


def test_windpowerlib_turbine():
    """
    returns a test windpowerlib turbine
    """
    return {'turbine_type': 'E-82/3000',
            'hub_height': 135,
            'power_curve': True}


def test_windpowerlib_turbine_2():
    """
    returns a test windpowerlib turbine with optional parameters
    """
    return {'turbine_type': 'V90/2000',
            'hub_height': 120,
            'rotor_diameter': 80,
            'power_curve': True}


def test_windpowerlib_farm():
    """
    returns a test windpowerlib wind farm
    """
    return {'wind_turbine_fleet': [
        {'wind_turbine': test_windpowerlib_turbine(),
         'number_of_turbines': 6},
        {'wind_turbine': test_windpowerlib_turbine_2(),
         'number_of_turbines': 3}]
    }


def test_windpowerlib_farm_2():
    """
    returns a test windpowerlib wind farm
    """
    return {'wind_turbine_fleet': [
        {'wind_turbine': test_windpowerlib_turbine(),
         'number_of_turbines': 1}]
    }


def test_windpowerlib_turbine_cluster():
    """
    returns a test windpowerlib wind turbine cluster
    """
    return {'wind_farms': [test_windpowerlib_farm(),
                           test_windpowerlib_farm_2()]}


def test_basic_pvlib_feedin():
    """
    test basic feedin calculation using pvlib

    """
    test_module = Photovoltaic(**test_pv_system())
    feedin = test_module.feedin(weather=test_weather_pvlib(),
                                location=(52, 13))
    if math.isclose(feedin.values[0], 143.28844, abs_tol=0.00001):
        print('passed')
    else:
        print('failed')


def test_basic_pvlib_feedin_with_surface_type():
    """
    test basic feedin calculation using pvlib and supplying an optional
    pv system parameter

    """
    test_module = test_pv_system()
    del test_module['albedo']
    test_module['surface_type'] = 'grass'
    test_module = Photovoltaic(**test_module)
    feedin = test_module.feedin(weather=test_weather_pvlib(),
                                location=(52, 13))
    if math.isclose(feedin.values[0], 143.28844, abs_tol=0.00001):
        print('passed')
    else:
        print('failed')


def test_basic_pvlib_feedin_with_optional_pp_parameter():
    """
    test basic feedin calculation using pvlib and supplying an optional
    pv system parameter

    """
    test_module = test_pv_system()
    test_module['strings_per_inverter'] = 2
    test_module = Photovoltaic(**test_module)
    feedin = test_module.feedin(weather=test_weather_pvlib(),
                                location=(52, 13))
    # power output is in this case limited by the inverter, which is why
    # power output with 2 strings is not twice as high as power output of one
    # string
    if math.isclose(feedin.values[0], 250.0, abs_tol=0.00001):
        print('passed')
    else:
        print('failed')


def test_basic_windpowerlib_single_turbine_feedin():
    """
    test basic feedin calculation using windpowerlib single turbine

    """
    test_turbine = WindPowerPlant(**test_windpowerlib_turbine())
    feedin = test_turbine.feedin(weather=test_weather_windpowerlib())
    if math.isclose(feedin.values[0], 833050.32551, abs_tol=0.00001):
        print('passed')
    else:
        print('failed')


def test_basic_windpowerlib_single_turbine_feedin_with_optional_pp_parameter():
    """
    test basic feedin calculation using windpowerlib single turbine and using
    optional parameters for power plant and modelchain

    """
    test_turbine = test_windpowerlib_turbine()
    test_turbine['rotor_diameter'] = 82
    test_turbine['power_coefficient_curve'] = True
    test_turbine = WindPowerPlant(**test_turbine)
    feedin = test_turbine.feedin(weather=test_weather_windpowerlib(),
                                 power_output_model='power_coefficient_curve')
    if math.isclose(feedin.values[0], 847665.85209, abs_tol=0.00001):
        print('passed')
    else:
        print('failed')


def test_missing_powerplant_parameter():
    """
    test if initialization fails in case of missing power plant parameter

    """
    test_module = test_pv_system()
    del(test_module['albedo'])
    try:
        Photovoltaic(**test_module)
        print('failed')
    except:
        print('passed')


def test_powerplant_requirements():
    """
    test that attribute error is not raised in case a valid model is specified
    when calling feedin method

    """
    test_module = Photovoltaic(**test_pv_system())
    feedin = test_module.feedin(weather=test_weather_pvlib(),
                                model=Pvlib,
                                location=(52, 13))
    if math.isclose(feedin.values[0], 143.28844, abs_tol=0.00001):
        print('passed')
    else:
        print('failed')


def test_powerplant_requirements_2():
    """
    test that attribute error is raised in case required power plant parameters
    are missing when feedin is called with a different model than initially
    specified

    """
    test_module = Photovoltaic(**test_pv_system())
    try:
        test_module.feedin(weather=test_weather_pvlib(),
                           model=WindpowerlibTurbine,
                           location=(52, 13))
        print('failed')
    except:
        print('passed')


def test_pv_feedin_scaling():
    """
    test if pv feedin timeseries are scaled correctly

    """
    test_module = Photovoltaic(**test_pv_system())
    feedin = test_module.feedin(
        weather=test_weather_pvlib(),
        location=(52, 13), scaling='peak_power', scaling_value=10)
    if math.isclose(feedin.values[0], 6.74616, abs_tol=0.00001):
        print('passed')
    else:
        print('failed')
    feedin = test_module.feedin(
        weather=test_weather_pvlib(),
        location=(52, 13), scaling='area', scaling_value=10)
    if math.isclose(feedin.values[0], 842.87318, abs_tol=0.00001):
        print('passed')
    else:
        print('failed')


def test_wind_feedin_scaling():
    """
    test if pv feedin timeseries are scaled correctly

    """
    test_turbine = WindPowerPlant(**test_windpowerlib_turbine())
    feedin = test_turbine.feedin(weather=test_weather_windpowerlib(),
                                 scaling='number', scaling_value=2)
    if math.isclose(feedin.values[0], 2 * 833050.32551, abs_tol=0.00001):
        print('passed')
    else:
        print('failed')

    feedin = test_turbine.feedin(weather=test_weather_windpowerlib(),
                                 scaling='capacity', scaling_value=2e6)
    if math.isclose(feedin.values[0], 2 / 3.02 * 833050.32551,
                    abs_tol=0.00001):
        print('passed')
    else:
        print('failed')


def test_windpowerlib_windfarm_init():
    try:
        # turbines as dict
        test_farm = test_windpowerlib_farm()
        WindPowerPlant(**test_farm, model=WindpowerlibTurbineCluster)
        # turbines as WindPowerPlant objects (turbines are already
        # WindPowerPlant objects due to use in previous init)
        WindPowerPlant(**test_farm, model=WindpowerlibTurbineCluster)
        print('passed')
    except:
        print('failed')


def test_windpowerlib_turbine_cluster_init():
    try:
        # turbines as dict
        test_cluster = test_windpowerlib_turbine_cluster()
        WindPowerPlant(**test_cluster, model=WindpowerlibTurbineCluster)
        # turbines as WindPowerPlant objects (turbines are already
        # WindPowerPlant objects due to use in previous init)
        WindPowerPlant(**test_cluster, model=WindpowerlibTurbineCluster)
        print('passed')
    except:
        print('failed')


def test_windpowerlib_windfarm_feedin():
    """
    test basic feedin calculation using windpowerlib wind turbine cluster
    modelchain for a wind farm

    """
    farm = WindPowerPlant(**test_windpowerlib_farm(),
                          model=WindpowerlibTurbineCluster)
    feedin = farm.feedin(weather=test_weather_windpowerlib(),
                         wake_losses_model=None)
    if math.isclose(feedin.values[0], 7659079.07202, abs_tol=0.00001):
        print('passed')
    else:
        print('failed')


def test_windpowerlib_turbine_cluster_feedin():
    """
    test basic feedin calculation using windpowerlib wind turbine cluster
    modelchain for a wind turbine cluster

    """
    test_cluster = WindPowerPlant(**test_windpowerlib_turbine_cluster(),
                                  model=WindpowerlibTurbineCluster)
    feedin = test_cluster.feedin(weather=test_weather_windpowerlib())
    if math.isclose(feedin.values[0], 7285198.61376, abs_tol=0.00001):
        print('passed')
    else:
        print('failed')


def test_windpowerlib_windfarm_feedin_with_optional_parameters():
    """
    test basic feedin calculation using windpowerlib wind turbine cluster
    modelchain and supplying an optional power plant and modelchain parameter

    """

    # test optional parameter
    test_farm = test_windpowerlib_farm()
    test_farm['efficiency'] = 0.9
    farm = WindPowerPlant(**test_farm, model=WindpowerlibTurbineCluster)
    feedin = farm.feedin(weather=test_weather_windpowerlib(),
                         wake_losses_model='constant_efficiency')
    if math.isclose(feedin.values[0], 6893171.16482, abs_tol=0.00001):
        print('passed')
    else:
        print('failed')


def test_windpowerlib_turbine_equals_windfarm():
    """
    test if wind turbine feedin calculation yields the same as wind farm
    calculation with one turbine

    """
    # turbine feedin
    test_turbine = WindPowerPlant(**test_windpowerlib_turbine())
    feedin = test_turbine.feedin(weather=test_weather_windpowerlib())
    # farm feedin
    test_farm = {'wind_turbine_fleet': [
        {'wind_turbine': test_turbine,
         'number_of_turbines': 1}]}
    test_farm = WindPowerPlant(**test_farm, model=WindpowerlibTurbineCluster)
    feedin_farm = test_farm.feedin(weather=test_weather_windpowerlib(),
                                   wake_losses_model=None)

    if math.isclose(feedin.values[0], feedin_farm.values[0], abs_tol=0.00001):
        print('passed')
    else:
        print('failed')


def test_windpowerlib_windfarm_equals_cluster():
    """
    test if windfarm feedin calculation yields the same as turbine cluster
    calculation with one wind farm

    """
    # farm feedin
    test_farm = test_windpowerlib_farm()
    test_farm = WindPowerPlant(**test_farm, model=WindpowerlibTurbineCluster)
    feedin_farm = test_farm.feedin(weather=test_weather_windpowerlib())
    # turbine cluster
    test_cluster = {'wind_farms': [test_windpowerlib_farm()]}
    test_cluster = WindPowerPlant(**test_cluster,
                                  model=WindpowerlibTurbineCluster)
    feedin_cluster = test_cluster.feedin(weather=test_weather_windpowerlib())

    if math.isclose(feedin_cluster.values[0], feedin_farm.values[0],
                    abs_tol=0.00001):
        print('passed')
    else:
        print('failed')


test_basic_pvlib_feedin()
test_basic_pvlib_feedin_with_surface_type()
test_basic_pvlib_feedin_with_optional_pp_parameter()
test_basic_windpowerlib_single_turbine_feedin()
test_basic_windpowerlib_single_turbine_feedin_with_optional_pp_parameter()
test_missing_powerplant_parameter()
test_powerplant_requirements()
test_powerplant_requirements_2()
test_pv_feedin_scaling()
test_wind_feedin_scaling()
test_windpowerlib_windfarm_init()
test_windpowerlib_turbine_cluster_init()
test_windpowerlib_windfarm_feedin()
test_windpowerlib_turbine_cluster_feedin()
test_windpowerlib_windfarm_feedin_with_optional_parameters()
test_windpowerlib_turbine_equals_windfarm()
test_windpowerlib_windfarm_equals_cluster()