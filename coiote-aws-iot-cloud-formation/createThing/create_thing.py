import boto3
import json

URL_ENCODED_COLON = '%3A'

iot_client = boto3.client('iot')
iot_data_client = boto3.client('iot-data')


def ensure_thing_type_exists(thing_type):
    existing_thing_types = iot_client.list_thing_types()['thingTypes']
    existing_thing_types_names = [thing['thingTypeName'] for thing in existing_thing_types]
    if thing_type not in existing_thing_types_names:
        iot_client.create_thing_type(thingTypeName=thing_type)

def extract_device_data(event):
    """
    We need to escape the URL-encoded colon for the device ID as we encode it on the Coiote's side.
    We also replace a dot with colon in the device type as the AWS disallows them in the thing type.
    """
    thing_name = event['coioteDeviceId'].replace(URL_ENCODED_COLON, ':')
    thing_type_name = event['coioteDeviceType'].replace('.', ':')
    return thing_name, thing_type_name

def lambda_handler(event, context):
    thing_name, thing_type_name = extract_device_data(event)
    ensure_thing_type_exists(thing_type_name)
    attribute_payload = {
        'attributes': {
            'protocol': 'LwM2M'
        },
        'merge': True
    }
    iot_client.create_thing(thingName=thing_name, thingTypeName=thing_type_name, attributePayload=attribute_payload)
    payload = json.dumps({"state": {}}).encode('utf-8')
    iot_data_client.update_thing_shadow(thingName=thing_name, shadowName='operation', payload=payload)
