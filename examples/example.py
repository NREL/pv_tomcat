# This example shows how to translate SunSolve results into the input files needed
# for TOMCAT's FEM simulation.

import sys
sys.path.append('..')
import tomcat_tmy

# parse PV Lighthouse SunSolve results
glass_columns = [
    'Absorbed Top interface #1',
    'Absorbed Top layer #1 (Glass)'
]

front_encapsulant_columns = [
    'Absorbed Top interface #2',
    'Absorbed Top layer #2 (EVA)'
]

cell_columns = [
    'Absorbed Solar cell top (interface #3)',
    'Absorbed Solar cell bulk (layer #3)',
    'Absorbed Solar cell bottom (interface #4)'
]

photocurrent_columns = ['Absorbed Solar cell bulk (layer #3)']


# The following line generates optics.csv
tomcat_tmy.parse_pvl('MRT RAT data - TOMCAT example - All data.csv', glass_columns,
                     front_encapsulant_columns, cell_columns, photocurrent_columns)

# The following line generates TOMCAT_input.csv and TOMCAT_tilt.txt
# based on TMY3 file 725650TYA.CSV and optics file optics.csv
tomcat_tmy.generate_input('725650TYA.CSV', 'optics.csv')

# Refer to the readme for how to use these files to run the FEM simulation
