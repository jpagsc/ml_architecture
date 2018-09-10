import time
import sys
import schedule
import logging
import pandas as pd
import level_2_optionals_baviera_options
from level_1_a_data_acquisition import read_csv, log_files
from level_1_b_data_processing import lowercase_column_convertion, remove_rows, remove_columns, string_replacer, date_cols, options_scraping, color_replacement, new_column_creation, score_calculation, duplicate_removal, reindex, total_price, margin_calculation, col_group, new_features_optionals_baviera, z_scores_function, ohe, global_variables_saving, prov_replacement, dataset_split
from level_1_c_data_modelling import model_training
from level_1_d_model_evaluation import performance_evaluation, model_choice
from level_1_e_deployment import save_csv
pd.set_option('display.expand_frame_repr', False)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S @ %d/%m/%y', filename='logs/optionals_baviera.txt', filemode='a')
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def main():
    logging.info('Project: Baviera Stock Optimization')
    # log_files('optional_baviera')

    ### Options:
    # input_file = 'dbs/' + 'ENCOMENDA.csv'
    input_file = 'dbs/' + 'testing_ENCOMENDA.csv'
    output_file = 'output/' + 'db_full_baviera.csv'
    stockdays_threshold, margin_threshold = 45, 3.5
    target_variable = ['new_score']  # possible targets = ['stock_class1', 'stock_class2', 'margem_class1', 'score_class', 'new_score']
    oversample_check = 0
    models = ['dt', 'rf']
    # models = ['dt', 'rf', 'lr']
    k = 10
    gridsearch_score = 'recall'
    metric = 'accuracy'
    metric_threshold = 0.8
    # evaluation_metrics = ['micro', 'average', 'macro', 'accuracy', 'precision', 'recall', 'classification_report']
    ###

    df = data_acquistion(input_file)
    df, train_x, train_y, test_x, test_y = data_processing(df, stockdays_threshold, margin_threshold, target_variable, oversample_check)
    model_predictions, classes, running_times = data_modelling(df, train_x, train_y, test_x, test_y, models, k, gridsearch_score, oversample_check)
    model_evaluation(models, model_predictions, running_times, classes, metric, metric_threshold, train_y, test_y)
    deployment()

    # df = pd.DataFrame()
    # save_csv(df, 'logs/optionals_baviera_ran.csv')

    # sys.stdout.flush()
    logging.info('Finished - Project: Baviera Stock Optimization\n')
    # return schedule.CancelJob


def data_acquistion(input_file):
    # print(time.strftime("%H:%M:%S @ %d/%m/%y"), '- Started Step A...')
    logging.info('Started Step A...')

    # df = read_csv(input_file, delimiter=';', parse_dates=['Data Compra', 'Data Venda'], infer_datetime_format=True, decimal=',')
    df = read_csv(input_file, delimiter=';', encoding='latin-1', parse_dates=['Data Compra', 'Data Venda'], infer_datetime_format=True, decimal=',')

    logging.info('Finished Step A.')
    # print(time.strftime("%H:%M:%S @ %d/%m/%y"), '- Finished Step A.')

    return df


