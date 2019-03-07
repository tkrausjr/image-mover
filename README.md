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
                      DESTINATION_REGISTRY [-u TARGET_REGISTRY_USER]
                      [-p TARGET_REGISTRY_PASSWORD]
```
## Examples

Example 1 - Migrate ALL images from one Registry to another.
```
$ python3 image-mover.py -s localhost:5000 -m sync -d localhost:5001
```
Example 2 - Migrate a list of images to the target registry to "library" project.
```
$ python3 image-mover.py -i nginx:latest,kafka:latest,tomcat -m sync -d harbor2.prod.domain.com/library
```


## Functionality not implemented yet



