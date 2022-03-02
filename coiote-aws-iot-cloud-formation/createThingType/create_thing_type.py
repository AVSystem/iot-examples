import boto3

client = boto3.client('iot')

# coioteDeviceType is for example anjay.demo_client
def extract_device_type(event):
    return event['coioteDeviceType'].replace('.', ':')

def lambda_handler(event, context):
    thing_type = extract_device_type(event)
    existing_thing_types = client.list_thing_types()['thingTypes']
    existing_thing_types_names = [thing['thingTypeName'] for thing in existing_thing_types]
    if thing_type not in existing_thing_types_names:
        client.create_thing_type(thing_type)
