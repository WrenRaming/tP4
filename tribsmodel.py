# tribsmodel.py

import numpy as np
import geopandas as gpd
import shutil
import pyproj
from shapely.geometry import LineString
from shapely.geometry import Point
from shapely.geometry import Polygon
import argparse
import pandas as pd
import os
import shutil
import subprocess
import sys
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# TODO
# geopandas for voronoi and rasterios for rasters, gdal for raster-shapefile conversions
# ideas on plotting up shapefiles--create overview with partioned reach, create plot of individual partions showing
# voronoi as shapes/
# in pre-check:
#   (1) call check if graph flag 2 or 3 is called the graph file contains the resepective reach or nodes? words in file name
#   (2) check that files actually exist...


class Model(object):
    """
    A tRIBS Model class.

    This class provides access to the underlying framework of a tRIBS (TIN-based Real-time Integrated Basin
    Simulator) simulation. It includes one nested class: Results. The Model class is initialized at the top-level to
    facilitate model setup, simultation, post-processing and can be used for mainpulating and generating multiple
    simulations in an efficient manner.

    Attributes:
        input_options (dict): A dictionary of the necessary keywords for a tRIBS .in file.
        model_input_file (str): Path to a template .in file with the specified paths for model results, inputs, etc.

    Methods:
         __init__(self, model_input_file):  # Constructor method
            :param model_input_file: Path to a template .in file.
            :type param1: str

        create_input(self):
             Creates a dictionary with tRIBS input options assigne to attribute input_options.

        get_input_var(self, var):
            Read variable specified by var from .in file.
            :param var: A keyword from the .in file.
            :type var: str
            :return: the line following the keyword argument from the .in file.
            :rtype: str

        read_node_list(self,file_path):
            Returns node list provide by .dat file.
            :param file_path: Relative or absolute file path to .dat file.
            :type file_path: str
            :return: List of nodes specified by .dat file
            :rtype: list

        def convert_to_datetime(starting_date):
            Returns a pandas date-time object.
            :param starting_date: The start date of a given model simulation, note needs to be in tRIBS format.
            :type starting_date: str
            :return: A pandas Timestamp object.

    Example:
        Provide an example of how to create and use an instance of this class
        >>> from tribsmodel import Model
        >>> m = Model('/path/to/.in')
    """

    def __init__(self):
        # attributes
        self.options = None  # input options for tRIBS model run
        self.descriptor_files = {}  # dict to store descriptor files
        self.grid_data_files = {}  # dict to store .gdf files
        self.create_input()
        self.geo = {"UTM_Zone": None, "EPSG": None, "Projection": None}

        # nested classes
        self.Results = Results(self)

    # SIMULATION METHODS
    def create_graph_files(
            self):  # TODO make it so you can run meshbuilder, and same functionality as pearl scripts, and ksh scripts but using python
        pass

    def precheck(self):
        """
        """
        pass


    @staticmethod
    def run(executable, input_file, mpi_command=None, tribs_flags=None, log_path=None,
            store_input=None, timeit=True):
        """
        Run a tRIBS model simulation with optional arguments.

        Run_simulation assumes that if relative paths are used then the binary and input file are collocated in the
        same directory. That means for any keywords that depend on a relative path, must be specified from the directory
        the tRIBS binary is executed. You can pass the location of the input file and executable as paths, in which case
        the function copies the binary and input file to same directory and then deletes both after the model run is complete.
        Optional arguments can be passed to store

        Args:
            binary_path (str): The path to the binary model executable.
            control_file_path (str): The path to the input control file for the binary.
            optional_args (str): Optional arguments to pass to the binary.

        Returns:
            int: The return code of the binary model simulation.
        """
        if mpi_command is not None:
            command = mpi_command.split()
            command.extend([executable, input_file])
        else:
            command = [executable, input_file]

        if tribs_flags is not None:
            command.extend(tribs_flags.split())

        if log_path is not None:
            command.append(log_path)

        if timeit:
            command.insert(0, "time")

        print(command)

        subprocess.run(command)

    @staticmethod
    def build(source_file, build_directory, verbose=True, exe="tRIBS", parallel="ON", cxx_flags="-O2"):
        """
        Run a tRIBS model simulation with optional arguments.

        Run_simulation assumes that if relative paths are used then the binary and input file are collocated in the
        same directory. That means for any keywords that depend on a relative path, must be specified from the directory
        the tRIBS binary is executed. You can pass the location of the input file and executable as paths, in which case
        the function copies the binary and input file to same directory and then deletes both after the model run is complete.
        Optional arguments can be passed to store

        Args:
            binary_path (str): The path to the binary model executable.
            control_file_path (str): The path to the input control file for the binary.
            optional_args (str): Optional arguments to pass to the binary.

        Returns:
            int: The return code of the binary model simulation.
        """
        # TODO: add check if build directory already exists, prompt user if they want to remove
        if os.path.exists(build_directory):
            print(f"The directory '{build_directory}' exists.")
            user_input = input("Would you like to remove it? [y/n]: ")
            if user_input:
                try:
                    # Remove the directory and its contents
                    shutil.rmtree(build_directory)
                    print(f"Directory '{build_directory}' and its contents have been removed.")
                except FileNotFoundError:
                    print(f"Directory '{build_directory}' does not exist.")
                except PermissionError:
                    print(f"Permission denied while attempting to remove '{build_directory}'.")
                except Exception as e:
                    print(f"An error occurred: {str(e)}")

        # Allow modification of CMakeList.txt
        modified_lines = []
        source_file = os.path.expanduser(source_file)
        file_path = os.path.join(source_file, "CMakeLists.txt")

        # Define the variables to search for and their corresponding replacements
        variables_to_replace = {
            "exe": exe,
            "parallel": parallel,
            "cxx_flags": cxx_flags
        }

        # Read the contents of the CMakeLists.txt file and modify lines as needed
        with open(file_path, 'r') as file:
            for line in file:
                for variable, value in variables_to_replace.items():
                    if line.strip().startswith(f'set({variable} "'):
                        line = f'set({variable} "{value}")\n'
                modified_lines.append(line)

        # Write the modified lines back to the file
        with open(file_path, 'w') as file:
            file.writelines(modified_lines)

        if verbose:
            cmake_configure_command = ["cmake", "-B", build_directory, "-S", source_file]
            subprocess.run(cmake_configure_command)

            cmake_build_command = ["cmake", "--build", build_directory, "--target", "all"]
            result = subprocess.run(cmake_build_command)
        else:
            cmake_configure_command = ["cmake", "-B", build_directory, "-S", source_file]
            subprocess.run(cmake_configure_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            cmake_build_command = ["cmake", "--build", build_directory, "--target", "all"]
            result = subprocess.run(cmake_build_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return result.returncode

    def clean(self):
        pass

    def check_paths(self):
        data = self.options  # Assuming m.options is a dictionary with sub-dictionaries
        exists = []
        doesnt = []

        # Filter sub-dictionaries where "io" is in the "tags" list
        result = [item for item in data.values() if any('io' in tag for tag in item.get("tags", []))]

        # Display the filtered sub-dictionaries
        for item in result:
            if item["value"] is not None:
                flag = os.path.exists(item["value"])
                if flag:
                    exists.append(item)
                else:
                    doesnt.append(item)

        print("\nThe following tRIBS inputs do not have paths that exist: \n")
        for item in doesnt:
            print(item["key_word"]+" "+item["describe"])

        print("...\n...\n...\n")

        print("Checking if station descriptor paths exist.\n")
        rain = self.read_precip_sdf()
        print("...\n...\n...\n")

        flags = []
        if rain is not None:
            for station in rain:
                flag = os.path.exists(station["file_path"])
                if not flag:
                    print({station["file_path"]} + " does not exist")
                    flags.append(flag)
            if all(flags):
                print("All rain gauge paths exist.")
        else:
            print("No rain gauges are specified.")

        met = self.read_met_sdf()
        print("...\n...\n...\n")

        flags = []
        if met is not None:
            for station in met:
                flag = os.path.exists(station["file_path"])
                if not flag:
                    print({station["file_path"]} + " does not exist")

                if all(flags):
                    print("All met station paths exist.")
        else:
            print("No met stations are specified.")



    # I/O METHODS
    @staticmethod
    def read_node_list(file_path):
        """
        Returns node list provide by .dat file.

        The node list can be further modified or used for reading in element/pixel files and subsequent processing.

        :param file_path: Relative or absolute file path to .dat file.
        :type file_path: str
        :return: List of nodes specified by .dat file
        :rtype: list

        Example:
            >>> from tribsmodel import Model
            >>> m = Model('/path/to/.in')
            >>> node_list = m.read_node_list(m.input_options['nodeoutputlist'])
        """
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()

            # Initialize an empty list to store the IDs
            node_ids = []

            # Check if the file is empty or has invalid content
            if not lines:
                return node_ids

            # Parse the first column as the size of the array
            size = int(lines[0].strip())

            # Extract IDs from the remaining lines
            for line in lines[1:]:
                id_value = line.strip()
                node_ids.append(id_value)

            # Ensure the array has the specified size
            if len(node_ids) != size:
                print("Warning: Array size does not match the specified size in the file.")

            return node_ids
        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found.")
            return []

    @staticmethod
    def convert_to_datetime(starting_date):
        """
        Returns a pandas date-time object.

        :param starting_date: The start date of a given model simulation, note needs to be in tRIBS format.
        :type starting_date: str
        :rtupe: A pandas Timestamp object
        """
        month = int(starting_date[0:2])
        day = int(starting_date[3:5])
        year = int(starting_date[6:10])
        minute = int(starting_date[11:13])
        second = int(starting_date[14:16])
        date = pd.Timestamp(year=year, month=month, day=day, minute=minute)
        return date

    def read_input_file(self, file_path):
        """
        Updates input_options with specified input file.
        """
        with open(file_path, 'r') as file:
            lines = file.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()  # Remove leading/trailing whitespace
            for key in self.options.keys():
                # Convert key to lowercase for case-insensitive comparison
                key_lower = key.lower()
                # Convert line to lowercase for case-insensitive comparison
                line_lower = line.lower()
                if line_lower.startswith(key_lower):
                    # Extract the portion of the line after the key
                    if i + 1 < len(lines):
                        # Extract the value from the next line
                        value = lines[i + 1].strip()
                        self.options[key]['value'] = value
            i += 1

    def write_input_file(self, output_file_path):
        with open(output_file_path, 'w') as output_file:
            for key, subdict in self.options.items():
                if "key_word" in subdict and "value" in subdict:
                    keyword = subdict["key_word"]
                    value = subdict["value"]
                    output_file.write(f"{keyword}\n")
                    output_file.write(f"{value}\n\n")

    def add_descriptor_files(self):
        self.descriptor_files.update({"precip": self.read_precip_sdf()})
        self.descriptor_files.update({"met": self.read_met_sdf()})

    def read_precip_sdf(self, file_path=None):
        if file_path is None:
            file_path = self.options["gaugestations"]["value"]

            if file_path is None:
                #print(self.options["gaugestations"]["key_word"] + "is not specified.")
                return None

        station_list = []

        with open(file_path, 'r') as file:
            lines = file.readlines()

        if len(lines) != 2:
            print("Error: Number of lines does not match the expected count (2).")
            return None

        num_stations, num_parameters = map(int, lines[0].strip().split())

        line = lines[1]
        station_info = line.strip().split()
        if len(station_info) == 7:
            station_id, file_path, lat, long, record_length, num_params, elevation = station_info
            station = {
                "station_id": station_id,
                "file_path": file_path,
                "y": float(lat),
                "x": float(long),
                "record_length": int(record_length),
                "num_parameters": int(num_params),
                "elevation": float(elevation)
            }
            station_list.append(station)

        elif len(station_list) != num_stations:
            print("Error: Number of stations does not match the specified count.")
            return None

        return station_list

    def read_precip_file(self, file_path):
        # TODO add var for specifying Station ID

        # Initialize empty lists to store datetime and precipitation rate data
        datetime_vector = []
        precip_rate_vector = []

        # Open the file and read it line by line
        with open(file_path, 'r') as file:
            # Skip the header line if it exists
            next(file, None)

            for line in file:
                # Split the line into individual values using whitespace as the delimiter
                values = line.strip().split()

                # Check if there are enough values for date and time (Year, Month, Day, Hour) and precipitation rate
                if len(values) >= 5:
                    year, month, day, hour, precip_rate = values[:5]

                    # Combine the date and time components to create a datetime object
                    date_time = f"{year}-{month}-{day} {hour}:00:00"

                    # Append the datetime and precipitation rate to their respective lists
                    datetime_vector.append(date_time)
                    precip_rate_vector.append(float(precip_rate))

        # Display the first few elements of the datetime and precipitation rate vectors
        for i in range(min(5, len(datetime_vector))):
            print(f"Datetime: {datetime_vector[i]}, Precipitation Rate: {precip_rate_vector[i]}")

        return datetime_vector, precip_rate_vector

    def write_precip_station(self):
        pass

    def read_met_sdf(self, file_path=None):
        if file_path is None:
            file_path = self.options["hydrometstations"]["value"]

            if file_path is None:
                #print(self.options["hydrometstations"]["key_word"] + "is not specified.")
                return None

        station_list = []

        with open(file_path, 'r') as file:
            lines = file.readlines()

        if len(lines) != 2:
            print("Error: Number of lines does not match the expected count (2).")
            return None

        num_stations, num_parameters = map(int, lines[0].strip().split())
        line = lines[1]
        station_info = line.strip().split()

        if len(station_info) == 10:
            station_id, file_path, lat, y, long, x, gmt, record_length, num_params, other = station_info
            station = {
                "station_id": station_id,
                "file_path": file_path,
                "lat_dd": float(lat),
                "x": float(x),
                "long_dd": float(long),
                "y": float(y),
                "GMT": int(gmt),
                "record_length": int(record_length),
                "num_parameters": int(num_params),
                "other": other
            }
            station_list.append(station)

        elif len(station_list) != num_stations:
            print("Error: Number of stations does not match the specified count.")
            return None

        return station_list

    def write_met_station(self):
        pass

    def read_soil_table(self):
        pass

    def write_soil_table(self):
        pass

    def read_landuse_table(self):
        pass

    def write_landuse_table(self):
        pass

    # Visualize model domain:
    def read_reach_file(self, filename=None):

        if filename is None:
            filename = self.options["outfilename"]["value"] + "_reach"

        with open(filename, 'r') as file:
            lines = file.readlines()

        features = []
        current_id = None
        coordinates = []

        for line in lines:
            line = line.strip()
            if line == "END":
                if current_id is not None:
                    line_string = LineString(coordinates)
                    features.append({"ID": current_id, "geometry": line_string})
                    current_id = None
                    coordinates = []
            else:
                if current_id is None:
                    current_id = int(line)
                else:
                    x, y = map(float, line.split(','))
                    coordinates.append((x, y))
        if self.geo["EPSG"] is not None:
            gdf = gpd.GeoDataFrame(features, crs=self.geo["EPSG"])
        else:
            gdf = gpd.GeoDataFrame(features)
            print("Coordinate Reference System (CRS) was not added to the GeoDataFrame")

        return gdf

    def read_voi_file(self, filename=None):

        if filename is None:
            filename = self.options["outfilename"]["value"] + "_voi"

        ids = []
        polygons = []
        if os.path.exists(filename):
            with open(filename, 'r') as file:
                current_id = None
                current_points = []

                for line in file:
                    line = line.strip()
                    if line == "END":
                        if current_id is not None:
                            ids.append(current_id)
                            if len(current_points) >= 3:
                                polygons.append(Polygon(current_points))
                            current_id = None
                            current_points = []
                    else:
                        parts = line.split(',')
                        if len(parts) == 3:
                            id_, x, y = map(float, parts)
                            current_id = id_
                            current_points.append((x, y))
                        elif len(parts) == 2:
                            x, y = map(float, parts)
                            current_points.append((x, y))

            if not ids or not polygons:
                raise ValueError("No valid data found in " + filename)

            features = {'ID': ids, 'geometry': polygons}

            if self.geo["EPSG"] is not None:
                gdf = gpd.GeoDataFrame(features, crs=self.geo["EPSG"])
            else:
                gdf = gpd.GeoDataFrame(features)
                print("Coordinate Reference System (CRS) was not added to the GeoDataFrame")

            return gdf
        else:
            print("Voi file not found.")
            return None

    # CONSTRUCTOR AND BASIC I/O FUNCTIONS
    def print_tags(self, tag_name):

        data = self.options  # Assuming m.options is a dictionary with sub-dictionaries

        # Filter sub-dictionaries where "io" is in the "tags" list
        result = [item for item in data.values() if any(tag_name in tag for tag in item.get("tags", []))]

        # Display the filtered sub-dictionaries
        for item in result:
            print(item)

    def create_input(self):
        """
        Creates a dictionary with tRIBS input options assigne to attribute input_options.

        This function loads a dictionary of the necessary variables for a tRIBS input file. And is called upon
        initialization. The dictionary is assigned as instance variable:input_options to the Class Simulation. Note
        the templateVars file will need to be udpated if additional keywords are added to the .in file.

        Each subdictionary has a tags key. With the tag indicating the role of the given option or variable in the model
        simulation.

        Tags:
            time    - set parameters related to model simulation times and time steps
            opts    - enable diffrent model options, modules, and functions
            physical    - set physical parameters
            io    - input and output variables i.e. paths to input files or outputfiles
            restart    - suite of options and variables related to tRIBS restart feature
            parallel    - suite of options and variables related to tRIBS parallelization
            deprecated    - deprecated or untested options

        Example:
            >>> from tribsmodel import Model
            >>> m = Model()
            >>> m.options
            {'startdate': 'STARTDATE:', 'runtime': 'RUNTIME:', 'rainsearch': 'RAINSEARCH:',...
        """
        self.options = {
            "startdate": {"key_word": "STARTDATE:", "describe": "Starting time (MM/DD/YYYY/HH/MM)", "value": None,
                          "tags": ["time"]},
            "runtime": {"key_word": "RUNTIME:", "describe": "simulation length in hours", "value": None,
                        "tags": ["time"]},
            "rainsearch": {"key_word": "RAINSEARCH:", "describe": "Rainfall search interval (hours)", "value": 24,
                           "tags": ["time"]},
            "timestep": {"key_word": "TIMESTEP:", "describe": "Unsaturated zone computational time step (mins)",
                         "value": 3.75, "tags": ["time"]},
            "gwstep": {"key_word": "GWSTEP:", "describe": "Saturated zone computational time step (mins)",
                       "value": 30.0, "tags": ["time"]},
            "metstep": {"key_word": "METSTEP:", "describe": "Meteorological data time step (mins)", "value": 60.0,
                        "tags": ["time"]},
            "etistep": {"key_word": "ETISTEP:", "describe": "ET, interception and snow time step (hours)", "value": 1,
                        "tags": ["time"]},
            "rainintrvl": {"key_word": "RAININTRVL:", "describe": "Time interval in rainfall input (hours)",
                           "value": 1, "tags": ["time"]},
            "opintrvl": {"key_word": "OPINTRVL:", "describe": "Output interval (hours)", "value": 1, "tags": ["time"]},
            "spopintrvl": {"key_word": "SPOPINTRVL:", "describe": "Spatial output interval (hours)", "value": 50000,
                           "tags": ["time"]},
            "intstormmax": {"key_word": "INTSTORMMAX:", "describe": "Interstorm interval (hours)", "value": 10000,
                            "tags": ["time"]},
            "baseflow": {"key_word": "BASEFLOW:", "describe": "Baseflow discharge (m3/s)", "value": 0.2,
                         "tags": ["physical"]},
            "velocitycoef": {"key_word": "VELOCITYCOEF:", "describe": "Discharge-velocity coefficient", "value": 1.2,
                             "tags": ["physical"]},
            "kinemvelcoef": {"key_word": "KINEMVELCOEF:", "describe": "Kinematic routing velocity coefficient",
                             "value": 3, "tags": ["physical"]},
            "velocityratio": {"key_word": "VELOCITYRATIO:", "describe": "Stream to hillslope velocity coefficient",
                              "value": 60, "tags": ["physical"]},
            "flowexp": {"key_word": "FLOWEXP:", "describe": "Nonlinear discharge coefficient", "value": 0.3,
                        "tags": ["physical"]},
            "channelroughness": {"key_word": "CHANNELROUGHNESS:", "describe": "Uniform channel roughness value",
                                 "value": 0.15, "tags": ["physical"]},
            "channelwidth": {"key_word": "CHANNELWIDTH:", "describe": "Uniform channel width  (meters)", "value": 12,
                             "tags": ["physical"]},
            "channelwidthcoeff": {"key_word": "CHANNELWIDTHCOEFF:",
                                  "describe": "Coefficient in width-area relationship", "value": 2.33,
                                  "tags": ["physical"]},
            "channelwidthexpnt": {"key_word": "CHANNELWIDTHEXPNT:", "describe": "Exponent in width-area relationship",
                                  "value": 0.54, "tags": ["physical"]},
            "channelwidthfile": {"key_word": "CHANNELWIDTHFILE:", "describe": "Filename that contains channel widths",
                                 "value": None, "tags": ["io"]},
            "optmeshinput": {"key_word": "OPTMESHINPUT:", "describe": "Mesh input data option\n" + \
                                                                      "1  tMesh data\n" + \
                                                                      "2  Point file\n" + \
                                                                      "3  ArcGrid (random)\n" + \
                                                                      "4  ArcGrid (hex)\n" + \
                                                                      "5  Arc/Info *.net\n" + \
                                                                      "6  Arc/Info *.lin,*.pnt\n" + \
                                                                      "7  Scratch\n" + \
                                                                      "8  Point Triangulator", "value": 8,
                             "tags": ["opts"]},
            "rainsource": {"key_word": "RAINSOURCE:", "describe": "Rainfall data source option\n" +
                                                                  "1  Stage III radar\n" +
                                                                  "2  WSI radar\n" +
                                                                  "3  Rain gauges", "value": 3, "tags": ["opts"]},
            "optevapotrans": {"key_word": "OPTEVAPOTRANS:", "describe": "Option for evapoTranspiration scheme\n" + \
                                                                        "0  Inactive evapotranspiration\n" + \
                                                                        "1  Penman-Monteith method\n" + \
                                                                        "2  Deardorff method\n" + \
                                                                        "3  Priestley-Taylor method\n" + \
                                                                        "4  Pan evaporation measurements", "value": 1,
                              "tags": ["opts"]},
            "hillalbopt": {"key_word": "HILLALBOPT:", "describe": "Option for albedo of surrounding hillslopes\n" + \
                                                                  "0  Snow albedo for hillslopes\n" + \
                                                                  "1  Land-cover albedo for hillslopes\n" + \
                                                                  "2  Dynamic albedo for hillslopes", "value": 0,
                           "tags": ["opts"]},
            "optradshelt": {"key_word": "OPTRADSHELT:", "describe": "Option for local and remote radiation sheltering" +
                                                                    "0  Local controls on shortwave radiation\n" + \
                                                                    "1  Remote controls on diffuse shortwave\n" + \
                                                                    "2  Remote controls on entire shortwave\n" + \
                                                                    "3  No sheltering", "value": 0, "tags": ["opts"]},
            "optintercept": {"key_word": "OPTINTERCEPT:", "describe": "Option for interception scheme\n" + \
                                                                      "0  Inactive interception\n" + \
                                                                      "1  Canopy storage method\n" + \
                                                                      "2  Canopy water balance method", "value": 2,
                             "tags": ["opts"]},
            "optlanduse": {"key_word": "OPTLANDUSE:", "describe": "Option for static or dynamic land cover\n" + \
                                                                  "0  Static land cover maps\n" + \
                                                                  "1  Dynamic updating of land cover maps", "value": 0,
                           "tags": ["opts"]},
            "optluinterp": {"key_word": "OPTLUINTERP:", "describe": "Option for interpolation of land cover\n" + \
                                                                    "0  Constant (previous) values between land cover\n" + \
                                                                    "1  Linear interpolation between land cover",
                            "value": 1, "tags": ["opts"]},
            "gfluxoption": {"key_word": "GFLUXOPTION:", "describe": "Option for ground heat flux\n" + \
                                                                    "0  Inactive ground heat flux\n" + \
                                                                    "1  Temperature gradient method\n" + \
                                                                    "2  Force_Restore method", "value": 2},
            "metdataoption": {"key_word": "METDATAOPTION:", "describe": "Option for meteorological data\n" + \
                                                                        "0  Inactive meteorological data\n" + \
                                                                        "1  Weather station point data\n" +
                                                                        "2  Gridded meteorological data", "value": 1,
                              "tags": ["opts"]},
            "convertdata": {"key_word": "CONVERTDATA:", "describe": "Option to convert met data format", "value": 0,
                            "tags": ["opts"]},
            # TODO update options in describe
            "optbedrock": {"key_word": "OPTBEDROCK:", "describe": "Option for uniform or variable depth", "value": 0,
                           "tags": ["opts"]},
            "widthinterpolation": {"key_word": "WIDTHINTERPOLATION:",
                                   "describe": "Option for interpolating width values", "value": 0, "tags": ["opts"]},
            "optgwfile": {"key_word": "OPTGWFILE:", "describe": "Option for groundwater initial file\n" + \
                                                                "0 Resample ASCII grid file in GWATERFILE\n" + \
                                                                "1 Read in Voronoi polygon file with GW levels",
                          "value": 0, "tags": ["opts"]},
            "optrunon": {"key_word": "OPTRUNON:", "describe": "Option for runon in overland flow paths", "value": 0,
                         "tags": ["opts"]},
            "optreservoir": {"key_word": "OPTRESERVOIR:", "describe": None, "value": 0, "tags": ["opts"]},
            # TODO update describe
            "optsoiltype": {"key_word": "OPTSOILTYPE:", "describe": None, "value": 0, "tags": ["opts"]},
            # TODO update describe
            "optspatial": {"key_word": "OPTSPATIAL:", "describe": "Enable dynamic spatial output", "value": 0,
                           "tags": ["opts"]},
            "optgroundwater": {"key_word": "OPTGROUNDWATER:", "describe": "Enable groundwater module", "value": 1,
                               "tags": ["opts"]},
            "optinterhydro": {"key_word": "OPTINTERHYDRO:", "describe": "Enable intermediate hydrograph output",
                              "value": 0, "tags": ["opts"]},
            "optheader": {"key_word": "OPTHEADER:", "describe": "Enable headers in output files", "value": 1,
                          "tags": ["opts"]},
            "optsnow": {"key_word": "OPTSNOW:", "describe": "Enable single layer snow module", "value": 1,
                        "tags": ["opts"]},
            "inputdatafile": {"key_word": "INPUTDATAFILE:", "describe": "tMesh input file base name for Mesh files",
                              "value": None, "tags": ["io"]},
            "inputtime": {"key_word": "INPUTTIME:", "describe": "deprecated", "value": None, "tags": ["deprecated"]},
            # TODO remove option, child remnant?
            "arcinfofilename": {"key_word": "ARCINFOFILENAME:", "describe": "tMesh input file base name Arc files",
                                "value": None, "tags": ["io"]},
            "pointfilename": {"key_word": "POINTFILENAME:", "describe": "tMesh input file name Points files",
                              "value": None, "tags": ["io"]},
            "soiltablename": {"key_word": "SOILTABLENAME:", "describe": "Soil parameter reference table (*.sdt)",
                              "value": None, "tags": ["io"]},
            "soilmapname": {"key_word": "SOILMAPNAME:", "describe": "Soil texture ASCII grid (*.soi)", "value": None,
                            "tags": ["io"]},
            "landtablename": {"key_word": "LANDTABLENAME:", "describe": "Land use parameter reference table",
                              "value": None, "tags": ["io"]},
            "landmapname": {"key_word": "LANDMAPNAME:", "describe": "Land use ASCII grid (*.lan)", "value": None,
                            "tags": ["io"]},
            "gwaterfile": {"key_word": "GWATERFILE:", "describe": "Ground water ASCII grid (*iwt)", "value": None,
                           "tags": ["io"]},
            "demfile": {"key_word": "DEMFILE:", "describe": "DEM ASCII grid for sky and land view factors (*.dem)",
                        "value": None, "tags": ["io"]},
            "rainfile": {"key_word": "RAINFILE:", "describe": "Base name of the radar ASCII grid", "value": None,
                         "tags": ["io"]},
            "rainextension": {"key_word": "RAINEXTENSION:", "describe": "Extension for the radar ASCII grid",
                              "value": None, "tags": ["io"]},
            "depthtobedrock": {"key_word": "DEPTHTOBEDROCK:", "describe": "Uniform depth to bedrock (meters)",
                               "value": 15, "tags": ["physical"]},
            "bedrockfile": {"key_word": "BEDROCKFILE:", "describe": "Bedrock depth ASCII grid (*.brd)", "value": None,
                            "tags": ["io"]},
            "lugrid": {"key_word": "LUGRID:", "describe": "Land cover grid data file (*.gdf)", "value": None,
                       "tags": ["io"]},
            "tlinke": {"key_word": "TLINKE:", "describe": "Atmospheric turbidity parameter", "value": 2.5,
                       "tags": ["physical"]},
            "minsntemp": {"key_word": "MINSNTEMP:", "describe": "Minimum snow temperature", "value": -50.0,
                          "tags": ["physical"]},
            "snliqfrac": {"key_word": "SNLIQFRAC:", "describe": "Maximum fraction of liquid water in snowpack",
                          "value": 0.065, "tags": ["physical"]},
            "templapse": {"key_word": "TEMPLAPSE:", "describe": "Temperature lapse rate", "value": -0.0065,
                          "tags": ["physical"]},
            "preclapse": {"key_word": "PRECLAPSE:", "describe": "Precipitation lapse rate", "value": 0,
                          "tags": ["physical"]},
            "hydrometstations": {"key_word": "HYDROMETSTATIONS:",
                                 "describe": "Hydrometeorological station file (*.sdf)", "value": None, "tags": ["io"]},
            "hydrometgrid": {"key_word": "HYDROMETGRID:", "describe": "Hydrometeorological grid data file (*.gdf)",
                             "value": None, "tags": ["io"]},
            "hydrometconvert": {"key_word": "HYDROMETCONVERT:",
                                "describe": "Hydrometeorological data conversion file (*.mdi)", "value": None,
                                "tags": ["io", "deprecated"]},
            "hydrometbasename": {"key_word": "HYDROMETBASENAME:",
                                 "describe": "Hydrometeorological data BASE name (*.mdf)", "value": None,
                                 "tags": ["io"]},
            "gaugestations": {"key_word": "GAUGESTATIONS:", "describe": " Rain Gauge station file (*.sdf)",
                              "value": None, "tags": ["io"]},
            "gaugeconvert": {"key_word": "GAUGECONVERT:", "describe": "Rain Gauge data conversion file (*.mdi)",
                             "value": None, "tags": ["io", "deprecated"]},
            "gaugebasename": {"key_word": "GAUGEBASENAME:", "describe": " Rain Gauge data BASE name (*.mdf)",
                              "value": None, "tags": ["io"]},
            "outhydroextension": {"key_word": "OUTHYDROEXTENSION:", "describe": "Extension for hydrograph output",
                                  "value": "mrf", "tags": ["io"]},
            "ribshydoutput": {"key_word": "RIBSHYDOUTPUT:", "describe": "compatibility with RIBS User Interphase",
                              "value": 0, "tags": ["io", "deprecated"]},
            "nodeoutputlist": {"key_word": "NODEOUTPUTLIST:",
                               "describe": "Filename with Nodes for Dynamic Output (*.nol)", "value": None,
                               "tags": ["io"]},
            "hydronodelist": {"key_word": "HYDRONODELIST:",
                              "describe": "Filename with Nodes for HydroModel Output (*.nol)", "value": None,
                              "tags": ["io"]},
            "outletnodelist": {"key_word": "OUTLETNODELIST:",
                               "describe": "Filename with Interior Nodes for  Output (*.nol)", "value": None,
                               "tags": ["io"]},
            "outfilename": {"key_word": "OUTFILENAME:", "describe": "Base name of the tMesh and variable",
                            "value": None, "tags": ["io"]},
            "outhydrofilename": {"key_word": "OUTHYDROFILENAME:", "describe": "Base name for hydrograph output",
                                 "value": None, "tags": ["io"]},
            "forecastmode": {"key_word": "FORECASTMODE:", "describe": "Rainfall Forecasting Mode Option", "value": 0,
                             "tags": ["opts"]},
            # TODO need to update model mode descriptions
            "forecasttime": {"key_word": "FORECASTTIME:", "describe": "Forecast Time (hours from start)", "value": 0,
                             "tags": ["time"]},
            "forecastleadtime": {"key_word": "FORECASTLEADTIME:", "describe": "Forecast Lead Time (hours) ",
                                 "value": 0, "tags": ["time"]},
            "forecastlength": {"key_word": "FORECASTLENGTH:", "describe": "Forecast Window Length (hours)", "value": 0,
                               "tags": ["time"]},
            "forecastfile": {"key_word": "FORECASTFILE:", "describe": "Base name of the radar QPF grids",
                             "value": None, "tags": ["io"]},
            "climatology": {"key_word": "CLIMATOLOGY:", "describe": "Rainfall climatology (mm/hr)", "value": 0,
                            "tags": ["physical"]},
            "raindistribution": {"key_word": "RAINDISTRIBUTION:", "describe": "Distributed or MAP radar rainfall",
                                 "value": 0, "tags": ["opts"]},
            "stochasticmode": {"key_word": "STOCHASTICMODE:", "describe": "Stochastic Climate Mode Option", "value": 0,
                               "tags": ["opts"]},
            "pmean": {"key_word": "PMEAN:", "describe": "Mean rainfall intensity (mm/hr)	", "value": 0,
                      "tags": ["physical"]},
            "stdur": {"key_word": "STDUR:", "describe": "Mean storm duration (hours)", "value": 0,
                      "tags": ["physical"]},
            "istdur": {"key_word": "ISTDUR:", "describe": "Mean time interval between storms (hours)", "value": 0,
                       "tags": ["physical"]},
            "seed": {"key_word": "SEED:", "describe": "Random seed", "value": 0, "tags": ["physical"]},
            "period": {"key_word": "PERIOD:", "describe": "Period of variation (hours)", "value": 0,
                       "tags": ["physical"]},
            "maxpmean": {"key_word": "MAXPMEAN:", "describe": "Maximum value of mean rainfall intensity (mm/hr)",
                         "value": 0, "tags": ["physical"]},
            "maxstdurmn": {"key_word": "MAXSTDURMN:", "describe": "Maximum value of mean storm duration (hours)",
                           "value": 0, "tags": ["physical"]},
            "maxistdurmn": {"key_word": "MAXISTDURMN:", "describe": "Maximum value of mean interstorm period (hours)",
                            "value": 0, "tags": ["physical"]},
            "weathertablename": {"key_word": "WEATHERTABLENAME:", "describe": "File with Stochastic Weather Table",
                                 "value": None, "tags": ["io"]},
            "restartmode": {"key_word": "RESTARTMODE:", "describe": "Restart Mode Option\n" + \
                                                                    "0 No reading or writing of restart\n" + \
                                                                    "1 Write files (only for initial runs)\n" + \
                                                                    "2 Read file only (to start at some specified time)\n" + \
                                                                    " Read a restart file and continue to write",
                            "value": 0, "tags": ["restart"]},
            "restartintrvl": {"key_word": "RESTARTINTRVL:", "describe": "Time set for restart output (hours)",
                              "value": None, "tags": ["restart"]},
            "restartdir": {"key_word": "RESTARTDIR:", "describe": "Path of directory for restart output",
                           "value": None, "tags": ["restart", "io"]},
            "restartfile": {"key_word": "RESTARTFILE:", "describe": "Actual file to restart a run", "value": None,
                            "tags": ["restart", "io"]},
            "parallelmode": {"key_word": "PARALLELMODE:", "describe": "Parallel or Serial Mode Option\n" + \
                                                                      "0  Run in serial mode\n" + \
                                                                      "1  Run in parallel mode",
                             "value": 0, "tags": ["parallel", "opts"]},
            "graphoption": {"key_word": "GRAPHOPTION:", "describe": "Graph File Type Option\n" + \
                                                                    "0  Default partitioning of the graph\n" + \
                                                                    "1  Reach-based partitioning\n" + \
                                                                    "2  Inlet/outlet-based partitioning", "value": 0,
                            "tags": ["parallel", "opts"]},
            "graphfile": {"key_word": "GRAPHFILE:", "describe": "Reach connectivity filename (graph file option 1,2)",
                          "value": None, "tags": ["parallel", "io"]},
            "optviz": {"key_word": "OPTVIZ:", "describe": "Option to write binary output files for visualization\n" + \
                                                          "0  Do NOT write binary output files for viz\n" + \
                                                          "1  Write binary output files for viz", "value": 0,
                       "tags": ["opts"]},
            "outvizfilename": {"key_word": "OUTVIZFILENAME:", "describe": "Filename for viz binary files",
                               "value": None, "tags": ["io"]},
            "optpercolation": {"key_word": "OPTPERCOLATION:", "describe": "Needs to be updated", "value": 0,
                               "tags": ["physical"]},
            "channelconductivity": {"key_word": "CHANNELCONDUCTIVITY:", "describe": "Needs to be updated", "value": 0,
                                    "tags": ["physical"]},
            "transientconductivity": {"key_word": "TRANSIENTCONDUCTIVITY:", "describe": "Needs to be updated",
                                      "value": 0, "tags": ["physical"]},
            "transienttime": {"key_word": "TRANSIENTTIME:", "describe": "Needs to be updated", "value": 0,
                              "tags": ["physical"]},
            "channelporosity": {"key_word": "CHANNELPOROSITY:", "describe": "Needs to be updated", "value": 0,
                                "tags": ["physical"]},
            "chanporeindex": {"key_word": "CHANPOREINDEX:", "describe": "Needs to be updated", "value": 0,
                              "tags": ["physical"]},
            "chanpsib": {"key_word": "CHANPSIB:", "describe": "Needs to be updated", "value": 0, "tags": ["physical"]}
        }


# POST-PROCESSING NESTED CLASS: RESULTS
class Results(Model):
    """
    A tRIBS Results Class.

    This class provides a framework for analyzing and visualizing individual tRIBS simulations. It takes an instance of
    Class Simulation and provides time-series and water balance analysis of the model results.


    Attributes:

    Methods:

    Example:
        Provide an example of how to create and use an instance of this class

    """

    def __init__(self, mod):
        self.element = None
        self.mrf = None
        self.options = mod.options

    def get_mrf_results(self, mrf_file=None):
        """

        """
        if mrf_file is None:
            mrf_file = self.options["outfilename"]["value"] + str(self.options["runtime"]["value"]) + "_00.mrf"

        # Read the first two rows to get column names and units
        with open(mrf_file, 'r') as file:
            column_names = file.readline().strip().split('\t')  # Assuming tab-separated data
            units = file.readline().strip().split('\t')  # Assuming tab-separated data

        # Read the data into a DataFrame, skipping the first two rows
        results_data_frame = pd.read_csv(mrf_file, skiprows=1, sep='\t')

        # Assign column names to the DataFrame
        results_data_frame.columns = column_names

        # Add units as metadata
        results_data_frame.attrs["units"] = units

        # # update time from hourly time step to date
        starting_date = self.options["startdate"]["value"]
        date = self.convert_to_datetime(starting_date)
        dt = pd.to_timedelta(results_data_frame['Time'], unit='h')
        results_data_frame['Time'] = [date + step for step in dt]

        self.mrf = results_data_frame
        return units

    def get_element_results(self, node_file=None):
        """
        Function assigns a dictionary to self as self.element_results. The keys in the dictionary represent a data
        frame with the content of the .invpixel file and each subsequent node. Key for .invpixel is "invar",
        and for nodes is simply the node ID. For each node this function reads in element file and create data frame
        of results and is assigned to the aforementioned dictionary.
        """

        if node_file is None:
            node_file = self.options["nodeoutputlist"]["value"]

        # read in node list
        nodes = self.read_node_list(node_file)

        # read in .ivpixel
        invar_path = self.options["outfilename"]["value"] + ".ivpixel"
        invar_data_frame = pd.read_csv(invar_path, sep=r"\s+", header=0)
        self.element = {"invar": invar_data_frame}

        # for each node read in element file read and set up a dictionary containing node
        for n in nodes:
            self.element.update({n: self.read_element_files(n)})

    def read_element_files(self, node):
        """
        Reads in .pixel from tRIBS model results and updates hourly timestep to time
        """
        element_results_file = self.options["outfilename"]["value"] + str(
            node) + ".pixel"  # need to add catch for parallel runs and if file doesn't exist
        results_data_frame = pd.read_csv(element_results_file, sep=r"\s+", header=0)

        # update time from hourly time step to date
        starting_date = self.options["startdate"]["value"]
        date = self.convert_to_datetime(starting_date)
        dt = pd.to_timedelta(results_data_frame['Time_hr'], unit='h')
        results_data_frame['Time'] = [date + step for step in dt]

        return results_data_frame

    def get_mrf_water_balance(self, method, porosity, bedrock, drainage_area):
        """
        """
        waterbalance = self.run_mrf_water_balance(self.mrf, porosity, bedrock, drainage_area, method)
        var = {"mrf": self.mrf, "waterbalance": waterbalance}
        self.mrf = var

    def get_element_water_balance(self, method, node_file=None):
        """
        This function loops through element_results and assigns water_balance as second item in the list for a given
        node/key. The user can specify a method for calculating the time frames over which the water balance is
        calculated.
        """
        # read in node list
        if node_file is None:
            node_file = self.options["nodeoutputlist"]["value"]

        nodes = self.read_node_list(node_file)
        invar_data_frame = self.element['invar']

        for n in nodes:
            porosity = invar_data_frame.Porosity[invar_data_frame.NodeID == int(n)].values[0]
            element_area = invar_data_frame.Area_m_sq[invar_data_frame.NodeID == int(n)].values[0]
            waterbalance = self.run_element_water_balance(self.element[n], porosity, element_area, method)
            self.element.update({n: {"pixel": self.element[n], "waterbalance": waterbalance}})

    # WATER BALANCE FUNCTIONS
    def run_element_water_balance(self, data, porosity, element_area, method):
        """

        :param data:
        :param porosity:
        :param element_area:
        :param method:
        :return: pandas data frame with waterbalance information
        """

        begin, end, timeframe = self.water_balance_dates(data, method)

        for n in range(0, len(timeframe)):
            if n == 0:
                waterbalance = self.element_wb_components(data, begin[n], end[n], porosity, element_area)
            else:
                temp = self.element_wb_components(data, begin[n], end[n], porosity, element_area)

                for key, val in temp.items():

                    if key in waterbalance:
                        waterbalance[key] = np.append(waterbalance[key], val)

        waterbalance.update({"Time": timeframe})
        waterbalance = pd.DataFrame.from_dict(waterbalance)
        waterbalance.set_index('Time', inplace=True)

        waterbalance['dS'] = np.add(np.add(waterbalance['dUnsat'], waterbalance['dSat'], waterbalance['dCanopySWE']),
                                    waterbalance['dSWE'],
                                    waterbalance['dCanopy'])  # change in storage

        waterbalance['nQ'] = np.add(waterbalance['nQsurf'], waterbalance['nQunsat'],
                                    waterbalance['nQsat'])  # net fluxes from surface and saturated and unsaturated zone

        return waterbalance

    @staticmethod
    def element_wb_components(element_data_frame, begin, end, porosity, element_area):
        """
        Computes water balance calculations for an individual computational element or node over a specified time frame. Data = pandas data
        frame of .pixel file, begin is start date, end is end date, bedrock depth is the depth to bedrock,
        porosity is well, porosity, and element area is surface area of voronoi polygon. Returns a dictionary with
        individual water components, keys with the prescript d indicate change in storage (i.e. delta) and n
        indicates net cumulative flux.
        """

        # logical index for calculating water balance
        begin_id = element_data_frame['Time'].values == begin
        end_id = element_data_frame['Time'].values == end
        duration_id = (element_data_frame['Time'].values >= begin) & (
                element_data_frame['Time'].values <= end)

        # return dictionary with values
        waterbalance = {}

        # Store ET flux as series due to complexity
        evapotrans = element_data_frame['EvpTtrs_mm_h'] - (
                element_data_frame.SnSub_cm * 10 + element_data_frame.SnEvap_cm * 10 + element_data_frame.IntSub_cm * 10)  # Snow evaporation fluxes are subtracted due to signed behavior in snow module

        # calculate individual water balance components
        waterbalance.update(
            {'dUnsat': element_data_frame.Mu_mm.values[end_id][0] - element_data_frame.Mu_mm.values[begin_id][
                0]})  # [0] converts from array to float
        waterbalance.update(
            {'dSat': (element_data_frame.Nwt_mm.values[begin_id][0] - element_data_frame.Nwt_mm.values[end_id][
                0]) * porosity})
        waterbalance.update({'dCanopySWE': (10 * (
                element_data_frame.IntSWEq_cm.values[end_id][0] - element_data_frame.IntSWEq_cm.values[begin_id][
            0]))})  # convert from cm to mm
        waterbalance.update({'dSWE': (10 * (
                element_data_frame.SnWE_cm.values[end_id][0] - element_data_frame.SnWE_cm.values[begin_id][0]))})
        waterbalance.update({'dCanopy': element_data_frame.CanStorage_mm.values[end_id][0] -
                                        element_data_frame.CanStorage_mm.values[begin_id][0]})
        waterbalance.update({'nP': np.sum(element_data_frame['Rain_mm_h'].values[duration_id])})
        waterbalance.update({'nET': np.sum(evapotrans.values[duration_id])})
        waterbalance.update({'nQsurf': np.sum(element_data_frame['Srf_Hour_mm'].values[duration_id])})
        waterbalance.update(
            {'nQunsat': np.sum(element_data_frame['QpIn_mm_h'].values[duration_id]) - np.sum(
                element_data_frame['QpOut_mm_h'].values[duration_id])})
        waterbalance.update(
            {'nQsat': np.sum(
                element_data_frame['GWflx_m3_h'].values[
                    duration_id]) / element_area * 1000})  # convert from m^3/h to mm/h

        return waterbalance

    def run_mrf_water_balance(self, data, porosity, bedrock, drainage_area, method):
        """

        :param data:
        :param porosity:
        :param method:
        :return: pandas data frame with waterbalance information
        """

        begin, end, timeframe = self.water_balance_dates(data, method)

        for n in range(0, len(timeframe)):
            if n == 0:
                waterbalance = self.mrf_wb_components(data, begin[n], end[n], porosity, bedrock, drainage_area)
            else:
                temp = self.mrf_wb_components(data, begin[n], end[n], porosity, bedrock, drainage_area)

                for key, val in temp.items():

                    if key in waterbalance:
                        waterbalance[key] = np.append(waterbalance[key], val)

        waterbalance.update({"Time": timeframe})
        # change in storage
        waterbalance.update({"dS": waterbalance['dUnsat'] + waterbalance['dSat'] + waterbalance['dCanopySWE'] +
                                   waterbalance['dSWE'] + waterbalance['dCanopy']})
        # net fluxes from surface and saturated and unsaturated zone
        waterbalance.update({'nQ': waterbalance['nQsurf'] + waterbalance['nQunsat'] + waterbalance['nQsat']})

        waterbalance = pd.DataFrame.from_dict(waterbalance)
        waterbalance.set_index('Time', inplace=True)

        return waterbalance

    @staticmethod
    def mrf_wb_components(mrf_data_frame, begin, end, porosity, bedrock_depth, drainage_area):
        """
        Computes water balance calculations for an individual computational mrf or node over a specified time frame. Data = pandas data
        frame of .pixel file, begin is start date, end is end date, bedrock depth is the depth to bedrock,
        porosity is well, porosity, and mrf area is surface area of voronoi polygon. Returns a dictionary with
        individual water components, keys with the prescript d indicate change in storage (i.e. delta) and n
        indicates net cumulative flux.
        """

        # logical index for calculating water balance
        begin_id = mrf_data_frame['Time'].values == begin
        end_id = mrf_data_frame['Time'].values == end
        duration_id = (mrf_data_frame['Time'].values >= begin) & (
                mrf_data_frame['Time'].values <= end)

        # return dictionary with values
        waterbalance = {}

        # Store ET flux as series due to complexity
        # Snow evaporation fluxes are subtracted due to signed behavior in snow module
        evapotrans = mrf_data_frame.MET - 10 * (
                mrf_data_frame.AvSnSub + mrf_data_frame.AvSnEvap + mrf_data_frame.AvInSu)
        unsaturated = mrf_data_frame.MSMU.values * porosity * mrf_data_frame.MDGW.values
        saturated = (bedrock_depth - mrf_data_frame.MDGW.values) * porosity

        # calculate individual water balance components
        waterbalance.update(
            {'dSat': saturated[end_id] - saturated[begin_id]})  # [0] converts from array to float
        waterbalance.update(
            {'dUnsat': (unsaturated[begin_id] - unsaturated[end_id])})
        waterbalance.update({'dCanopySWE': (10 * (
                mrf_data_frame.AvInSn.values[end_id][0] - mrf_data_frame.AvInSn.values[begin_id][
            0]))})  # convert from cm to mm
        waterbalance.update({'dSWE': (10 * (
                mrf_data_frame.AvSWE.values[end_id][0] - mrf_data_frame.AvSWE.values[begin_id][0]))})
        waterbalance.update({'dCanopy': 0})  # TODO update mrf w/ mean intercepted canpoy storaage
        waterbalance.update({'nP': np.sum(mrf_data_frame.MAP.values[duration_id])})
        waterbalance.update({'nET': np.sum(evapotrans.values[duration_id])})
        waterbalance.update({'nQsurf': np.sum(mrf_data_frame.Srf.values[duration_id] * 3600 * 1000 / drainage_area)})
        waterbalance.update({'nQunsat': 0})  # Assumption in model is closed boundaries at divide and outled
        waterbalance.update({'nQsat': 0})

        return waterbalance

    @staticmethod
    def plot_water_balance(waterbalance, saved_fig=None):
        """

        :param saved_fig:
       :param waterbalance:
       :return:
       """

        plt.style.use('bmh')
        barwidth = 0.25
        fig, ax = plt.subplots()

        ax.bar(np.arange(len(waterbalance)) + barwidth, waterbalance['nP'], align='center', width=barwidth,
               color='grey', label='nP')
        rects = ax.patches

        # Make some labels.
        labels = ["%.0f" % (p - waterbalance) for p, waterbalance in
                  zip(waterbalance['nP'], waterbalance['dS'] + waterbalance['nQ'] + waterbalance['nET'])]
        netdiff = [p - waterbalance for p, waterbalance in
                   zip(waterbalance['nP'], waterbalance['dS'] + waterbalance['nQ'] + waterbalance['nET'])]

        for rect, label in zip(rects, labels):
            height = rect.get_height()
            ax.text(
                rect.get_x() + rect.get_width() / 2, height + 5, label, ha="center", va="bottom"
            )

        ax.text(len(waterbalance.index) - 5, max(waterbalance.nP), "mean difference: " + "%.0f" % np.mean(netdiff))

        waterbalance.plot.bar(ax=ax, y=["nQ", "nET", "dS"], stacked=True, width=barwidth,
                              color=['tab:blue', 'tab:red', 'tab:cyan'])
        ax.legend(bbox_to_anchor=(1.35, 0.85), loc='center right',
                  labels=["Precip.", "Runoff", "Evapo. Trans.", "$\Delta$ Storage"])
        ax.set_ylabel("Water Flux & $\Delta$ Storage (mm)")
        ax.set_xticks(range(len(waterbalance.index)), waterbalance.index.strftime("%Y-%m"), rotation=45)
        fig.autofmt_xdate()
        plt.show()

        if saved_fig is not None:
            plt.savefig(saved_fig, bbox_inches='tight')

        return fig, ax

    @staticmethod
    def water_balance_dates(results_data_frame, method):
        """
        data = pandas data frame of .pixel file, methods select approach for segmenting data['Time_hr'].
        "water_year", segments time frame by water year and discards results that do not start first or end on
        last water year in data. "year", just segments based on year, "month" segments base on month,
        and "cold_warm",segments on cold (Oct-April) and warm season (May-Sep).
        """

        min_date = min(results_data_frame.Time)
        max_date = max(results_data_frame.Time)
        begin_dates = None
        end_dates = None

        if method == "water_year":
            years = np.arange(min_date.year, max_date.year)
            begin_dates = [pd.Timestamp(year=x, month=10, day=1, hour=0, minute=0, second=0) for x in years]
            years += 1
            end_dates = [pd.Timestamp(year=x, month=9, day=30, hour=23, minute=0, second=0) for x in years]

            # make sure water years are in data set
            while begin_dates[0] < min_date:
                begin_dates.pop(0)
                end_dates.pop(0)

            while end_dates[len(end_dates) - 1] > max_date:
                begin_dates.pop(len(end_dates) - 1)
                end_dates.pop(len(end_dates) - 1)

        if method == "year":
            years = np.arange(min_date.year, max_date.year)
            begin_dates = [pd.Timestamp(year=x, month=1, day=1, hour=0, minute=0, second=0) for x in years]
            end_dates = [pd.Timestamp(year=x, month=12, day=31, hour=23, minute=0, second=0) for x in years]

            # adjust start date according to min_date
            begin_dates[0] = min_date

            # add ending date according to end_date
            end_dates.append(max_date)

            # add last year to years
            years = np.append(years, max_date.year)

        if method == "cold_warm":
            years = np.arange(min_date.year, max_date.year + 1)
            begin_dates = [[pd.Timestamp(year=x, month=5, day=1, hour=0, minute=0, second=0),
                            pd.Timestamp(year=x, month=10, day=1, hour=0, minute=0, second=0)] for x in years]
            begin_dates = [date for sublist in begin_dates for date in sublist]
            end_dates = [[pd.Timestamp(year=x, month=9, day=30, hour=23, minute=0, second=0),
                          pd.Timestamp(year=x + 1, month=4, day=30, hour=23, minute=0, second=0)] for x in years]
            end_dates = [date for sublist in end_dates for date in sublist]

            # make sure season are in data set
            while begin_dates[0] < min_date:
                begin_dates.pop(0)
                end_dates.pop(0)

            while end_dates[len(end_dates) - 1] > max_date:
                begin_dates.pop(len(end_dates) - 1)
                end_dates.pop(len(end_dates) - 1)

        # Update date time to reflect middle of period over which the waterbalance is calculated
        years = [x + (y - x) / 2 for x, y in zip(begin_dates, end_dates)]
        return begin_dates, end_dates, years
