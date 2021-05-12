#!/usr/bin/env python3


import sys


import grpc
from containerd.services.containers.v1 import containers_pb2_grpc, containers_pb2
from containerd.services.images.v1 import images_pb2_grpc, images_pb2


# args :   c print containers and associated images
#          i print images name
#          u print unused images name
#          s print sumary info
#          p DELETE unused images (if run interactively, will request confirmation)
#          f force delete without confirmation


args = ",".join(sys.argv[1:]).lower()
if "p" in args and not "f" in args and sys.stdout.isatty():
    resp = input("Unused images will be deleted, please confirm [y/N]: ")
    if resp.upper() != "Y":
        print("Operation cancelled")
        sys.exit(1)

with grpc.insecure_channel('unix:///var/snap/microk8s/common/run/containerd.sock') as channel:

    containersv1 = containers_pb2_grpc.ContainersStub(channel)
    containers = containersv1.List( containers_pb2.ListContainersRequest(),
                                    metadata=(('containerd-namespace', 'k8s.io'),)).containers

    usedImages = {}
    for c in containers:
        usedImages[c.image] = c.id
        if "c" in args:
            print("C:", c.id, c.image)

    imagesv1 = images_pb2_grpc.ImagesStub(channel)
    images = imagesv1.List( images_pb2.ListImagesRequest(),
                            metadata=(('containerd-namespace', 'k8s.io'),)).images
    
    unused = []
    for i in images:
        if i.name not in usedImages: unused.append(i.name)
        if "i" in args:
            print("I:", i.name)

    if "u" in args:
        for i in unused: print("U:", i)

    if "p" in args:
        for i in unused: imagesv1.Delete( images_pb2.DeleteImageRequest( name=i, sync=True),
                                          metadata=(('containerd-namespace', 'k8s.io'),) )

    if "s" in args:
        print("S:", len(containers), "containers")
        print("S:", len(usedImages), "used images")
        print("S:", len(images), "total images")
        if unused: print("S:", len(unused), "unused images", "(removed)" if "p" in args else "")
