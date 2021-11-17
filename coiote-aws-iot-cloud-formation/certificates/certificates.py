import json
import os
from typing import TypedDict

from requests import Response

import boto3
import requests
from crhelper import CfnResource
from OpenSSL import crypto


class Certificate(TypedDict):
    certificatePem: str
    privateKey: str


class InternalCertificate(TypedDict):
    certificateAuthority: str
    certificatePem: str
    privateKey: str


class ExternalCertificate(TypedDict):
    certificatePem: str


helper = CfnResource()
iot_client = boto3.client('iot')
secrets_manager_client = boto3.client('secretsmanager')

user = os.environ['coioteDMrestUsername']
password = os.environ['coioteDMrestPassword']
rest_uri = os.environ['coioteDMrestUri'] + '/api/coiotedm/v3'
group_id = os.environ['coioteDMrestGroupId']

cert_secret_name = 'coioteDMcert'
cert_data_secret_name = 'coioteDMcertData'


@helper.create
def create(event, context):

    internal_certificate = iot_client.create_keys_and_certificate(setAsActive=True)
    external_certificate = generate_external_cert(email_address=user, common_name=user)
    ca_result = requests.get('https://www.amazontrust.com/repository/AmazonRootCA1.pem')
    internal_cert_ca = ca_result.content.decode('UTF-8')

    save_certificate_in_secret_manager(external_certificate)
    send_internal_certificate(internal_certificate, internal_cert_ca)
    save_internal_certificate_data(internal_certificate)
    send_external_certificate(external_certificate)


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
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')

    return {
        'certificatePem': crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8"),
        'privateKey': crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode("utf-8")
    }


def send_internal_certificate(internal_certificate, internal_cert_ca) -> Response:

    request_body: InternalCertificate = {
        'certificateAuthority': internal_cert_ca,
        'certificatePem': internal_certificate['certificatePem'],
        'privateKey': internal_certificate['keyPair']['PrivateKey']
    }

    uri = rest_uri + '/awsIntegration/auth/internalCertificate/' + group_id
    return requests.post(uri, data=request_body, auth=(user, password))


def save_internal_certificate_data(internal_certificate):
    secrets_manager_client.create_secret(Name=cert_data_secret_name)
    secret_string = json.dumps(internal_certificate['certificateId'])
    secrets_manager_client.put_secret_value(SecretId=cert_data_secret_name, SecretString=secret_string)


def send_external_certificate(external_certificate: Certificate) -> Response:
    request_body: ExternalCertificate = {
        'certificatePem': external_certificate['certificatePem']
    }

    uri = rest_uri + '/auth/certificates'
    return requests.post(uri, data=request_body, auth=(user, password))


def save_certificate_in_secret_manager(external_certificate: Certificate):
    secrets_manager_client.create_secret(Name=cert_secret_name)
    secrets_manager_client.put_secret_value(SecretId=cert_secret_name, SecretString=json.dumps(external_certificate))


@helper.delete
def delete(event, context):
    try:
        delete_internal_certificate_from_coiote()
        delete_internal_certificate_from_aws()
        delete_external_certificate()
        delete_certificates_from_aws()
    except Exception:
        pass


def delete_internal_certificate_from_coiote() -> Response:
    uri = rest_uri + '/awsIntegration/auth/internalCertificate/' + group_id
    return requests.delete(uri, auth=(user, password))


def delete_internal_certificate_from_aws():
    secret_value = secrets_manager_client.get_secret_value(SecretId=cert_data_secret_name)
    secret_string = json.JSONDecoder().decode(secret_value['SecretString'])
    iot_client.delete_certificate(secret_string['certificateId'])
    secrets_manager_client.delete_secret(Name=cert_data_secret_name)


def delete_external_certificate() -> Response:
    uri = rest_uri + '/auth/certificates/' + user
    return requests.delete(uri, auth=(user, password))


def delete_certificates_from_aws():
    secrets_manager_client.delete_secret(Name=cert_secret_name)


def handler(event, context):
    helper(event, context)
