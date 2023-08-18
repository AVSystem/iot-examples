# IoT Examples used in AVS developer zone [<img align="right" height="50px" src="https://avsystem.github.io/Anjay-doc/_images/avsystem_logo.png">](http://www.avsystem.com/)

## Air quality meter
This is a simple Java Application, that uses the Anjay-Java to expose Temperature and Air Quality over 
Lwm2m protocol. 
Please check:

https://iotdevzone.avsystem.com/docs/Azure_IoT_Integration_Guide/Tutorials/Air_quality_monitoring_tutorial.html 

## Coiote AWS IoT Terraform & CloudFormation config
A Terraform & CloudFormation files that allow to deploy resources in AWS subscription, that are required to allow LPWAN (Lwm2m) devices connection to AWS IoT Core using Coiote DM Platform. 


Once you update the contents of CloudFormation integration, a [Github workflow](https://github.com/AVSystem/iot-examples/blob/main/.github/workflows/update-aws-lambdas.yml) will be executed to update the resources in AWS used by the integrating parties.
