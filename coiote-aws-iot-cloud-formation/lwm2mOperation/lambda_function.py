import json
import os

import requests
import boto3
from dataclasses import dataclass
from OpenSSL.crypto import X509, PKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography import x509


REST_URI = os.environ['coioteDMrestUri'] + '/api/coiotedm/v3'


class Pkcs12Context(requests.packages.urllib3.contrib.pyopenssl.OpenSSL.SSL.Context):
    def __init__(self, method):
        super().__init__(method)
        certificate = getCoioteSecrets()
        cert = x509.load_pem_x509_certificate(str.encode(certificate.certificatePem))
        pkey = load_pem_private_key(str.encode(certificate.privateKey), None)
        self.use_certificate(X509.from_cryptography(cert))
        self.use_privatekey(PKey.from_cryptography_key(pkey))


@dataclass
class UserAuthCert:
    certificatePem: str
    privateKey: str


def getCoioteSecrets() -> UserAuthCert:
    secretName = "coioteDMrest"

    session = boto3.session.Session()
    client = session.client('secretsmanager')

    try:
        getSecretValueResponse = client.get_secret_value(
            SecretId=secretName
        )
    except Exception:
        raise Exception('Coiote DM credentials not found in Secrets Manager')

    if 'SecretString' not in getSecretValueResponse:
        raise Exception('Coiote DM credentials are not set up correctly')

    secretsMap = json.JSONDecoder().decode(getSecretValueResponse['SecretString'])

    certificatePemKey = 'certificatePem'
    privateKeyKey = 'privateKey'

    expectedKeysSet = {certificatePemKey, privateKeyKey}
    fetchedKeysSet = set(secretsMap.keys())

    if expectedKeysSet.issubset(fetchedKeysSet):
        return UserAuthCert(
            certificatePem=secretsMap[certificatePemKey],
            privateKey=secretsMap[privateKeyKey],
        )
    else:
        raise Exception(f'Secret in Secrets Manager does not have all required keys ({", ".join(expectedKeysSet)})')


