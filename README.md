# Overview

For sending logs from Kubernetes Pods, available options as outlined [here](https://kubernetes.io/docs/concepts/cluster-administration/logging/)

When we create a fargate profile in EKS, we either create a profile based on a namespace or a selector, so that every workload matching the namespace or selector runs in Fargate. Pods are scheduled in Fargate and they are Kubernetes Pods. Although they are Kubernetes Pods, there is no way to access host level log file destination. Although, there is talk about [AWS Firelens as a potential solution](https://github.com/aws/containers-roadmap/issues/701), it is not supported in EKS as of this writing. Adding a sidecar with a known log file name or changing the application to directly send to a log destination are tedious and require changes which are very intrusive and also could be expensive and difficult to maintain.

As an alternative, add one additional workload in the same selector/namespace to send logs to loki is cheaper and easy to maintain and with very less overhead and without the need to change any existing workloads.


## Deployment

Samples for deployment in [k8s](k8s/). Current implementation is only for namespaces. Same approach could be done for selectors if needed.

## Dev Setup - Using Telepresence

Add a deployment to your existing namespace with the image datawire/telepresence-k8s:0.103.

```bash
# for example for a namespace dev1 and deployment log-exporter, run the following
telepresence --namespace dev1 --deployment log-exporter --run-shell
# you can run the python script, change etc in your local machine now.
# pip --disable-pip-version-check install -r requirements.txt
```