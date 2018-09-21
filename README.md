# pv_tomcat
TOMCAT is a simulation framework for predicting photovoltaic (PV) cell operating temperature as a function of measurable optical and thermal module properties and ambient weather conditions. It is designed to support research into innovative methods for increasing energy yield through reduced operating temperature.

## Requirements

The TOMCAT framework requires the following.

1. [SunSolve](https://www.pvlighthouse.com.au/sunsolve), for ray-tracing simulations of module optics
1. A SunSolve model of a PV module, one of which is included in this repository
1. [COMSOL Multiphysics](https://www.comsol.com) and the COMSOL Heat Transfer Module, for conduction and radiation simulations
1. A COMSOL model of a PV system, one of which is included in this repository
1. The Python functions, included in this repository, for preparing inputs to the COMSOL model
1. A weather input file, such as a TMY3 file

## Generating FEM input files

The following example generates two input files for FEM calculations: `TOMCAT_input.csv` contains time-series inputs and `TOMCAT_tilt.txt` contains the array tilt. The `generate_input` function creates these files based on [TMY3](https://www.nrel.gov/docs/fy08osti/43156.pdf) and optics input files.

```python
from tomcat_tmy import generate_input

input_df = generate_input(tmy_file, optics_file, out_file_time_series='TOMCAT_input.csv', out_file_tilt='TOMCAT_tilt.txt')
```

## Optics input file format

The optics file details where solar radiation is absorbed within the module and photocurrent changes for different angles of incidence. It must be a `.csv` file with the following column names. Note that all values should include cosine losses from angle of incidence.  
`angle` The angle of incidence for solar illumination in degrees, 0 is normal  
`glass_abs_W/m2` Absorbed energy in the front glass  
`encapsulant_abs_W/m2` Absorbed energy in the front encapsulant  
`cell_abs_W/m2` Absorbed energy in the front cell  
`current_factor` The fractional change in photocurrent from relative to the value corresponding to the `efficiencyElectricalSTC` parameter in the FEM simulation

## Executing the COMSOL run

Place `TOMCAT_input.csv` and `TOMCAT_tilt.txt` in the same directory as `TOMCAT_TMY.class`, which is a compiled version of `TOMCAT_TMY.java`. Execute your system's equivalent of

```comsol batch -inputfile /path/to/wherever/you/put/TOMCAT_TMY.class -nosave```

This will automatically produce `ModelOutput_Power.csv` and `ModelOutput_Temperature.csv` results files when the run is complete.

An example `TOMCAT_TMY.class` file and the `TOMCAT_TMY.java` file it is based on are provided.
