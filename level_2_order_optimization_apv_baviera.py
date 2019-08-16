import time
import sys
import logging
from level_0_performance_report import log_record, project_dict
from level_1_a_data_acquisition import dw_data_retrieval, autoline_data_retrieval
from level_1_b_data_processing import apv_dataset_treatment
from level_1_c_data_modelling import apv_stock_evolution_calculation, part_ref_selection, part_ref_ta_definition
from level_1_e_deployment import time_tags
import level_2_order_optimization_apv_baviera_options as options_file

update = 1  # Decides whether to fetch new datasets from the DW or not

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S @ %d/%m/%y', filename=options_file.log_files['full_log'], filemode='a')
logging.Logger('errors')
# logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))  # Allows the stdout to be seen in the console
logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))  # Allows the stderr to be seen in the console


def main():
    log_record('Project: Baviera APV Order Optimization', options_file.project_id)

    min_date = '20180131'  # This is a placeholder for the minimum possible date - It already searches for the last processed date.
    # max_date = '20190731'  # This will be replaced by current date

    max_date, _ = time_tags(format_date='%Y%m%d')
    print('Full Available Data: {} to {}'.format(min_date, max_date))

    df_sales, df_purchases, df_stock, df_reg, df_reg_al_clients, df_al = data_acquistion(options_file, max_date)
    df_sales_cleaned, df_purchases_cleaned, df_stock = data_processing(df_sales, df_purchases, df_stock, options_file)
    results = data_modelling(options_file.pse_code, df_sales_cleaned, df_al, df_stock, df_reg_al_clients, df_purchases_cleaned, min_date, max_date)

    log_record('Finished Successfully - Project: {} .\n'.format(project_dict[options_file.project_id]), options_file.project_id)


def data_acquistion(options_info, current_date):
    log_record('Started Step A...', options_file.project_id)

    pse_code = options_info.pse_code
    start = time.time()

    df_sales, df_purchases, df_stock, df_reg, df_reg_al_clients = dw_data_retrieval(pse_code, current_date, options_info, update)
    df_al = autoline_data_retrieval(pse_code, current_date)

    print('Elapsed time: {:.2f}'.format(time.time() - start))

    log_record('Finished Step A.', options_file.project_id)
    return df_sales, df_purchases, df_stock, df_reg, df_reg_al_clients, df_al


def data_processing(df_sales, df_purchases, df_stock, options_info):
    log_record('Sarted Step B...', options_file.project_id)
    start_treatment = time.time()

    df_sales, df_purchases, df_stock = apv_dataset_treatment(df_sales, df_purchases, df_stock, options_info.pse_code, options_info.urgent_purchases_flags, update)

    print('Elapsed time: {:.2f}'.format(time.time() - start_treatment))

    log_record('Finished Step B.', options_file.project_id)
    return df_sales, df_purchases, df_stock


def data_modelling(pse_code, df_sales, df_al, df_stock, df_reg_al_clients, df_purchases, min_date, max_date):
    log_record('Started Step C', options_file.project_id)
    start = time.time()

    if pse_code == '0I':
        selected_parts = ['BM83.21.2.405.675', 'BM07.12.9.952.104', 'BM07.14.9.213.164', 'BM83.19.2.158.851', 'BM64.11.9.237.555']  # PSE_Code = 0I, Lisboa - Expo
    if pse_code == '0B':
        selected_parts = ['BM83.21.0.406.573', 'BM83.13.9.415.965', 'BM51.18.1.813.017', 'BM11.42.8.507.683', 'BM64.11.9.237.555']  # PSE_Code = 0B, Gaia

    selected_parts = part_ref_selection(df_al, min_date, max_date)
    results = apv_stock_evolution_calculation(pse_code, selected_parts, df_sales, df_al, df_stock, df_reg_al_clients, df_purchases, min_date, max_date)
    part_ref_ta_definition(df_al, selected_parts, pse_code, max_date, [options_file.bmw_ta_mapping, options_file.mini_ta_mapping])  # This function deliberately uses the full amount of data, while i don't have a reliable source of TA - the more information, the less likely it is for the TA to be wrong
    # sales_solver(results)

    print('Elapsed time: {:.2f}'.format(time.time() - start))

    log_record('Finished Step C', options_file.project_id)
    return results


if __name__ == '__main__':
    try:
        main()
    except Exception as exception:
        log_record('Failed - Project: {}'.format(project_dict[options_file.project_id]), options_file.project_id)