# PV TOMCAT
PV TOMCAT (or TOMCAT) is a simulation framework for predicting photovoltaic (PV) cell operating temperature as a function of measurable optical and thermal module properties and ambient weather conditions. It is designed to support research into innovative methods for increasing energy yield through reduced operating temperature.

## Requirements

The TOMCAT framework requires the following.

1. [SunSolve](https://www.pvlighthouse.com.au/sunsolve), for ray-tracing simulations of module optics
1. A SunSolve model of a PV module (an example is included)
1. [COMSOL Multiphysics](https://www.comsol.com) and the COMSOL Heat Transfer Module, for conduction and radiation simulations
1. A COMSOL model of a PV system (an example is included)
1. Python and the Python functions, included in this repository, for preparing inputs to the COMSOL model
1. A weather input file, such as a TMY3 file

## Doing the example simulation

Before you customize the TOMCAT simulation to your needs, it is recommended to run the example simulation. This will familiarize you with the framework and will confirm that all of the tools are in place.

### Optical simulation

1. Log into [SunSolve](https://www.pvlighthouse.com.au/sunsolve), a cloud-based ray tracing tool for PV module optics
1. Load the example file `baseline harmonized.pvl` from this repository
1. Carry out an optical simulation, sweeping angle of incidence from 0 to 88 degrees in steps of 11 degrees
1. Prepare an **optics file** from the results

#### Optics file format
The optics file details where solar radiation is absorbed within the module and photocurrent changes for different angles of incidence. It must be a `.csv` file with the following column names. Note that all values should include cosine losses from angle of incidence.  
`angle` The angle of incidence for solar illumination in degrees, 0 is normal  
`glass_abs_W/m2` Absorbed energy in the front glass  
`encapsulant_abs_W/m2` Absorbed energy in the front encapsulant  
`cell_abs_W/m2` Absorbed energy in the front cell  
`current_factor` The fractional change in photocurrent from relative to the value corresponding to the `efficiencyElectricalSTC` parameter in the FEM simulation

### Preparing time-series and tilt input files

1. Select a [TMY3](https://www.nrel.gov/docs/fy08osti/43156.pdf) weather file
1. Use the `generate_input` function in `tomcat_tmy.py` to combine the weather file and the optics file into a **time-series file** named `TOMCAT_input.csv` and a **tilt file** named `TOMCAT_tilt.txt`

#### Using `generate_input`
The following example generates two input files for FEM calculations: `TOMCAT_input.csv` contains time-series inputs and `TOMCAT_tilt.txt` contains the array tilt. The `generate_input` function creates these files based on [TMY3](https://www.nrel.gov/docs/fy08osti/43156.pdf) and optics input files.

```python
from tomcat_tmy import generate_input

input_df = generate_input(tmy_file, optics_file, out_file_time_series='TOMCAT_input.csv', out_file_tilt='TOMCAT_tilt.txt')
```

### Thermal simulation

1. Locate the `TOMCAT_TMY.java` file and compile it using COMSOL's Java compiler (details below). If your system is similar enough to ours (macOS 10.12, COMSOL 5.3a) you may be able to skip this step by using the already-compiled `TOMCAT_TMY.class` file.
1. Place `TOMCAT_input.csv` and `TOMCAT_tilt.txt` in the same location as `TOMCAT_TMY.class`
1. Run the simulation either by opening the COMSOL GUI and loading `TOMCAT_TMY.class`, or by initiating the simulation in batch mode using the terminal (details below).

#### Compiling a COMSOL Java file

The COMSOL documentation covers compiling Java files using COMSOL. On a macOS system, running this line in the Terminal:

    /Applications/COMSOL53a/Multiphysics/bin/comsol compile -jdkroot `/usr/libexec/java_home -v 1.8*` /full/path/to/TOMCAT_TMY.java

(replacing `/full/path/to/` with the actual path on your system) will produce a `TOMCAT_TMY.class` file that has been compiled with a 1.8* version of Java (the latest supported by COMSOL 5.3a). Naturally, if you are using a different operating system or version of COMSOL, consult COMSOL documentation or COMSOL support for details about compiling.

#### Running a COMSOL `class` file from the terminal

The COMSOL documentation covers running `class` files without the COMSOL GUI (in 'batch mode'). This is useful for running batches of simulations. On a macOS system, running this line in the Terminal:

    /Applications/COMSOL53a/Multiphysics/bin/comsol batch -inputfile /full/path/to/TOMCAT_TMY.class

(replacing `/full/path/to/` with the actual path on your system) will run a year-long simulation and produce `ModelOutput_Power.csv`, `ModelOutput_Temperature.csv`, and `TOMCAT_TMY_Model.mph` files. 

## Customizing the simulation

### Optical changes

Changes to optical properties or to the optical stack representing the PV module and solar cell should be made in SunSolve. Don't forget to propagate these changes all the way to the time-series file.

### Changes to weather conditions

Weather files from any of the [>1000 TMY3 locations](https://rredc.nrel.gov/solar/old_data/nsrdb/1991-2005/tmy3/) can be used without modification.

Weather data from other sources, for instance from local meteorological measurement stations with higher measurement frequency than hourly, can also be used. Because every met station is different, it is the user's responsibility to ensure that local weather data are used correctly to generate the time-series input file.

### Thermal, electrical, and geometric changes

Thermal properties, layer thicknesses, electrical properties, and several PV system parameters are set in the COMSOL file, `TOMCAT_TMY.java`. They can be changed manually or programmatically before compiling and running a new simulation. These parameters can also be changed manually using the Global Definitions: Parameters node of the model in the COMSOL GUI.

## Improving TOMCAT

Formal development of TOMCAT ended on 30 September, 2018. Users are encouraged to fork this repository and implement improvements themselves. Suggested improvements include the following.

1. Improve TOMCAT's very simple convection model to include tilt-dependent natural and forced convection, accounting for differences due to wind direction
1. Replace the heat conduction and radiation simulation capabilities of COMSOL with Python implementations of a radiation view factor model (already developed for short-wave radiation in bifacial PV) and a heat conduction model (countless simple implementations exist)

## Citing TOMCAT

If you use part or all of TOMCAT, please cite it and link to this repository.

## References

TOMCAT is directly descended from the thermal model described in the following paper.

> T J Silverman, M G Deceglie, I Subedi, N J Podraza, I M Slauch, V E Ferry, I Repins. [Reducing operating temperature in photovoltaic modules](https://ieeexplore.ieee.org/document/8252698/). IEEE Journal of Photovoltaics, 2018.

## Acknowledgment

This work was authored in part by the National Renewable Energy Laboratory, operated by Alliance for Sustainable Energy, LLC, for the U.S. Department of Energy (DOE) under Contract No. DE-AC36-08GO28308. Funding was provided by the U.S. Department of Energy Office of Energy Efficiency and Renewable Energy Solar Energy Technologies Office under agreement number 30312. The views expressed in the article do not necessarily represent the views of the DOE or the U.S. Government. The U.S. Government retains and the publisher, by accepting the article for publication, acknowledges that the U.S. Government retains a nonexclusive, paid-up, irrevocable, worldwide license to publish or reproduce the published form of this work, or allow others to do so, for U.S. Government purposes.

## License

PV TOMCAT Copyright (c) 2018 Alliance for Sustainable Energy, LLC and University of Minnesota. All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. The name of the copyright holder(s), any contributors, the United States Government, the United States Department of Energy, or any of their employees may not be used to endorse or promote products derived from this software without specific prior written permission from the respective party.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER(S) AND ANY CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER(S), ANY CONTRIBUTORS, THE UNITED STATES GOVERNMENT, OR THE UNITED STATES DEPARTMENT OF ENERGY, NOR ANY OF THEIR EMPLOYEES, BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
