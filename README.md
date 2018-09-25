# PV TOMCAT
PV TOMCAT (or TOMCAT) is a simulation framework for predicting photovoltaic (PV) cell operating temperature as a function of measurable optical and thermal module properties and ambient weather conditions. It is designed to support research into innovative methods for increasing energy yield through reduced operating temperature.

## Example results

The table below shows several example thermal management strategies for PV modules. The first column gives a description of a thermal management approach. The second column shows the levelized cost of energy (LCOE) in Kansas City, Missouri (KCMO), calculated using the `lcoe()` function or the `pvlcoe.nrel.gov` calculator. We give LCOE assuming the only benefit of temperature reduction is improved energy output, ignoring the service life extension that is enabled by reducing operating temperature. The 'LCOE reduction' column shows the percentage reduction compared to the 'baseline' case. The 'breakeven cost' column shows the maximum cost that an extra component could have and still remain at or below the baseline LCOE. The 'reference' column contains a note referring to one of the works in the References section of this file.

| modification                                                                                        | LCOE in KCMO (USD/kWh) | LCOE reduction | breakeven cost (USD/m^2) | reference                         |
|-----------------------------------------------------------------------------------------------------|------------------------|----------------|--------------------------|-----------------------------------|
| baseline                                                                                            | 0.0670                 |                |                          |                                   |
| double thermal conductivity in packaging behind the cell                                            | 0.0669                 | 0%             | 0.20                     | Silverman 2017, Table II, item 20 |
| maximum possible thermal emissivity on front and back surfaces                                      | 0.0666                 | 1%             | 1.18                     | Silverman 2017, Table II, item 17 |
| Li 2017 omnidirectional multi-layer reflector on cover glass                                        | 0.0660                 | 1%             | 2.95                     | Silverman 2017, Table II, item 9  |
| Li 2017 multi-layer reflector on cover glass                                                        | 0.0657                 | 2%             | 3.73                     | Silverman 2017, Table II, item 8  |
| Slauch 2018 omnidirectional multi-layer reflector on cover glass                                    | 0.0646                 | 4%             | 7.27                     | Slauch 2018                       |
| Ideal sub-bandgap reflector underneath cover glass                                                  | 0.0658                 | 2%             | 3.34                     | Silverman 2017, Table II, item 3  |
| Ideal sub-bandgap reflector underneath cover glass and ideal anti-reflective coating on cover glass | 0.0617                 | 8%             | 16.89                    | Silverman 2017, Table II, item 5  |


## Assumptions
The following assumptions are implicit in the initial TOMCAT release. It is possible to update it to handle conditions not covered by these assumptions.
1. The PV module is of the construction glass/encapsulant/cell/encapsulant/backsheet
2. The cell is opaque at all wavelengths modeled

## Requirements

The TOMCAT framework requires the following.

