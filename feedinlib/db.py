from itertools import chain, groupby

from pandas import DataFrame as DF, Series, Timedelta as TD, to_datetime as tdt
from geoalchemy2.elements import WKTElement as WKTE
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sqla
import oedialect

from feedinlib import openFRED as ofr

import time


TRANSLATIONS = {
    "windpowerlib": {
        "wind_speed": [("VABS_AV",)],
        "temperature": [("T",)],
        "roughness_length": [("Z0",)],
        "pressure": [("P",)],
    },
    "pvlib": {
        "wind_speed": [("VABS_AV", 10)],
        "temp_air": [("T", 10)],
        "dhi": [("ASWDIFD_S", 0)],
        "ghi": [("ASWDIFD_S", 0), ("ASWDIR_S", 0)],
        "dni": [("ASWDIRN_S", 0)],
    },
}


def defaultdb():
    engine = getattr(defaultdb, "engine", None) or sqla.create_engine(
        "postgresql+oedialect://openenergy-platform.org"
    )
    defaultdb.engine = engine
    session = (
        getattr(defaultdb, "session", None) or sessionmaker(bind=engine)()
    )
    defaultdb.session = session
    metadata = sqla.MetaData(schema="model_draft", bind=engine, reflect=False)
    return {"session": session, "db": ofr.mapped_classes(metadata)}


