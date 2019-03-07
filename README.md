# image-mover
A simple application utility for Migrating Docker Images between Registries or entire Registries to a new Registry. 

## Installation
Run as a Docker Container or locally with Python already installed.

## Requirements
If running locally as a script you will need Docker CLI installed.
Network access to SRC and DST Docker Registries.
Only tested with Python 3.6.1

## Usage

```
usage: image-mover.py [-h] [-s SOURCE_REGISTRY] [-i IMAGES] -m MODE -d
                      DESTINATION_REGISTRY [-n DESTINATION_NAMESPACE]
                      [-u TARGET_REGISTRY_USER] [-p TARGET_REGISTRY_PASSWORD]
                      [--secure]

image-mover.py: error: the following arguments are required: -m/--mode, -d/--destination_registry
```
## Harbor

If the target Registry is Harbor you must specify -n DESTINATION_NAMESPACE which is a Harbor Project that must already exist. The default Harbor Projects is called "Library".

Habor also requires --secure to force HTTPS connections.

## Examples

Example 1 - Migrate ALL images from one Registry to another.
```
$ python3 image-mover.py -s localhost:5000 -m sync -d localhost:5001
```
Example 2 - Migrate a list of images to the target registry to "library" project.
```
$ python3 image-mover.py -i nginx:latest,tomcat -m sync -d registry.prod.domain.com
```
Example 3 - Migrate a list of images to a Harbor target registry to "library" project.
```
$ python3 image-mover.py -i nginx:latest,tomcat -m sync -d .domain.com -u admin -p password -n library --secure
```

## Functionality not implemented yet



