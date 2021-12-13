import json
import os
import logging
from typing import TypedDict

import boto3
import requests
from requests.exceptions import HTTPError
from OpenSSL import crypto
from crhelper import CfnResource


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
logger = logging.getLogger()

USER = os.environ['coioteDMrestUsername']
PASSWORD = os.environ['coioteDMrestPassword']
REST_URI = os.environ['coioteDMrestUri'] + '/api/coiotedm/v3'

CERT_SECRET_NAME = 'coioteDMcert'
CERT_DATA_SECRET_NAME = 'coioteDMcertData'


def log_success(msg: str):
    logger.info(f"SUCCESS: {msg}")


@helper.create
def create(event, context):
    external_certificate = iot_client.create_keys_and_certificate(setAsActive=True)
    log_success("Certificate created in IoT Core.")
    cert_policy = event['ResourceProperties']['PolicyName']
    iot_client.attach_principal_policy(policyName=cert_policy, principal=external_certificate['certificateArn'])

    user_auth_cert = generate_external_cert(email_address=USER, common_name=USER)
    ca_result = requests.get('https://www.amazontrust.com/repository/AmazonRootCA1.pem')
    ca_result.raise_for_status()

    external_cert_ca = ca_result.content.decode('UTF-8')

    save_external_certificate_data(external_certificate)
    send_external_certificate(external_certificate, external_cert_ca)
    send_user_auth_cert(user_auth_cert)
    save_certificate_in_secrets_manager(user_auth_cert)

    log_success("All certificates have been successfully created.")


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


def send_external_certificate(internal_certificate, internal_cert_ca):
    request_body: ExternalCertificateRequestBody = {
        'certificateAuthority': internal_cert_ca,
        'certificatePem': internal_certificate['certificatePem'],
        'privateKey': internal_certificate['keyPair']['PrivateKey']
    }
    uri = REST_URI + '/awsIntegration/auth/externalCertificate'
    requests.post(uri, json=request_body, auth=(USER, PASSWORD), verify=False).raise_for_status()
    log_success("IoT Core certificate saved in CoioteDM.")


def save_external_certificate_data(internal_certificate):
    secrets_manager_client.create_secret(Name=CERT_DATA_SECRET_NAME)
    secret_string = json.dumps(internal_certificate['certificateId'])
    secrets_manager_client.put_secret_value(SecretId=CERT_DATA_SECRET_NAME, SecretString=secret_string)
    log_success("IoT Core certificate id saved in AWS Secrets Manager.")


def send_user_auth_cert(external_certificate: Certificate):
    request_body: UserAuthCertRequestBody = {
        'certificatePem': external_certificate['certificatePem']
    }
    uri = REST_URI + '/auth/certificates'
    requests.post(uri, json=request_body, auth=(USER, PASSWORD), verify=False).raise_for_status()
    log_success("User authentication certificate saved in CoioteDM.")


def save_certificate_in_secrets_manager(external_certificate: Certificate):
    secrets_manager_client.create_secret(Name=CERT_SECRET_NAME)
    secrets_manager_client.put_secret_value(SecretId=CERT_SECRET_NAME, SecretString=json.dumps(external_certificate))
    log_success("User authentication certificate saved in AWS Secrets Manager.")


@helper.delete
def delete(event, context):
    removal_actions = [
        delete_external_certificate_from_aws(),
        delete_external_certificate_from_coiote(),
        delete_user_auth_cert_from_coiote(),
        delete_certificate_from_secrets_manager(),
    ]
    if not all(removal_actions):
        raise Exception("Delete action went wrong, check CloudWatch logs for more details.")
    else:
        log_success("All certificates have been successfully removed.")


def delete_external_certificate_from_coiote() -> bool:
    uri = REST_URI + '/awsIntegration/auth/externalCertificate'
    try:
        requests.delete(uri, auth=(USER, PASSWORD), verify=False).raise_for_status()
    except HTTPError as e:
        logger.error(e)
        return False

    log_success("IoT Core certificate removed from CoioteDM.")
    return True


def delete_external_certificate_from_aws() -> bool:
    try:
        secret_value = secrets_manager_client.get_secret_value(SecretId=CERT_DATA_SECRET_NAME)
        secret_string = json.loads(secret_value['SecretString'])

        try:
            iot_client.update_certificate(certificateId=secret_string, newStatus='INACTIVE')
            iot_client.delete_certificate(certificateId=secret_string)
        except iot_client.exceptions.ResourceNotFoundException:
            logger.warning("Certificate not found in IoT Core, it could have been removed manually.")

        try:
            secrets_manager_client.delete_secret(SecretId=CERT_DATA_SECRET_NAME, ForceDeleteWithoutRecovery=True)
        except secrets_manager_client.exceptions.ResourceNotFoundException:
            pass

    except secrets_manager_client.exceptions.ResourceNotFoundException as e:
        logger.error(
            "IoT Core certificate id not found in Secrets Manager."
            "Certificate will be kept in IoT Core if it has not been removed manually."
        )
        logger.error(e)
        return False
    except Exception as e:
        logger.error(e)
        return False

    log_success("IoT Core certificate removed from AWS Secrets Manager.")
    return True


def delete_user_auth_cert_from_coiote() -> bool:
    uri = REST_URI + '/auth/certificates/'

    try:
        requests.delete(uri, auth=(USER, PASSWORD), verify=False).raise_for_status()
    except HTTPError as e:
        logger.error(e)
        return False

    log_success("User authentication certificate removed from CoioteDM")
    return True


def delete_certificate_from_secrets_manager() -> bool:
    try:
        secrets_manager_client.delete_secret(SecretId=CERT_SECRET_NAME, ForceDeleteWithoutRecovery=True)
    except secrets_manager_client.exceptions.ResourceNotFoundException:
        logger.warning("Certificate not found in Secrets Manager, it could have been removed manually.")
    except Exception as e:
        logger.error(e)
        return False

    log_success("User authentication certificate removed from AWS Secrets Manager")
    return True


def handler(event, context):
    helper(event, context)
