import boto3

client = boto3.client('iot')


def lambda_handler(event, context):
    thing_name = event['coioteDeviceId']
    thing_type_name = event['coioteDeviceType']
    attribute_payload = {
        'attributes': {
            'protocol': 'LwM2M'
        },
        'merge': True
    }
    client.create_thing(thingName=thing_name, thingTypeName=thing_type_name, attributePayload=attribute_payload)
