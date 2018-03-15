import boto3
import sys
from botocore.exceptions import ClientError

class XDB:
    def __init__(self):
        self.connect()
        pass
       
    def connect(self):
        dynamodb = boto3.resource('dynamodb')
        # dynamodb = boto3.resource('dynamodb',
        #                           endpoint_url='http://localhost:8000',
        #                           region_name='eu-central-1')

        try:
            dynamodb.create_table(
                TableName='webuntis',
                KeySchema=[
                    {
                        'AttributeName': 'id',
                        'KeyType': 'HASH'
                    },
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'id',
                        'AttributeType': 'S'
                    },
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            self.table.meta.client.get_waiter('table_exists').wait(TableName='webuntis')
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                self.table = dynamodb.Table('lessons')
            else:
                raise
       
        self.table = dynamodb.Table('webuntis')
   
    def write_data(self, jsonString):
        self.table.put_item(
           Item={
                'id': 'data',
                'json': jsonString,
            }
        )
   
    def get_data(self):
        response = self.table.get_item(
            Key={
                'id': 'data'
            }
        )
        item = response['Item']
        return item['json']
   
def main():
    xdb=XDB()
    xdb.write_data('teststring')
    s=xdb.get_data()
    print(s)

# main
if __name__ == '__main__': 
    main(*sys.argv[1:])