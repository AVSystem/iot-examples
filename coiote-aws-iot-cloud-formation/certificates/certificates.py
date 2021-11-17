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
group_id = os.environ['coioteDMrestGroupId']

secret_name = 'coioteDMcert'


@helper.create
def create(event, context):

    internal_certificate = iot_client.create_keys_and_certificate(setAsActive=True)
    external_certificate = generate_external_cert(email_address=user, common_name=user)
    ca_result = requests.get('https://www.amazontrust.com/repository/AmazonRootCA1.pem')
    internal_cert_ca = ca_result.content.decode('UTF-8')

    send_internal_certificate(internal_certificate, internal_cert_ca)

    send_external_certificate(external_certificate)

    try:
        save_certificate_in_secret_manager(external_certificate)
    except secrets_manager_client.exceptions.ResourceExistsException:
        delete_internal_certificate()
        delete_external_certificate()


def generate_external_cert(email_address: str, common_name: str, serial_number=0) -> dict:
    # can look at generated file using openssl:
    # openssl x509 -inform pem -in selfsigned.crt -noout -text
    # create a key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 4096)
    # create a self-signed cert
    cert = crypto.X509()
    cert.get_issuer().C = 'PL'
    cert.get_issuer().ST = 'Lesser Poland'
    cert.get_issuer().L = 'Cracow'
    cert.get_issuer().O = 'AVSystem'
    cert.get_issuer().OU = 'AVSystem'
    cert.get_issuer().CN = 'AVSystem'
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


def send_internal_certificate(internal_certificate, internal_cert_ca):

    request_body = {
        'certificateAuthority': internal_cert_ca,
        'certificatePem': internal_certificate['certificatePem'],
        'privateKey': internal_certificate['keyPair']['PrivateKey']
    }

    uri = rest_uri + '/api/coiotedm/v3/awsIntegration/auth/internalCertificate/' + group_id
    headers = {'Content-Type': 'application/json'}
    return requests.post(uri, data=json.dumps(request_body), headers=headers, auth=(user, password))


def send_external_certificate(external_certificate):
    request_body = {
        'certificatePem': external_certificate['certificatePem']
    }

    uri = rest_uri + '/api/coiotedm/v3//auth/certificates'
    headers = {'Content-Type': 'application/json'}
    return requests.post(uri, data=json.dumps(request_body), headers=headers, auth=(user, password))


def save_certificate_in_secret_manager(external_certificate):
    secrets_manager_client.create_secret(Name=secret_name)
    secrets_manager_client.put_secret_value(SecretId=secret_name, SecretString=json.dumps(external_certificate))


@helper.delete
def delete(event, context):
    try:
        delete_internal_certificate()
        delete_external_certificate()
        delete_certificates_from_aws()
    except Exception:
        pass


def delete_internal_certificate():
    uri = rest_uri + '/api/coiotedm/v3/awsIntegration/auth/internalCertificate/' + group_id
    headers = {'Content-Type': 'application/json'}
    return requests.delete(uri, data=json.dumps({}), headers=headers, auth=(user, password))


def delete_external_certificate():
    uri = rest_uri + '/api/coiotedm/v3//auth/certificates/' + user
    headers = {'Content-Type': 'application/json'}
    return requests.post(uri, data=json.dumps({}), headers=headers, auth=(user, password))


def delete_certificates_from_aws():
    secrets_manager_client.delete_secret(Name=secret_name)


def handler(event, context):
    helper(event, context)