def lambda_handler(event, context):
    if 'keys' not in event:
        #Results of print functions are logged in CloudWatch when debugging is enabled
        #Results of return seem to be not logged there
        print('Error: keys must be specified')
        return {
            'statusCode': 400,
            'body': '{"error":"keys must be specified"}'
        }
    else:
        keys = event['keys']

    def pathsOptimization(keys):
        if any(element in keys for element in ('all','','.','/')):
            keysCsStr=''
        else:
            i=0
            for key in keys:
                if not key.endswith('.'):
                    keys[i] = key+'.'
                i+=1
            keys = list(set(keys))
            keys.sort()
            i=0
            jEnd=len(keys)
            for key in keys:
                j=i+1
                while j < jEnd:
                    if keys[j].startswith(key):
                        del keys[j]
                        j-=1
                        jEnd-=1
                    j+=1
                i+=1
            i=0
            for key in keys:
                keys[i] = key[:-1]
                i+=1
            keysCsStr = ','.join(keys)
        return keysCsStr

    if not 'operation' in event:
        print('Error: operation must be specified')
        return {
            'statusCode': 400,
            'body': '{"error":"operation must be specified"}'
        }
    else:
        operation = event['operation']
        #print('Operation is '+operation)
        thingName = event['thingName']

        if operation == 'write':
            i=0
            for key in keys:
                if key.endswith('.'):
                    keys[i] = key[:-1]
                i+=1
            if len(keys) != len(set(keys)):
                print('Error: keys must be unique for write operation')
                return {
                    'statusCode': 400,
                    'body': '{"error":"keys must be unique for write operation"}'
                }
            if 'values' in event:
                values = event['values']
                if len(keys) != len(values):
                    print('Error: The number of keys must be equal to the number of values')
                    return {
                        'statusCode': 400,
                        'body': '{"error":"The number of keys must be equal to the number of values"}'
                    }
            else:
                print('Error: You must specify values when write operation is used')
                return {
                    'statusCode': 400,
                    'body': '{"error":"You must specify values when write operation is used"}'
                }
            keysCsStr = ','.join(keys)
            #valuesCsStr = ','.join(values)
            valuesCsStr = ','.join([str(x) for x in values])
            body='{"templateName":"AWSwrite","config":{"parameters":[{"name":"keys","value":"'+keysCsStr+'"},{"name":"values","value":"'+valuesCsStr+'"}]}}'

        elif operation == 'read':
            keysCsStr = pathsOptimization(keys)
            body='{"templateName":"AWSread","config":{"parameters":[{"name":"keys","value":"'+keysCsStr+'"}]}}'

        elif operation == 'readComposite':
            keysCsStr = pathsOptimization(keys)
            body='{"templateName":"AWSreadComposite","config":{"parameters":[{"name":"keys","value":"'+keysCsStr+'"}]}}'

        elif operation == 'observe':
            i=0
            for key in keys:
                if not key.endswith('.'):
                    keys[i] = key+'.'
                i+=1
            if len(keys) != len(set(keys)):
                print('Error: keys must be unique for observe operation')
                return {
                    'statusCode': 400,
                    'body': '{"error":"keys must be unique for observe operation"}'
                }
            if 'attributes' in event:
                attributes = event['attributes']
                if len(keys) != len(attributes):
                    print('Error: The number of keys must be equal to the number of attributes')
                    return {
                        'statusCode': 400,
                        'body': '{"error":"The number of keys must be equal to the number of attributes"}'
                    }
            else:
                print('Error: You must specify attributes when observe operation is used')
                return {
                    'statusCode': 400,
                    'body': '{"error":"You must specify attributes when observe operation is used"}'
                }
            keysAttributesDict = dict(zip(keys,attributes))
            attributes.clear()
            keys.sort()
            i=0
            jEnd=len(keys)
            for key in keys:
                j=i+1
                while j < jEnd:
                    if keys[j].startswith(key):
                        del keys[j]
                        j-=1
                        jEnd-=1
                    j+=1
                i+=1
            i=0
            for key in keys:
                keys[i] = key[:-1]
                #key = key[:-1]
                #keys[i] = key
                attributes.append(keysAttributesDict[key])
                i+=1
            keysCsStr = ','.join(keys)
            ###attributesCsStr = str(attributes)[1:-1].replace(" ","")
            attributesStr = str(attributes).replace(" ","")
            #keysCsStr = pathsOptimization(keys)
            body='{"templateName":"AWSobserve","config":{"parameters":[{"name":"keys","value":"'+keysCsStr+'"},{"name":"attributes","value":"'+attributesStr+'"}]}}'

        elif operation == 'observeComposite':
            keys = list(set(keys))
            keysCsStr = ','.join(keys)
            body='{"templateName":"AWSobserveComposite","config":{"parameters":[{"name":"keys","value":"'+keysCsStr+'"}]}}'

        elif operation == 'execute':
            if len(keys) != 1:
                print('Error: Only one LwM2M path can be passed for execute operation - keys array must contain only one element')
                return {
                    'statusCode': 400,
                    'body': '{"error":"Only one LwM2M path can be passed for execute operation - keys array must contain only one element"}'
                }
            if not 'arguments' in event:
                body='{"templateName":"AWSexecute","config":{"parameters":[{"name":"keys","value":"'+keys[0]+'"}]}}'
            else:
                arguments = event['arguments']
                if arguments is not None:
                    body='{"templateName":"AWSexecute","config":{"parameters":[{"name":"keys","value":"'+keys[0]+'"},{"name":"arguments","value":"'+arguments+'"}]}}'
                else:
                    body='{"templateName":"AWSexecute","config":{"parameters":[{"name":"keys","value":"'+keys[0]+'"}]}}'

        elif operation == 'cancelObserve':
            # even if there are other keys in 'keys', set it to be just 'all' if 'keys' contains 'all'
            if 'all' in keys:
                keysCsStr = 'all'
            else:
                keys = list(set(keys))
                keysCsStr = ','.join(keys)
            body='{"templateName":"AWScancelObserve","config":{"parameters":[{"name":"keys","value":"'+keysCsStr+'"}]}}'

        elif operation == 'cancelObserveComposite':
            keys = list(set(keys))
            keysCsStr = ','.join(keys)
            body='{"templateName":"AWScancelObserveComposite","config":{"parameters":[{"name":"keys","value":"'+keysCsStr+'"}]}}'

        elif operation == 'writeAttributes':
            i=0
            for key in keys:
                if not key.endswith('.'):
                    keys[i] = key+'.'
                i+=1
            if len(keys) != len(set(keys)):
                print('Error: keys must be unique for writeAttributes operation')
                return {
                    'statusCode': 400,
                    'body': '{"error":"keys must be unique for writeAttributes operation"}'
                }
            if 'attributes' in event:
                attributes = event['attributes']
                if len(keys) != len(attributes):
                    print('Error: The number of keys must be equal to the number of attributes')
                    return {
                        'statusCode': 400,
                        'body': '{"error":"The number of keys must be equal to the number of attributes"}'
                    }
            else:
                print('Error: You must specify attributes when writeAttributes operation is used')
                return {
                    'statusCode': 400,
                    'body': '{"error":"You must specify attributes when writeAttributes operation is used"}'
                }
            i=0
            for key in keys:
                keys[i] = key[:-1]

                i+=1
            keysCsStr = ','.join(keys)
            attributesStr = str(attributes).replace(" ","").replace("None","''")
            body='{"templateName":"AWSwriteAttributes","config":{"parameters":[{"name":"keys","value":"'+keysCsStr+'"},{"name":"attributes","value":"'+attributesStr+'"}]}}'

        else:
            print('Error: operation '+operation+' is not implemented for AWS-CoioteDM integration')
            return {
                'statusCode': 406,
                'body': '{"error":"operation '+operation+' is not implemented for AWS-CoioteDM integration"}'
            }

        try:
            requests.packages.urllib3.contrib.pyopenssl.OpenSSL.SSL.Context = Pkcs12Context
        except Exception as ex:
            print('Error: ' + str(ex))
            return {
                'statusCode': 400,
                'body': '{"error":"' + str(ex) + '"}'
            }
        #uri=restUri+'/api/coiotedm/v3/tasksFromTemplates/deviceBlocking/'+thingName
        """
        in this approach, the task is scheduled at Coiote - and then we are performing 2nd call to trigger session even if a device is deregistered
        as the task has exec condition that it is executed only when the device is registered
        below resolved by 2nd exec condition - if a device is in queue mode, the task is executed once the device comes with some LwM2M message:
        we can also add an optional parameter in the shadow to wait for a device (by default set to false) and in this case not performing 2nd call triggering session
        If instead these 2 the method commented above is used, Coiote will respond with error indicating that the device is deregistered and the task will not be scheduled at all
        """
        uri = REST_URI+'/tasksFromTemplates/device/'+thingName
        headers = {'Content-Type': 'application/json', 'Authorization': 'Certificate'}
        apiCallResp = requests.post(uri, data=body, headers=headers)
        qjResponseCode = apiCallResp.status_code
        qjResponseBody = apiCallResp.text
        if qjResponseCode != 201:
            print('Error: Coiote DM responded with: ' + str(qjResponseCode) + ': ' + qjResponseBody)
            return {
                'statusCode': qjResponseCode,
                'body': qjResponseBody
            }

        uri = REST_URI+'/sessions/'+thingName+'/allow-deregistered'
        headers = {'Authorization': 'Certificate'}
        apiCallResp = requests.post(uri, headers=headers)
        qjResponseCode = apiCallResp.status_code
        qjResponseBody = apiCallResp.text
        if qjResponseCode != 200:
            print('Error: Coiote DM responded with: ' + str(qjResponseCode) + ': ' + qjResponseBody)

        return {
            'statusCode': qjResponseCode,
            'body': qjResponseBody
        }
