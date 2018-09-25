import requests
import json
import numpy as np

def fetch_bos_cost_tree():
    '''Gets the BOS cost tree from NREL's online LCOE calculator'''

    # Load the BOS cost tree from the NREL online LCOE calculator
    bos_cost_tree = requests.get(
        'https://www.nrel.gov/pv/lcoe-calculator/js/bos_cost_tree.js'
    )
    # Parse the JSON
    bos_cost_tree = json.loads(bos_cost_tree.content.decode().split('=')[-1])
    return bos_cost_tree

def lcoe(cost_module=1.15*58.78, cost_om=15.40, r_degradation=0.36,
         r_discount=6.3, energy_yield=1475., service_life=25,
         state='MO', efficiency=19., bos_cost_tree=None,
         system_type='fixed tilt, utility scale'):
    
    '''Calculate LCOE using discounted cash flow and simple cost inputs
    This is a clone of the calculator at https://pvlcoe.nrel.gov .
    Further documentation is available there.
    
    The default values are correct (matching the web version of the
    calculator) as of 2018-09-24.
    
    cost_module in $/m^2
    cost_om in $/kW/year
    r_degradation rate in %/year
    r_discount in %
    energy_yield in h
    service life in year
    efficiency in %
    bos_cost_tree is a nested dict like at
        https://www.nrel.gov/pv/lcoe-calculator/js/bos_cost_tree.js
        If none is specified, this one will be loaded and used. Note
        that this can take a lot of extra time, so for repeated calls of
        lcoe(), consider loading bos_cost_tree once with an external
        call to fetch_bos_cost_tree() and passing the result to lcoe() 
    system_type is one of 'fixed tilt, utility scale',
        'single-axis tracked, utility scale', or
        'roof-mounted, residential scale'
    '''
    
    if bos_cost_tree is None:
        bos_cost_tree = fetch_bos_cost_tree()
    
    def cost(year):
        '''Give the PV system cost as a function of year'''
        if year == 0:
            return cost_module/(10.*efficiency)\
                + bos_cost_tree[system_type][state]['cost_bos_power']\
                + bos_cost_tree[system_type][state]['cost_bos_area']/(10.*efficiency)
        else:
            return cost_om/1000.

    def energy(year):
        '''Give the PV system energy output as a function of year'''
        if year == 0:
            return 0
        else:
            return max(energy_yield/1000.*np.power(
                (1.-r_degradation/100.), year-1), 0.
            )

    years = np.arange(service_life + 1)
    total_cost = np.sum([cost(year)/np.power(1.+r_discount/100., year) for year in years])
    total_energy = np.sum([energy(year)/np.power(1.+r_discount/100., year) for year in years])

    return total_cost/total_energy