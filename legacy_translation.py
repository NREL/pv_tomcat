import pandas as pd


def optics(file):
    '''
    Translates legacy optical results in file to the format
    required by tomcat_tmy.generate_input(). Each case in file
    generates a tomcat_tmy.generate_input() compliant csv.
    '''
    cols = ['case', 'angle', 'glass_abs_W/m2', 'EVA_abs_W/m2',
            'cell_abs_W/m2', 'current_derate']

    input_df = pd.read_csv(file)

    # 180 used to mean difuse, that is now calculated by tomcat_tmy.generate_input()
    input_df = input_df[input_df['angle'] != 180]
    input_df = input_df[cols]
    input_df.rename(columns={'current_derate': 'current_factor', 'EVA_abs_W/m2': 'encapsulant_abs_W/m2'}, inplace=True)

    cases = set(input_df['case'])

    cases

    for case in cases:
        case_df = input_df[input_df['case'] == case]
        case_df.to_csv(case + '_optics.csv', index=False)

    return