class Weather:
    """ Load weather measurements from an openFRED conforming database.

    Note that you need a database storing weather data using the openFRED
    schema in order to use this class. There is one publicly available at

        https://openenergy-platform.org

    In order to access it, you need the `oedialect` Python package and the, as
    of yet unreleased, `openFRED` package. The former has some important up to
    date fixes which didn't make it into a release yet while the latter isn't
    even properly packaged yet. This means that you have to install both
    packages from source. For the `oedialect` that means you have to do

    ```
    git clone https://github.com/OpenEnergyPlatform/oedialect DIALECTSOURCE
    cd DIALECTSOURCE
    pip install .
    ```

    For `openFRED` you can simply download the `openFRED.py` file from

        https://raw.githubusercontent.com/open-fred/cli/master/openFRED.py

    and put in the directory from which you'll run your scripts. Then the file
    is importable and things should work fine.


    Once you did this, you can simply instantiate a `Weather` object via e.g.:

    ```
    from shapely.geometry import Point

    point = Point(9.7311, 53.3899)
    weather = Weather(
        "2003-04-05 06:00",
        "2003-04-05 07:31",
        [point],
        [10],
        "pvlib",
        **defaultdb()
    )
    ```

    Instead of the special values `"pvlib"` and `"windpowerlib"` you can
    also supply a list of variables, like e.g. `["P", "T", "Z0"]`, to
    retrieve from the database.

    After initialization, you can use e.g. `weather.df(point, "pvlib")`
    to retrieve a `DataFrame` with weather data from the measurement
    location closest to the given `point`.

    Parameters
    ----------
    start : Anything `pandas.to_datetime` can convert to a timestamp
        Load weather data starting from this date.
    stop : Anything `pandas.to_datetime` can convert to a timestamp
        Don't load weather data before this date.
    locations : list of `shapely.geometry.Point`s
        Weather measurements are collected from measurement locations closest
        to the the given points.
    heights : list of numbers
        Limit selected timeseries to these heights. If `variables` contains a
        variable which isn't height dependent, i.e. it has only one height,
        namely `0`, the corresponding timeseries is always
        selected. Don't select the correspoding variable, in order to avoid
        this.
        Defaults to `None` which means no restriction on height levels.
    variables : list of str or one of "pvlib" or "windpowerlib"
        Load the weather variables specified in the given list, or the
        variables necessary to calculate a feedin using `"pvlib"` or
        `"windpowerlib"`.
        Defaults to `None` which means no restriction on loaded variables.
    regions : list of `shapely.geometry.Polygon`s
         Weather measurements are collected from measurement locations
         contained within the given polygons.
    session : `sqlalchemy.orm.Session`
    db : dict of mapped classes
    """

    def __init__(
        self,
        start,
        stop,
        locations,
        heights=None,
        variables=None,
        regions=None,
        session=None,
        db=None,
    ):
        self.session = session
        self.db = db

        variables = {
            "windpowerlib": ["P", "T", "VABS_AV", "Z0"],
            "pvlib": ["ASWDIFD_S", "ASWDIRN_S", "ASWDIR_S", "T", "VABS_AV"],
            None: variables
        }[variables if variables in ["pvlib", "windpowerlib"] else None]

        self.locations = (
            {(l.x, l.y): self.location(l) for l in locations}
            if locations is not None
            else {}
        )
        self.regions = (
            {WKTE(r, srid=4326): self.within(r) for r in regions}
            if regions is not None
            else {}
        )

        location_ids = [
            l.id
            for l in chain(self.locations.values(), *self.regions.values())
        ]
        series = sorted(
            session.query(
                db["Series"], db["Variable"], db["Timespan"], db["Location"]
            )
            .join(db["Series"].variable)
            .join(db["Series"].timespan)
            .join(db["Series"].location)
            .filter((db["Series"].location_id.in_(location_ids)))
            .filter(
                None
                if variables is None
                else db["Variable"].name.in_(variables)
            )
            .filter(
                None
                if heights is None
                else (db["Series"].height.in_(chain([0], heights)))
            )
            .filter(
                (db["Timespan"].stop >= tdt(start))
                & (db["Timespan"].start <= tdt(stop))
            )
            .all(),
            key=lambda p: (
                p[3].id,
                p[1].name,
                p[0].height,
                p[2].start,
                p[2].stop,
            ),
        )

        self.series = {
            k: [
                (segment_start, segment_stop, value)
                for (series, variable, timespan, location) in g
                for (segment, value) in zip(timespan.segments, series.values)
                for segment_start in [tdt(segment[0])]
                for segment_stop in [tdt(segment[1])]
                if segment_start >= tdt(start) and segment_stop <= tdt(stop)
            ]
            for k, g in groupby(
                series, key=lambda p: (p[3], p[1].name, p[0].height,)
            )
        }

        self.variables = {
            k: sorted(set(h for _, h in g))
            for k, g in groupby(
                sorted((name, height) for _, name, height in self.series),
                key=lambda p: p[0],
            )
        }
        self.variables = {k: {"heights": v} for k, v in self.variables.items()}

    def location(self, point=None):
        """ Get the measurement location closest to the given `point`.
        """
        point = WKTE(point.to_wkt(), srid=4326)
        return (
            self.session.query(self.db["Location"])
            .order_by(self.db["Location"].point.distance_centroid(point))
            .first()
        )

    def within(self, region=None):
        """ Get all measurement locations within the given `region`.
        """
        region = WKTE(region.to_wkt(), srid=4326)
        return (
            self.session.query(self.db["Location"])
            .filter(self.db["Location"].point.ST_Within(region))
            .all()
        )

    def df(self, location=None, lib=None):
        xy = (location.x, location.y)
        point = (
            self.locations[xy]
            if xy in self.locations
            else self.location(location)
        )
        if format is None:
            raise NotImplementedError(
                "Arbitrary dataframes not supported yet.\n"
                'Please use one of `lib="pvlib"` or `lib="windpowerlib"`.'
            )
        index = (
            [
                dhi[0] + (dhi[1] - dhi[0]) / 2
                for dhi in self.series[point, "ASWDIFD_S", 0]
            ]
            if lib == "pvlib"
            else [
                wind_speed[0]
                for wind_speed in self.series[
                    point, "VABS_AV", self.variables["VABS_AV"]["heights"][0]
                ]
            ]
            if lib == "windpowerlib"
            else []
        )

        def to_series(v, h):
            s = self.series[point, v, h]
            return Series([p[2] for p in s], index=[p[0] for p in s])

        series = {
            k: sum(to_series(*p, *k[1:]) for p in TRANSLATIONS[lib][k[0]])
            for k in (
                [("dhi",), ("dni",), ("ghi",), ("temp_air",), ("wind_speed",)]
                if lib == "pvlib"
                else [
                    (v, h)
                    for v in [
                        "pressure",
                        "roughness_length",
                        "temperature",
                        "wind_speed",
                    ]
                    for h in self.variables[TRANSLATIONS[lib][v][0][0]][
                        "heights"
                    ]
                ]
                if lib == "windpowerlib"
                else [(v,) for v in self.variables]
            )
        }
        if lib == "pvlib":
            series[("temp_air",)] = (
                (series[("temp_air",)] - 273.15)
                .resample("15min")
                .interpolate()[series[("dhi",)].index]
            )
            ws = series[("wind_speed",)]
            for k in series[("wind_speed",)].keys():
                ws[k + TD("15min")] = ws[k]
            ws.sort_index(inplace=True)
        if lib == "windpowerlib":
            roughness = TRANSLATIONS[lib]["roughness_length"][0][0]
            series.update(
                {
                    ("roughness_length", h): series["roughness_length", h]
                    .resample("30min")
                    .interpolate()[index]
                    for h in self.variables[roughness]["heights"]
                }
            )
            series.update({k: series[k][index] for k in series})
        return DF(index=index, data={k: series[k].values for k in series})


