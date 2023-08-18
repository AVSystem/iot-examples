import json
import os
from tempfile import NamedTemporaryFile
from dataclasses import dataclass
from typing import TypedDict

import boto3
import requests

REST_URI = os.environ['coioteDMrestUri'] + '/api/coiotedm/v3'


class OperationHttpStatus(TypedDict):
    statusCode: int
    body: str


def operation_error(code: int, error: str) -> OperationHttpStatus:
    return OperationHttpStatus(
        statusCode=code,
        body=json.dumps({
            'error': error
        })
    )


def get_certificate_files():
    user_auth_cert = get_user_auth_cert()
    certificate_pem = NamedTemporaryFile(delete=False)
    private_key = NamedTemporaryFile(delete=False)
    certificate_pem_file = certificate_pem.name
    private_key_file = private_key.name
    try:
        certificate_pem.write(str.encode(user_auth_cert.certificatePem))
        private_key.write(str.encode(user_auth_cert.privateKey))
        certificate_pem.close()
        private_key.close()
        yield certificate_pem_file, private_key_file
    finally:
        os.unlink(certificate_pem_file)
        os.unlink(private_key_file)


@dataclass
class UserAuthCert:
    certificatePem: str
    privateKey: str


def get_user_auth_cert() -> UserAuthCert:
    secret_name = 'coioteDMcert'

    session = boto3.session.Session()
    client = session.client('secretsmanager')

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except Exception:
        raise Exception('Coiote DM certificate not found in Secrets Manager')

    if 'SecretString' not in get_secret_value_response:
        raise Exception('Coiote DM certificate are not set up correctly')

    secrets_map = json.JSONDecoder().decode(
        get_secret_value_response['SecretString'])

    certificate_pem_key = 'certificatePem'
    private_key_key = 'privateKey'

    expected_keys_set = {certificate_pem_key, private_key_key}
    fetched_keys_set = set(secrets_map.keys())

    if expected_keys_set.issubset(fetched_keys_set):
        return UserAuthCert(
            certificatePem=secrets_map[certificate_pem_key],
            privateKey=secrets_map[private_key_key],
        )
    else:
        raise Exception(
            f'Secret in Secrets Manager does not have all required keys ({", ".join(expected_keys_set)})')


def get_device_db_id(endpoint_name, certificate, private_key):
    uri = REST_URI + "/devices"
    condition = f"properties.endpointName eq '{endpoint_name}'"
    params = {
        "searchCriteria": condition
    }
    response = requests.get(uri, params=params, cert=(
        certificate, private_key), verify=False)
    return response.json()[0]