def data_processing(df, stockdays_threshold, margin_threshold, target_variable, oversample_check):
    # print(time.strftime("%H:%M:%S @ %d/%m/%y"), '- Started Step B...')
    logging.info('Started Step B...')

    df = lowercase_column_convertion(df, ['Opcional', 'Cor', 'Interior'])
    df = remove_rows(df, [df.loc[df['Opcional'] == 'preço de venda', :].index])

    dict_strings_to_replace = {('Modelo', ' - não utilizar'): '', ('Interior', '|'): '/', ('Cor', '|'): '', ('Interior', 'ind.'): '', ('Interior', ']'): '/', ('Interior', '.'): ' ', ('Interior', '\'merino\''): 'merino', ('Interior', '\' merino\''): 'merino', ('Interior', '\'vernasca\''): 'vernasca'}
    df = string_replacer(df, dict_strings_to_replace)
    df = remove_columns(df, ['CdInt', 'CdCor'])  # Columns that have missing values which are needed
    df.dropna(axis=0, inplace=True)  # Removes all remaining NA's.

    df = new_column_creation(df, ['Navegação', 'Sensores', 'Cor_Interior', 'Caixa Auto', 'Cor_Exterior', 'Jantes'])

    dict_cols_to_take_date_info = {'buy_': 'Data Compra'}
    df = date_cols(df, dict_cols_to_take_date_info)
    df = options_scraping(df)
    df = color_replacement(df)

    df = total_price(df)
    df = duplicate_removal(df, subset_col='Nº Stock')
    df = remove_columns(df, ['Cor', 'Interior', 'Versão', 'Opcional', 'A', 'S', 'Custo', 'Vendedor', 'Canal de Venda', 'Tipo Encomenda'])
    # Will probably need to also remove: stock_days, stock_days_norm, and one of the scores
    df = reindex(df)

    # print(time.strftime("%H:%M:%S @ %d/%m/%y"), '- Checkpoint B.1...')
    logging.info('Checkpoint B.1...')
    # ToDO: Checkpoint B.1 - this should be the first savepoint of the df. If an error is found after this point, the code should check for the df of this checkpoint

    df = remove_rows(df, [df[df.Modelo.str.contains('Série')].index, df[df.Modelo.str.contains('Z4')].index, df[df.Modelo.str.contains('MINI')].index, df[df['Prov'] == 'Demonstração'].index, df[df['Prov'] == 'Em utilização'].index])
    df = margin_calculation(df)
    df = score_calculation(df, stockdays_threshold, margin_threshold)

    cols_to_group = ['Cor_Exterior', 'Cor_Interior', 'Jantes', 'Local da Venda', 'Modelo']
    dictionaries = [level_2_optionals_baviera_options.color_ext_dict, level_2_optionals_baviera_options.color_int_dict, level_2_optionals_baviera_options.jantes_dict, level_2_optionals_baviera_options.sales_place_dict, level_2_optionals_baviera_options.model_dict]
    df = col_group(df, cols_to_group, dictionaries)
    df = prov_replacement(df)
    df = new_features_optionals_baviera(df, sel_cols=['Navegação', 'Sensores', 'Caixa Auto', 'Cor_Exterior_new', 'Cor_Interior_new', 'Jantes_new', 'Modelo_new'])

    global_variables_saving(df, project='optionals_baviera')
    df = z_scores_function(df, cols_to_normalize=['price_total', 'number_prev_sales', 'last_margin', 'last_stock_days'])

    ### Need to remove: 'Data Venda', 'Data Compra', 'Margem', 'Nº Stock'

    # df = df_copy(df)
    ohe_cols = ['Jantes_new', 'Cor_Interior_new', 'Cor_Exterior_new', 'Local da Venda_new', 'Modelo_new', 'Prov_new', 'buy_day', 'buy_month', 'buy_year']
    df_ohe = df.copy(deep=True)
    df_ohe = ohe(df_ohe, ohe_cols)
    train_x, train_y, test_x, test_y = dataset_split(df_ohe[[x for x in df_ohe if x not in ['Data Venda', 'Data Compra', 'Margem', 'Nº Stock']]], target_variable, oversample_check)

    logging.info('Finished Step B.')
    # print(time.strftime("%H:%M:%S @ %d/%m/%y"), '- Finished Step B.')

    return df, train_x, train_y, test_x, test_y


def data_modelling(df, train_x, train_y, test_x, test_y, models, k, score, oversample_check, voting=0):
    # print(time.strftime("%H:%M:%S @ %d/%m/%y"), '- Started Step C...')
    logging.info('Started Step C...')

    if oversample_check:
        oversample_flag_backup, original_index_backup = train_x['oversample_flag'], train_x['original_index']
        remove_columns(train_x, ['oversample_flag', 'original_index'])

    predictions, classes, running_times = model_training(models, train_x, train_y, test_x, k, score, voting)

    # print(time.strftime("%H:%M:%S @ %d/%m/%y"), '- Finished Step C.')
    logging.info('Finished Step C.')

    return predictions, classes, running_times


def model_evaluation(models, model_predictions, running_times, classes, metric, metric_threshold, train_y, test_y):
    # print(time.strftime("%H:%M:%S @ %d/%m/%y"), '- Started Step D...')
    logging.info('Started Step D...')

    results_training, results_test = performance_evaluation(models, classes, model_predictions, running_times, train_y, test_y)
    # save_csv()  # ToDO: Save csv locally
    best_model_name, best_model_value = model_choice(results_test, metric, metric_threshold)
    print(best_model_name, best_model_value)

    # print(time.strftime("%H:%M:%S @ %d/%m/%y"), '- Finished Step D.')
    logging.info('Finished Step D.')


def deployment():
    # print(time.strftime("%H:%M:%S @ %d/%m/%y"), '- Started Step E...')
    logging.info('Started Step E...')

    # print(time.strftime("%H:%M:%S @ %d/%m/%y"), '- Finished Step E.')
    logging.info('Finished Step E.')


if __name__ == '__main__':
    main()
