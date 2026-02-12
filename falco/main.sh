#!/bin/bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update

kubectl apply -f falco_secret.yml 
helm install falco falcosecurity/falco -f falco.yml
helm install falcosidekick falcosecurity/falcosidekick  -f falcosidekick.yml

# to test
#To trigger critical event:- 
docker run --privileged -it -d --name priv-container nginx
docker exec -it priv-container bash
cd /proc/self/
echo "echo /bin/bash > /proc/self/release_agent" > /release_agent