def lambda_handler(event, context):
    if 'keys' not in event:
        # Results of print functions are logged in CloudWatch when debugging is enabled
        # Results of return seem to be not logged there
        print('Error: keys must be specified')
        return operation_error(400, 'keys must be specified')
    else:
        keys = event['keys']

    def pathsOptimization(keys):
        if any(element in keys for element in ('all', '', '.', '/')):
            keysCsStr = ''
        else:
            i = 0
            for key in keys:
                if not key.endswith('.'):
                    keys[i] = key+'.'
                i += 1
            keys = list(set(keys))
            keys.sort()
            i = 0
            jEnd = len(keys)
            for key in keys:
                j = i+1
                while j < jEnd:
                    if keys[j].startswith(key):
                        del keys[j]
                        j -= 1
                        jEnd -= 1
                    j += 1
                i += 1
            i = 0
            for key in keys:
                keys[i] = key[:-1]
                i += 1
            keysCsStr = ','.join(keys)
        return keysCsStr

    if 'operation' not in event:
        print('Error: operation must be specified')
        return operation_error(400, 'operation must be specified')
    else:
        operation = event['operation']
        thingName = event['thingName']

        if operation == 'write':
            i = 0
            for key in keys:
                if key.endswith('.'):
                    keys[i] = key[:-1]
                i += 1

            if len(keys) != len(set(keys)):
                print('Error: keys must be unique for write operation')
                return operation_error(400, 'keys must be unique for write operation')

            if 'values' in event:
                values = event['values']
                if len(keys) != len(values):
                    print(
                        'Error: The number of keys must be equal to the number of values')
                    return operation_error(400, 'The number of keys must be equal to the number of values')
            else:
                print('Error: You must specify values when write operation is used')
                return operation_error(400, 'You must specify values when write operation is used')

            keysCsStr = ','.join(keys)
            valuesCsStr = ','.join([str(x) for x in values])
            body = {
                'templateName': 'AWSwriteCertAuth',
                'config': {
                    'parameters': [{'name': 'keys', 'value': keysCsStr}, {'name': 'values', 'value': valuesCsStr}]
                }
            }
        elif operation == 'read':
            keysCsStr = pathsOptimization(keys)
            body = {
                'templateName': 'AWSreadCertAuth',
                'config': {
                    'parameters': [{'name': 'keys', 'value': keysCsStr}]
                }
            }
        elif operation == 'readComposite':
            keysCsStr = pathsOptimization(keys)
            body = {
                'templateName': 'AWSreadCompositeCertAuth',
                'config': {
                    'parameters': [{'name': 'keys', 'value': keysCsStr}]
                }
            }
        elif operation == 'observe':
            i = 0
            for key in keys:
                if not key.endswith('.'):
                    keys[i] = key+'.'
                i += 1
            if len(keys) != len(set(keys)):
                print('Error: keys must be unique for observe operation')
                return operation_error(400, 'keys must be unique for observe operation')

            if 'attributes' in event:
                attributes = event['attributes']
                if len(keys) != len(attributes):
                    print(
                        'Error: The number of keys must be equal to the number of attributes')
                    return operation_error(400, 'The number of keys must be equal to the number of attributes')
            else:
                print(
                    'Error: You must specify attributes when observe operation is used')
                return operation_error(400, 'You must specify attributes when observe operation is used')

            keysAttributesDict = dict(zip(keys, attributes))
            attributes.clear()
            keys.sort()
            i = 0
            jEnd = len(keys)
            for key in keys:
                j = i+1
                while j < jEnd:
                    if keys[j].startswith(key):
                        del keys[j]
                        j -= 1
                        jEnd -= 1
                    j += 1
                i += 1

            i = 0
            for key in keys:
                keys[i] = key[:-1]
                # key = key[:-1]
                # keys[i] = key
                attributes.append(keysAttributesDict[key])
                i += 1

            keysCsStr = ','.join(keys)
            # attributesCsStr = str(attributes)[1:-1].replace(' ','')
            attributesStr = str(attributes).replace(' ', '')
            # keysCsStr = pathsOptimization(keys)
            body = {
                'templateName': 'AWSobserveCertAuth',
                'config': {
                    'parameters': [{'name': 'keys', 'value': keysCsStr}, {'name': 'attributes', 'value': attributesStr}]
                }
            }
        elif operation == 'observeComposite':
            keys = list(set(keys))
            keysCsStr = ','.join(keys)
            body = {
                'templateName': 'AWSobserveCompositeCertAuth',
                'config': {
                    'parameters': [{'name': 'keys', 'value': keysCsStr}]
                }
            }
        elif operation == 'execute':
            if len(keys) != 1:
                print(
                    'Error: Only one LwM2M path can be passed for execute operation - keys array must contain only one element')
                return operation_error(400, 'Only one LwM2M path can be passed for execute operation - keys array must contain only one element')
            if 'arguments' not in event:
                body = {
                    'templateName': 'AWSexecuteCertAuth',
                    'config': {
                        'parameters': [{'name': 'keys', 'value': keys[0]}]
                    }
                }
            else:
                arguments = event['arguments']
                if arguments is not None:
                    body = {
                        'templateName': 'AWSexecuteCertAuth',
                        'config': {
                            'parameters': [{'name': 'keys', 'value': keys[0]}, {'name': 'arguments', 'value': arguments}]
                        }
                    }
                else:
                    body = {
                        'templateName': 'AWSexecuteCertAuth',
                        'config': {
                            'parameters': [{'name': 'keys', 'value': keys[0]}]
                        }
                    }
        elif operation == 'cancelObserve':
            # even if there are other keys in 'keys', set it to be just 'all' if 'keys' contains 'all'
            if 'all' in keys:
                keysCsStr = 'all'
            else:
                keys = list(set(keys))
                keysCsStr = ','.join(keys)

            body = {
                'templateName': 'AWScancelObserveCertAuth',
                'config': {
                    'parameters': [{'name': 'keys', 'value': keysCsStr}]
                }
            }
        elif operation == 'cancelObserveComposite':
            keys = list(set(keys))
            keysCsStr = ','.join(keys)
            body = {
                'templateName': 'AWScancelObserveCompositeCertAuth',
                'config': {
                    'parameters': [{'name': 'keys', 'value': keysCsStr}]
                }
            }
        elif operation == 'writeAttributes':
            i = 0
            for key in keys:
                if not key.endswith('.'):
                    keys[i] = key+'.'
                i += 1
            if len(keys) != len(set(keys)):
                print('Error: keys must be unique for writeAttributes operation')
                return operation_error(400, 'keys must be unique for writeAttributes operation')
            if 'attributes' in event:
                attributes = event['attributes']
                if len(keys) != len(attributes):
                    print(
                        'Error: The number of keys must be equal to the number of attributes')
                    return operation_error(400, 'The number of keys must be equal to the number of attributes')
            else:
                print(
                    'Error: You must specify attributes when writeAttributes operation is used')
                return operation_error(400, 'You must specify attributes when writeAttributes operation is used')
            i = 0
            for key in keys:
                keys[i] = key[:-1]

                i += 1
            keysCsStr = ','.join(keys)
            attributesStr = str(attributes).replace(
                ' ', '').replace('None', "''")
            body = {
                'templateName': 'AWSwriteAttributesCertAuth',
                'config': {
                    'parameters': [{'name': 'keys', 'value': keysCsStr}, {'name': 'attributes', 'value': attributesStr}]
                }
            }
        else:
            print(
                f'Error: operation {operation} is not implemented for AWS-CoioteDM integration')
            return operation_error(406, f'operation {operation} is not implemented for AWS-CoioteDM integration')

        # in this approach, the task is scheduled at Coiote - and then
        # we are performing 2nd call to trigger session even if a device is deregistered
        # as the task has exec condition that it is executed only when the device is registered
        # below resolved by 2nd exec condition - if a device is in queue mode,
        # the task is executed once the device comes with some LwM2M message:
        # we can also add an optional parameter in the shadow to wait for a device (by default set to false)
        # and in this case not performing 2nd call triggering session
        # If instead these 2 the method commented above is used, Coiote will respond with
        # error indicating that the device is deregistered and the task will not be scheduled at all
        for certificate, private_key in get_certificate_files():
            device_id = get_device_db_id(thingName, certificate, private_key)
            uri = REST_URI+'/tasksFromTemplates/device/'+device_id
            headers = {'Authorization': 'Certificate'}
            apiCallResp = requests.post(uri, json=body, headers=headers, cert=(
                certificate, private_key), verify=False, timeout=10)
            qjResponseCode = apiCallResp.status_code
            qjResponseBody = apiCallResp.text
            if qjResponseCode != 201:
                print('Error: Coiote DM responded with: ' +
                      str(qjResponseCode) + ': ' + qjResponseBody)
                return OperationHttpStatus(
                    statusCode=qjResponseCode,
                    body=qjResponseBody
                )

            uri = REST_URI+'/sessions/'+device_id+'/allow-deregistered'
            apiCallResp = requests.post(uri, headers=headers, cert=(
                certificate, private_key), verify=False, timeout=10)
            qjResponseCode = apiCallResp.status_code
            qjResponseBody = apiCallResp.text
            if qjResponseCode != 200:
                print('Error: Coiote DM responded with: ' +
                      str(qjResponseCode) + ': ' + qjResponseBody)

            return OperationHttpStatus(
                statusCode=qjResponseCode,
                body=qjResponseBody
            )
