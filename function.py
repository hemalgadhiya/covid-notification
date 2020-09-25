import pandas as pd
import boto3
from io import StringIO
import logging
import json
def lambda_handler(event, context):

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    url_nyt = "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us.csv"
    url_john_hopkins = "https://raw.githubusercontent.com/datasets/covid-19/master/data/time-series-19-covid-combined.csv"

    s3 = boto3.client('s3')

    bucket = "nyt-jh-covid-data"
    key = "nyt_data.csv"

    db = boto3.resource('dynamodb')
    table = db.Table('covid_data')

    df_nyt_new = pd.read_csv(url_nyt, names=["Date","Confirmed", "Deaths"])
    # logger.info("Last row of new NYT data: ", df_nyt_new.iloc[[-1]])
    # print("Last row of new NYT data: ", df_nyt_new.iloc[[-1]])
    try:
        nyt_data = s3.get_object(Bucket=bucket, Key=key)['Body']
        logger.info("Got old NYT data from S3")
        df_nyt_old = pd.read_csv( nyt_data , names=["Date", "Confirmed", "Deaths"])
        # logger.info("Last row of old NYT data: ", df_nyt_old.iloc[[-1]])
        # print("Last row of old NYT data: ", df_nyt_old.iloc[[-1]])
    except s3.exceptions.NoSuchKey as e:
        logger.info("Key {key} found in S3".format(key=key))
        # print("Key {key} found in S3".format(key=key))
        df_nyt_old = pd.DataFrame()

    df_nyt_updated = pd.concat([df_nyt_new, df_nyt_old]).drop_duplicates(keep=False)


    if df_nyt_updated['Date'].count() > 1:
        logger.info("NYT data updated with {} rows ".format(df_nyt_updated['Date'].count()))
        # print("NYT data updated with {} rows ".format(df_nyt_updated['Date'].count()))
        logger.info("Updated Data: {}".format(df_nyt_updated.head()))
        # print("Updated Data: {}".format(df_nyt_updated.head()))


        df_jh = pd.read_csv(url_john_hopkins)
        US_data = df_jh.loc[df_jh['Country/Region']=="US"]
        logger.info("Merged NYD and JH data")
        # print("Merged NYD and JH data")
        df_nyt_updated = df_nyt_updated.merge(US_data, on='Date')
        # logger.info("Last row of Merged: ", df_nyt_updated.iloc[[-1]])
        # print("Last row of new NYT data: ", df_nyt_updated.iloc[[-1]])

        df_nyt_updated = df_nyt_updated.drop(['Confirmed_y', 'Deaths_y', 'Country/Region', 'Province/State', 'Lat', 'Long'], axis=1)

        df_nyt_updated['Date'] = pd.to_datetime(df_nyt_updated['Date'])
        date = list(df_nyt_updated['Date'])
        cases = list(df_nyt_updated['Confirmed_x'])
        deaths = list(df_nyt_updated['Deaths_x'])
        recovered = list(df_nyt_updated['Recovered'])
        data = []
        for i in range(len(date)):
            obj = {}
            obj['date'] = date[i]
            obj['cases'] = cases[i]
            obj['deaths'] = deaths[i]
            obj['recovered'] = recovered[i]
            data.append(obj)


        for c_data in data:
            c_data['date'] = str(c_data['date'])
            c_data['recovered'] = int(c_data['recovered'])
            table.put_item(Item=c_data)
            logger.info("{} data uploaded".format(c_data['date']))

    # upload new NYT data to s3
        csv_buffer = StringIO()
        df_nyt_new.to_csv(csv_buffer)
        s3.put_object(Bucket=bucket, Key=key, Body=csv_buffer.getvalue())
        logger.info("New NYT data uploaded to S3")
        return {
            'statusCode': 200,
            'body': json.dumps('Update Success')
        }
    else:
        logger.info("No Data Updated in NYT")
        return {
            'statusCode': 200,
            'body': json.dumps('No Data Updated')
        }