if __name__ == "__main__":
    from shapely.geometry import Point
    from geoalchemy2.shape import to_shape
    import os
    import geopandas as gpd
    import pandas as pd

    modus = 'points'  # 'points' or 'region'
    # modus = 'region'  # 'points' or 'region'

    years = [2015, 2016]

    path_to_server = '/home/sabine/rl-institut'
    weather_data_path = path_to_server + '/04_Projekte/163_Open_FRED/03-Projektinhalte/AP7 Community/paper_data/weather_data'

    if modus == 'points':
        coordinates = [[53.128206, 12.114433], [51.785053, 14.456623],
                       [52.564506, 13.724137]
                       ]

        points = [Point(co[1], co[0]) for co in coordinates]
        locations = points
        regions = None
    elif modus == 'region':
        # get region file
        path = '/home/sabine/rl-institut/04_Projekte/163_Open_FRED/03-Projektinhalte/AP7 Community/paper_data/geometries/'
        filename = os.path.join(path, 'germany', 'germany_nuts_1.geojson')
        germany = gpd.read_file(filename)
        berlin = germany[germany['nuts'] == 'DE300']
        regions = berlin.iloc[0]['geometry']
        locations = None

    for year in years:
        start = time.time()
        weather = Weather(
            start="{}-01-01 00:00".format(year),
            stop="{}-12-31 23:59".format(year),
            locations=locations,
            heights=None,
            variables="windpowerlib",
            regions=regions,
            **defaultdb()
        )
        end = time.time()
        print('Time {}'.format(end - start))

        if modus == 'region':
            dfs = [[weather.df(to_shape(location.point), "windpowerlib")
                    for location in locations]
                   for locations in weather.regions.values()]
            # for df in dfs:
            print('weather.region.values():')
            print(weather.regions.values())
            print('Länge dfs: {}'.format(len(dfs)))
            print('Länge dfs[0]: {}'.format(len(dfs[0])))
            print('Länge dfs[0][0]: {}'.format(len(dfs[0][0])))

            try:
                print(len(dfs[1]))
            except:
                print('no 1')

        elif modus == 'points':
            weather_dfs = [weather.df(to_shape(location.point), "windpowerlib")
                    for location in weather.locations.values()]
            weather_df = pd.DataFrame()
            for df, location in zip(weather_dfs, weather.locations.values()):
                df['lat'] = to_shape(location.point).y
                df['lon'] = to_shape(location.point).x
                df.index = pd.MultiIndex.from_frame(
                    df[['lat', 'lon']].reset_index())
                df.drop(['lat', 'lon'], axis=1, inplace=True)
                weather_df = pd.concat([weather_df, df], axis=0)
                weather_df.rename_axis(index=['time', 'lat', 'lon'],
                                       inplace=True)
                filename = os.path.join(weather_data_path,
                                        'open_fred_wind_lib_val_{}.csv'.format(
                                            year))
                weather_df.to_csv(filename)
                # print(weather_df)


