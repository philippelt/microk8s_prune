# microk8s_prune

As you can expect, this small utility is doing for a microk8s / containerd environment the same operation that docker system prune does : it search for images unused by container to list them and/or delete them to recover space

You will need a python3 running environnment and the containerd library (pip install containerd). This should also install grpc dependancies.

if you chmod +x the utility, just run it with :

```./microk8s_prune.py [ciuspf]```

Parameters:
- c : List containers and associated images (line output prefixed with C:)
- i : List all found images names (prefixed with I:)
- u : List unused images names (prefixed with U:)
- s : Print summary information (# containers, total images, unused images)
- p : DELETE unused images (will require confirmation if run interactively)
- f : Force delete without confirmation

Without any parameter, it will do the job of identifying unused images but do not display anything nor delete anything. Without ```p``` and/or ```f``` parameter, the utility is strictly read-only.

The ctr utility to manage containerd do not provide such feature and considering that microk8s is especially usefull for small appliances where resources are limited I think it would be nice to have it.

In the meantime, this utility will solve the problem 😊

This utility could be used in non microk8s containerd environment, just replace the namespace which is harcoded to ```k8s.io``` and reference the appropriate sock in place of the microk8s one ``unix:///var/snap/microk8s/common/run/containerd.sock``
