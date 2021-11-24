import json
import os
from typing import TypedDict

import boto3
import requests
from OpenSSL import crypto
from crhelper import CfnResource
from requests import Response


class Certificate(TypedDict):
    certificatePem: str
    privateKey: str


class ExternalCertificateRequestBody(TypedDict):
    certificateAuthority: str
    certificatePem: str
    privateKey: str


class UserAuthCertRequestBody(TypedDict):
    certificatePem: str


helper = CfnResource()
iot_client = boto3.client('iot')
secrets_manager_client = boto3.client('secretsmanager')

USER = os.environ['coioteDMrestUsername']
PASSWORD = os.environ['coioteDMrestPassword']
REST_URI = os.environ['coioteDMrestUri'] + '/api/coiotedm/v3'
GROUP_ID = os.environ['coioteDMrestGroupId']

CERT_SECRET_NAME = 'coioteDMcert'
CERT_DATA_SECRET_NAME = 'coioteDMcertData'


@helper.create
def create(event, context):

    external_certificate = iot_client.create_keys_and_certificate(setAsActive=True)
    user_auth_cert = generate_external_cert(email_address=USER, common_name=USER)
    ca_result = requests.get('https://www.amazontrust.com/repository/AmazonRootCA1.pem')
    external_cert_ca = ca_result.content.decode('UTF-8')

    save_external_certificate_data(external_certificate)
    send_external_certificate(external_certificate, external_cert_ca)
    send_user_auth_cert(user_auth_cert)
    save_certificate_in_secrets_manager(user_auth_cert)


def generate_external_cert(email_address: str, common_name: str, serial_number=0) -> Certificate:
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
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')

    return {
        'certificatePem': crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8"),
        'privateKey': crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode("utf-8")
    }


def send_external_certificate(internal_certificate, internal_cert_ca) -> Response:

    request_body: ExternalCertificateRequestBody = {
        'certificateAuthority': internal_cert_ca,
        'certificatePem': internal_certificate['certificatePem'],
        'privateKey': internal_certificate['keyPair']['PrivateKey']
    }

    uri = REST_URI + '/awsIntegration/auth/externalCertificate/' + GROUP_ID
    return requests.post(uri, json=request_body, auth=(USER, PASSWORD))


def save_external_certificate_data(internal_certificate):
    secrets_manager_client.create_secret(Name=CERT_DATA_SECRET_NAME)
    secret_string = json.dumps(internal_certificate['certificateId'])
    secrets_manager_client.put_secret_value(SecretId=CERT_DATA_SECRET_NAME, SecretString=secret_string)


def send_user_auth_cert(external_certificate: Certificate) -> Response:
    request_body: UserAuthCertRequestBody = {
        'certificatePem': external_certificate['certificatePem']
    }

    uri = REST_URI + '/auth/certificates'
    return requests.post(uri, json=request_body, auth=(USER, PASSWORD))


def save_certificate_in_secrets_manager(external_certificate: Certificate):
    secrets_manager_client.create_secret(Name=CERT_SECRET_NAME)
    secrets_manager_client.put_secret_value(SecretId=CERT_SECRET_NAME, SecretString=json.dumps(external_certificate))


@helper.delete
def delete(event, context):
    delete_external_certificate_from_aws()
    delete_external_certificate_from_coiote()
    delete_user_auth_cert_from_coiote()
    delete_certificate_from_secrets_manager()


def delete_external_certificate_from_coiote() -> Response:
    uri = REST_URI + '/awsIntegration/auth/externalCertificate/' + GROUP_ID
    return requests.delete(uri, auth=(USER, PASSWORD))


def delete_external_certificate_from_aws():
    secret_value = secrets_manager_client.get_secret_value(SecretId=CERT_DATA_SECRET_NAME)
    secret_string = json.JSONDecoder().decode(secret_value['SecretString'])
    iot_client.delete_certificate(secret_string['certificateId'])
    secrets_manager_client.delete_secret(Name=CERT_DATA_SECRET_NAME)


def delete_user_auth_cert_from_coiote() -> Response:
    uri = REST_URI + '/auth/certificates/'
    return requests.delete(uri, auth=(USER, PASSWORD))


def delete_certificate_from_secrets_manager():
    secrets_manager_client.delete_secret(Name=CERT_SECRET_NAME)


def handler(event, context):
    helper(event, context)
