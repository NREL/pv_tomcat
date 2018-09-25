import lcoe
import numpy as np
import scipy.optimize


# Do an LCOE calculation with the default values
lcoe_example = lcoe.lcoe()
print('Default-scenario LCOE: {} USD/kWh'.format(lcoe_example))

# Change the location (affecting BOS cost only)
lcoe_baseline = lcoe.lcoe(state='CO')
print('Default-scenario LCOE with BOS from CO: {} USD/kWh'.format(lcoe_baseline))

# Change location and energy yield
lcoe_proposed = lcoe.lcoe(state='CO', energy_yield=1589)
print('Default-scenario LCOE with BOS and energy yield from CO: {} USD/kWh'.format(lcoe_proposed))


# Do a batch of calculations very quickly by preloading the bos_cost_tree
bos_cost_tree = lcoe.fetch_bos_cost_tree()
print('Doing a batch of LCOE calculations based on the default scenario:')
for cost_module in np.linspace(0, 100, 10):
    print('Module cost: {} USD/m^2, LCOE: {} USD/kWh'.format(
        np.round(cost_module, 2),
        np.round(lcoe.lcoe(bos_cost_tree=bos_cost_tree, cost_module=cost_module), 4)
    ))

# Calculate breakeven cost of an additional module component (USD/m^2) based on some amount of extra energy
print('Calculating the breakeven cost:')
energy_factor = 1.1
cost_module = 1.15 * 58.78
lcoe_arguments = {'state': 'CO', 'bos_cost_tree': bos_cost_tree}
lcoe_baseline = lcoe.lcoe(energy_yield=1589, cost_module=cost_module, **lcoe_arguments)


def lcoe_difference(cost_extra):
    return lcoe.lcoe(energy_yield=1589 * energy_factor, cost_module=cost_module + cost_extra, **lcoe_arguments) - lcoe_baseline


breakeven_cost = scipy.optimize.newton(lcoe_difference, 0)
print('For a module that produces {}x as much energy, the additional cost can be up to {} USD/m^2'.format(
    np.round(energy_factor, 2),
    np.round(breakeven_cost, 2)
))