1. The angularly- and spectrally-resolved optical absorption in each layer of the module. This can be calculated, for example, with the module ray-tracing simulations that are available in [SunSolve](https://www.pvlighthouse.com.au/sunsolve).
1. [COMSOL Multiphysics](https://www.comsol.com) and the COMSOL Heat Transfer Module, for conduction and radiation simulations
1. A COMSOL model of a PV system (an example is included)
1. Python and the Python functions, included in this repository, for preparing inputs to the COMSOL model. The python functions here have been tested in Python 3.6 with the environment described in `requirements.txt`. These packages can be installed with `pip install -r requirements.txt`
1. A weather input file, such as a TMY3 file

## Doing the example simulation

Before you customize the TOMCAT simulation to your needs, it is recommended to run the example simulation. This will familiarize you with the framework and will confirm that all of the tools are in place.

### Optical simulation
One way to obtain the angularly- and spectrally-resolved optical absorption in each layer of the module is to calculate it with SunSolve. This example illustrates that approach, but other optical models may be used to generate the optics file in the format specified below.  
1. Log into [SunSolve](https://www.pvlighthouse.com.au/sunsolve), a cloud-based ray tracing tool for PV module optics  
1. Load the example file `example/TOMCAT example.sim` from this repository. Two important features are that the wavelength range of the simulation is extended beyond the bandgap to 2500 nm and that the angle of incidence is swept from 0 to near 90 degrees.
1. Run the SunSolve simulation 
1. Download a `.csv` of the reflection, absorption, transmission results ('Export RAT Data') in a single file
1. Generate the optics file from the RAT results with `tomcat_tmy.parse_pvl()`

#### Optics file format
The optics file details where solar radiation is absorbed within the module and photocurrent changes for different angles of incidence. It must be a `.csv` file with the following column names. Note that all values in the optics file should include cosine factors from angle of incidence.  
* `angle` The angle of incidence for solar illumination in degrees, 0 is normal  
* `glass_abs_W/m2` Absorbed energy in the front glass  
* `encapsulant_abs_W/m2` Absorbed energy in the front encapsulant  
* `cell_abs_W/m2` Absorbed energy in the front cell  
* `current_factor` The fractional change in photocurrent from relative to the value corresponding to the `efficiencyElectricalSTC` parameter in the FEM simulation

### Preparing time-series and tilt input files

1. Select a [TMY3](https://www.nrel.gov/docs/fy08osti/43156.pdf) weather file
1. Use `tomcat_tmy.generate_input()` to combine the weather file and the optics file into a **time-series file** named `TOMCAT_input.csv` and a **tilt file** named `TOMCAT_tilt.txt`

**The above example steps are shown in `example/example.py`**

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

Changes to optical properties or to the optical stack representing the PV module and solar cell should be made in the optical model of the module. Don't forget to propagate these changes through the TOMCAT optics file all the way to the time-series file.

### Changes to weather conditions

Weather files from any of the [>1000 TMY3 locations](https://rredc.nrel.gov/solar/old_data/nsrdb/1991-2005/tmy3/) can be used without modification.

Weather data from other sources, for instance from local meteorological measurement stations with higher measurement frequency than hourly, can also be used. Because every met station is different, it is the user's responsibility to ensure that local weather data are used correctly to generate the time-series input file. File formats other than TMY3 may be accommodated through modification of `generate_input()`.

### Thermal, electrical, and geometric changes

Thermal properties, layer thicknesses, electrical properties, and several PV system parameters are set in the COMSOL file, `TOMCAT_TMY.java`. They can be changed manually or programmatically before compiling and running a new simulation. These parameters can also be changed manually using the Global Definitions: Parameters node of the model in the COMSOL GUI.

## Improving TOMCAT

Formal development of TOMCAT ended on 30 September, 2018. Users are encouraged to fork this repository and implement improvements themselves. Suggested improvements include the following.

1. Improve TOMCAT's very simple convection model to include tilt-dependent natural and forced convection, accounting for differences due to wind direction
1. Replace the heat conduction and radiation simulation capabilities of COMSOL with Python implementations of a radiation view factor model (already developed for short-wave radiation in bifacial PV) and a heat conduction model (countless simple implementations exist)

## Citing TOMCAT

If you use part or all of TOMCAT, please cite it, including the version number and url of this repository.

Please also cite the following paper, which describes an early version of TOMCAT:

> T J Silverman, M G Deceglie, I Subedi, N J Podraza, I M Slauch, V E Ferry, I Repins. [Reducing operating temperature in photovoltaic modules](https://ieeexplore.ieee.org/document/8252698/). IEEE Journal of Photovoltaics, 2018.

## References

> T J Silverman, M G Deceglie, I Subedi, N J Podraza, I M Slauch, V E Ferry, I Repins. [Reducing operating temperature in photovoltaic modules](https://ieeexplore.ieee.org/document/8252698/). IEEE Journal of Photovoltaics, 2018.

> I M Slauch, M G Deceglie, T J Silverman, V E Ferry. [Spectrally selective mirrors with combined optical and thermal benefit for photovoltaic module thermal management](https://pubs.acs.org/doi/abs/10.1021/acsphotonics.7b01586). ACS Photonics, 2018.

## Acknowledgment

This work was authored in part by the National Renewable Energy Laboratory, operated by Alliance for Sustainable Energy, LLC, for the U.S. Department of Energy (DOE) under Contract No. DE-AC36-08GO28308. Funding was provided by the U.S. Department of Energy Office of Energy Efficiency and Renewable Energy Solar Energy Technologies Office under agreement number 30312. The views expressed in the article do not necessarily represent the views of the DOE or the U.S. Government. The U.S. Government retains and the publisher, by accepting the article for publication, acknowledges that the U.S. Government retains a nonexclusive, paid-up, irrevocable, worldwide license to publish or reproduce the published form of this work, or allow others to do so, for U.S. Government purposes.
