#!/usr/bin/env python3

import sys
from datetime import datetime

import grpc
from containerd.services.containers.v1 import containers_pb2_grpc, containers_pb2
from containerd.services.images.v1 import images_pb2_grpc, images_pb2
from containerd.services.content.v1 import content_pb2_grpc, content_pb2

# args :   c print containers and associated images
#          i print images name
#          u print unused images name
#          s print sumary info
#          p DELETE unused images (if run interactively, will request confirmation)
#          f force delete without confirmation


def compute_size(contentv1, imgDigest, doneLayer=None):
    content = contentv1.Info( content_pb2.InfoRequest(digest=imgDigest),
                              metadata=(('containerd-namespace', 'k8s.io'),)).info
    layers = [l for l in content.labels if "containerd.io/gc.ref.content." in l]
    size = content.size
    for l in layers:
        try:
            if doneLayer is not None:
                if content.labels[l] in doneLayer:
                    continue
                else:
                    doneLayer.append(content.labels[l])
                    size += compute_size(contentv1, content.labels[l], doneLayer)
            else:
                size += compute_size(contentv1, content.labels[l])
        except:
            pass # Layer not found in content ?
    return size


# From Fred Cirera on StackOverflow : thanks !
# https://stackoverflow.com/questions/1094841/get-human-readable-version-of-file-size
def sizeof_fmt(num, suffix='B'):
    for unit in [' B',' K',' M',' G',' T',' P',' E',' Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


args = ",".join(sys.argv[1:]).lower()
if "p" in args and not "f" in args and sys.stdout.isatty():
    resp = input("Unused images will be deleted, please confirm [y/N]: ")
    if resp.upper() != "Y":
        print("Operation cancelled")
        sys.exit(1)

with grpc.insecure_channel('unix:///var/snap/microk8s/common/run/containerd.sock') as channel:

    containersv1 = containers_pb2_grpc.ContainersStub(channel)
    imagesv1 = images_pb2_grpc.ImagesStub(channel)
    contentv1 = content_pb2_grpc.ContentStub(channel)

    containers = containersv1.List( containers_pb2.ListContainersRequest(),
                                    metadata=(('containerd-namespace', 'k8s.io'),)).containers

    usedImages = {}
    for c in containers:
        usedImages[c.image] = c.id
        if "c" in args: print("C:", c.id, c.image)

    images = imagesv1.List( images_pb2.ListImagesRequest(),
                            metadata=(('containerd-namespace', 'k8s.io'),)).images
    
    unused = []
    totalImageSize = 0
    netTotalSize = 0
    doneLayer = []
    for i in images:
        if i.name not in usedImages: unused.append(i.name)
        imageSize = compute_size(contentv1, i.target.digest)
        totalImageSize += imageSize
        netTotalSize += compute_size(contentv1, i.target.digest, doneLayer)
        if "i" in args:
            print("I:", i.name,
                        imageSize,
                        datetime.fromtimestamp(i.updated_at.seconds).isoformat())

    if "u" in args:
        for i in unused: print("U:", i)

    if "p" in args:
        for i in unused: imagesv1.Delete( images_pb2.DeleteImageRequest( name=i, sync=True),
                                          metadata=(('containerd-namespace', 'k8s.io'),) )

    if "s" in args:

        print("S:", len(containers), "containers")
        print("S:", len(images), "total images")
        print("S: %s (%s bytes) total images size, %s shared" % (sizeof_fmt(totalImageSize), totalImageSize, sizeof_fmt(totalImageSize-netTotalSize)))
        print("S:", len(usedImages), "used images")
        if unused: print("S:", len(unused), "unused images")

        if "p" in args:
            images = imagesv1.List( images_pb2.ListImagesRequest(),
                                    metadata=(('containerd-namespace', 'k8s.io'),)).images
            newNetImageSize = 0
            doneLayer = []
            for i in images:
                newNetImageSize += compute_size(contentv1, i.target.digest, doneLayer)
            recovered = netTotalSize - newNetImageSize
            print("S: %s (%s bytes) recovered space" % (sizeof_fmt(recovered), recovered))
