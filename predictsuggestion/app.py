import json
import csv
import pandas as pd
import numpy as np
import requests
from flask import jsonify, request
from flask_cors import CORS, cross_origin
from scipy.stats import pearsonr
from numpy import cov
from scipy import stats
import os
import flask

app = flask.Flask(__name__)
cors = CORS(app)
app.config["DEBUG"] = False

QTD_EXEC = 3
SET_POINT = 1375
MULTIPLO = 2
url = 'http://79773486-dc12-493e-a9b1-8c9ac605b286.brazilsouth.azurecontainer.io/score'
headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
contador = 1
listsample_input = []
percent_total = 0
firstjson = ''
df = ''
d = ''
contadorSuggest = 0


def correlation(dataset, threshold, columnname, setpointpercent, multiplo, jsonentrada, contador, epcorrOldValue,
                epcoorOldName):
    pcorrOldValue = 0
    pcoorOldName = ''
    col_corr = set()  # Set of all the names of deleted columns
    corr_matrix = dataset.corr()
    corr_old = 0
    for i in range(len(corr_matrix.columns)):
        for j in range(i):
            if corr_matrix.columns[i] == columnname:
                if (corr_matrix.iloc[i, j] >= threshold):  # and corr_matrix.columns[j].find('.C.') != -1:
                    if corr_matrix.columns[j].find('.C.') != -1 and contador == 0:
                        if pcorrOldValue == 0:
                            pcorrOldValue = float(corr_matrix.iloc[i, j])
                            pcoorOldName = corr_matrix.columns[j]

                        elif corr_matrix.iloc[i, j] > pcorrOldValue:
                            pcorrOldValue = float(corr_matrix.iloc[i, j])
                            pcoorOldName = corr_matrix.columns[j]
                    else:
                        pcorrOldValue = epcorrOldValue
                        pcoorOldName = epcoorOldName
                    colname = corr_matrix.columns[j]
                    pctcorrcol = (setpointpercent * corr_matrix.iloc[i, j]) * multiplo
                    # print(pctcorrcol)
                    # print(d['data'][0][colname])
                    valorAtual = float(jsonentrada['data'][0][colname])
                    jsonentrada['data'][0][colname] = (valorAtual * (pctcorrcol / 100)) + valorAtual
                    # print(d['data'][0][colname])
    return jsonentrada


def correlationpr(dataset, threshold, columnname, setpointpercent, multiplo, jsonentrada):
    col_corr = set()  # Set of all the names of deleted columns
    corr_matrix = dataset.corr()
    for i in range(len(corr_matrix.columns)):
        for j in range(i):
            data1 = df[columnname]
            if corr_matrix.columns[i] == columnname:
                data2 = df[corr_matrix.columns[j]]
                corr, _ = pearsonr(data1, data2)
                if corr >= threshold:  # and corr_matrix.columns[j].find('.C.') != -1:
                    colname = corr_matrix.columns[j]
                    pctcorrcol = (setpointpercent * corr) * multiplo
                    jsonentrada['data'][0][colname] = (d['data'][0][colname] * (pctcorrcol / 100)) + d['data'][0][
                        colname]


def calculatepercent(setpoint, value):
    if setpoint > value:
        percent_dif_set_point = ((setpoint * 100) / value) - 100
    else:
        percent_dif_set_point = 100 - ((setpoint * 100) / value)
    return percent_dif_set_point


def executamodelo(listsample_row, data, percent_total, contador):
    d = data
    requestdata = requests.post(url, data=json.dumps(d), headers=headers)
    sample_output = json.loads(requestdata.json())
    sample_output = sample_output.get('result')[0]
    print('Sugestão %i resultado: %.3f' % (contador, sample_output))
    novaPerformance = ((sample_output * 100) / SET_POINT)
    diff = novaPerformance - percent_total
    print('Performance anterior:%f Nova Performace:%f Diferença:%f %%' % (percent_total, novaPerformance, diff))
    listsample_row.append(contador)
    # listsample_row.append(firstjson)
    listsample_row.append(round(float(percent_total), 3))
    listsample_row.append(round(float(novaPerformance), 3))
    listsample_row.append(round(float(diff), 3))
    listsample_row.append(str(d))
    listsample_input.append(listsample_row)


@app.route("/")
@cross_origin()
def hello():
    return "Hello, World!"


@app.route('/getSuggestion', methods=['GET', 'POST'])
@cross_origin()
def getSuggestion():
    jsonString = None
    contador = 1
    corrOldValue = 0
    coorOldName = ''
    listsample_input.clear()

    d = request.get_json()
    firstjson = d

    if type(d) is not dict:
        d = json.loads(d)
    requestdata = requests.post(url, data=json.dumps(d), headers=headers)
    sample_output = json.loads(requestdata.json())
    sample_output = sample_output.get('result')[0]

    percent_dif_set_point = calculatepercent(SET_POINT, sample_output)

    percent_total = ((sample_output * 100) / SET_POINT)
    print('Execução atual: %.3f' % (sample_output))
    primeiraexec = float(sample_output);
    df = pd.read_csv('dataset_reduzido.csv', sep=';')

    percent_dif_set_point_median = None
    for x in range(0, QTD_EXEC):
        contadorSuggest = x + 1
        ############### CORRELAÇÃO ###############
        listsample_row = []
        data = correlation(df, 0.3, 'Stage1.Output.Measurement0.U.Actual', percent_dif_set_point,
                           MULTIPLO, d, x, corrOldValue, coorOldName);
        executamodelo(listsample_row, data, percent_total, contadorSuggest)
        contador = contador + 1
        # listsample_input.append(listsample_row)
        percent_dif_set_point = calculatepercent(SET_POINT, sample_output)

        ############### MEDIANA   ###############
        '''
        listsample_row_med = []
        print('test', coorOldName)
        if percent_dif_set_point_median is None:
            percent_dif_set_point_median = calculatepercent(df[coorOldName].median(), d['data'][0][coorOldName])
        print(percent_dif_set_point_median)
        corrOldValueMed, coorOldNameMed = correlation(df, 0.3, coorOldName, percent_dif_set_point_median, MULTIPLO, d,
                                                      x, corrOldValueMed, coorOldNameMed);
        executamodelo(listsample_row_med)
        listsample_input.append(listsample_row_med)
        percent_dif_set_point_median = calculatepercent(df[coorOldName].median(), d['data'][0][coorOldName])


    header = ['ExecNo', 'Origem', 'Performance Anterior', 'Nova Performance', 'Diferenca', 'Sugestao']
    arquivo = open("resultado.csv", "a")
    with open('test.csv', 'a', encoding='UTF8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC, delimiter=';')
        if contador == 1:
            writer.writerow(header)
        for x in range(0, len(listsample_input)):
            # print(listsample_input[x])
            writer.writerow(listsample_input[x])
    '''
    # contador = contador + 1

    jsonString = json.dumps(listsample_input)
    print(jsonString)
    return jsonString


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)