import boto3

client = boto3.client('iot')


def lambda_handler(event, context):
    # coioteDeviceType is for example anjay.demo_client
    thing_type = event['coioteDeviceType'].replace('.', ':')
    existing_thing_types = client.list_thing_types()['thingTypes']
    existing_thing_types_names = [thing['thingTypeName'] for thing in existing_thing_types]
    if thing_type not in existing_thing_types_names:
        client.create_thing_type(thing_type)
