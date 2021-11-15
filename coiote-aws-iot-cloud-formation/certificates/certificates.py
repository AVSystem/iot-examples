import json
import os

import boto3
import requests
from crhelper import CfnResource
from OpenSSL import crypto

helper = CfnResource()
iot_client = boto3.client('iot')
secrets_manager_client = boto3.client('secretsmanager')

user = os.environ['coioteDMrestUsername']
password = os.environ['coioteDMrestPassword']
rest_uri = os.environ['coioteDMrestUri']
domain_id = os.environ['coioteDMrestDomainId']
group_id = os.environ['coioteDMrestGroupId']


@helper.create
def create(event, context):

    internal_certificate = iot_client.create_keys_and_certificate(setAsActive=True)
    external_certificate = generate_external_cert(email_address=user, common_name=user)
    ca_result = requests.get('https://www.amazontrust.com/repository/AmazonRootCA1.pem')
    internal_cert_ca = ca_result.content.decode('UTF-8')

    body = '{"domainId": "' + domain_id + '","groupId": "' + group_id + '","username": "' + user + \
        '","internalCertificate": {"certificatePem": "' + internal_certificate['certificatePem'] + \
        '","privateKey": "' + internal_certificate['keyPair']['PrivateKey'] + '", "certificateAuthority": "' + \
        internal_cert_ca + '"},"externalCertificate": {"certificatePem": "' + \
        external_certificate['certificatePem'] + '"}} '

    uri = rest_uri + '/api/coiotedm/v3/certificates/saveTwoWayCertificates'
    headers = {'Content-Type': 'application/json'}
    api_call_resp = requests.post(uri, data=body, headers=headers, auth=(user, password))

    try:
        save_certificate_in_secret_manager(external_certificate)
    except secrets_manager_client.exceptions.ResourceExistsException:
        delete_certificates_from_coiote()

    print(api_call_resp.content)
    print(api_call_resp.status_code)


def generate_external_cert(email_address, common_name, serial_number=0):
    # can look at generated file using openssl:
    # openssl x509 -inform pem -in selfsigned.crt -noout -text
    # create a key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 4096)
    # create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = 'PL'
    cert.get_subject().ST = 'Lesser Poland'
    cert.get_subject().L = 'Cracow'
    cert.get_subject().O = 'AVSYSTEM'
    cert.get_subject().OU = 'AVSYSTEM'
    cert.get_subject().CN = common_name
    cert.get_subject().emailAddress = email_address
    cert.set_serial_number(serial_number)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')

    return {
        'certificatePem': crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8"),
        'privateKey': crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode("utf-8")
    }


def save_certificate_in_secret_manager(external_certificate):
    secrets_manager_client.create_secret(Name='coioteDMcert')
    secrets_manager_client.put_secret_value(SecretId='coioteDMcert', SecretString=json.dumps(external_certificate))


@helper.delete
def delete(event, context):
    try:
        delete_certificates_from_coiote()
        delete_certificates_from_aws()
    except Exception:
        pass


def delete_certificates_from_coiote():
    uri = rest_uri + '/api/coiotedm/v3/certificates/deleteTwoWayCertificates/' + group_id
    headers = {'Content-Type': 'application/json'}
    api_call_resp = requests.delete(uri, headers=headers, auth=(user, password))
    print(api_call_resp.content)
    print(api_call_resp.status_code)


def delete_certificates_from_aws():
    secrets_manager_client.delete_secret(Name='coioteDMcert')


def handler(event, context):
    helper(event, context)
