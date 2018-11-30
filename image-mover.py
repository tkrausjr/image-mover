__author__ = 'tkraus-m'

import requests
import sys
import subprocess
import time
import json
import os
import fileinput
import getopt
import shlex
import shutil
import marathon
import re

# Set the Target for Docker Iamges. Valid options are 'quay' and 'docker_registry'
docker_target = 'quay'
# Set the Target for HTTP Artifacts including the actual Universe JSON definition itself
# Valid options are 'nginx' and 'nexus'
http_target = 'nexus'
remove_images=False # Will remove local copies of images already transferred to dst_registry_host

# Section below used for Source Universe - In general these values do not need to be changed
src_registry_proto = 'https://'
src_registry_host = 'localhost:5000'
src_http_protocol = 'http://'
src_http_host = 'localhost:8082'
src_insecure = True
pulled_images =[]

# Update section below if a proxy exists between server where script is run and destination HTTP server
# IF proxy exists between server where script runs & Quay/registry svr then setup a Docker Daemon proxy also
http_proxy =''
https_proxy = http_proxy
proxies = {"http" : http_proxy, "https" : https_proxy}

# Section below used for Destination Quay or Registry Server for Universe Docker Images
dst_registry_proto = 'https://'
dst_registry_host = 'quay-server.domain.net'
dst_registry_namespace ='universe/'  # Include Trailing Slash after namespace

# Section below used for Destination HTTP/FRS/Artifactory for Universe Artifacts
dst_http_protocol ='https://'
dst_http_host = 'http-artifact-svr.domain.net'
dst_http_namespace = 'maven/content/sites/GCP-SITE/DCOS-Universe/Prod/'
dst_http_repository_user = 'xyzxyzxyz'
dst_http_repository_pass = 'xyzxyzxyz'
universe_json_file = 'repo-up-to-1.8.json'
working_directory = '/tmp/'
http_artifacts_scan_zip_dir = '/var/lib/a_ansible/'

target_dcos_master = 'https://dcos-master.domain.net'
target_dcos_user = 'admindcos'

def load_universe(universe_image):
    print('--Loading Mesosphere/Universe Docker Image '+universe_image)
    command = ['sudo','docker', 'load', '-i', universe_image]
    subprocess.check_call(command)

def start_universe(universe_image,command):
    print('--Starting Mesosphere/Universe Docker Image '+universe_image)
    subprocess.Popen(command).wait()
    print('--Successfully Started Mesosphere/Universe Docker Image '+universe_image)
    print('--Waiting 5 Seconds for Container Startup')
    time.sleep(5)

def docker_login(dst_registry_proto,dst_registry_host):
    print('--Docker Logging in for Quay Server: '+ dst_registry_host )
    command = ['sudo','docker', 'login', '{}{}'.format(dst_registry_proto,dst_registry_host)]
    subprocess.check_call(command)

def get_registry_images(registry_proto,registry_host):
    print("--Getting Mesosphere/Universe Repositories ")
    response = requests.get(registry_proto + registry_host +'/v2/_catalog', verify=False)

    if response.status_code != 200:
        print (str(response.status_code) + " Registry API CAll unsuccessful to " + registry_host)
        print ("----Raw Docker Error Message is  " + response.text )
        exit(1)
    else:
        responseJson=response.json()
        if responseJson['repositories'] ==[]:
            print ("----No Repositories found on Source Mesosphere/Universe")
            sys.exit(1)
        else:
            repositories=[]
            for i in responseJson['repositories']:
                print("----Found an image named " + i)
                repositories.append(i)
            return repositories

def get_registry_manifests(registry_proto,registry_host,repos):
    registry_manifest_dict ={}
    print("--Getting Source Mesosphere/Universe Registry Manifests")
    for i in repos:
            response = requests.get(registry_proto + registry_host +'/v2/'+ i + '/tags/list', verify=False)
            responseJson=response.json()
            print("----Manifests Response " + str(responseJson))
            name = responseJson['name']
            for tag in responseJson['tags']:
                tag = tag
                registry_manifest_dict[str(name)] = str(tag)
                print("----Name is " + name + " and tag is " + tag)
    return registry_manifest_dict

def pull_images(name):
    print('--Pulling docker image: {}'.format(name))
    command = ['sudo', 'docker', 'pull', name]
    subprocess.check_call(command)

def new_format_image_name(dst_registry_host,dst_registry_namespace,image,imagetag):
    print("Src Imagename is " + image)
    if '/' in image:
        newimage='{}/{}{}:{}'.format(dst_registry_host,dst_registry_namespace,image.split("/")[1],imagetag)
        print("Slash in image name, New image is " + newimage)
        return newimage
    else:
        print("No slash in image so New image is " + image)
        return image

def tag_images(image,imagetag,fullImageId,dst_registry_host):
    new_image_name = new_format_image_name(dst_registry_host,dst_registry_namespace,image,imagetag)
    print("--Tagging temp Universe Image "+fullImageId + " for new Registry "+new_image_name)
    command = ['sudo','docker', 'tag', fullImageId, new_image_name]
    subprocess.check_call(command)
    return new_image_name

def push_images(new_image,docker_target):
    if docker_target == 'docker_registry':
        print("--Pushing Image to Docker Registry - "+new_image)
        command = ['sudo', 'docker', 'push', new_image]
        subprocess.check_call(command)
    if docker_target == 'quay':
        print("--Pushing Image to Quay - "+new_image)
        command = ['sudo', 'docker', 'push', new_image]
        subprocess.check_call(command)

def make_repo_public(new_image,dst_registry_proto):
    hostname,namespace,image = new_image.split('/')
    image_only = image.split(':')[0]
    quay_repository = '{}{}/{}/{}/{}/{}'.format(dst_registry_proto,hostname,'api/v1/repository',namespace,image_only,'changevisibility')
    headers = {'Authorization':'Bearer TzOMaqr7MwFm32DcDrEDZ5o0ZlO5YQV2t4CaJOFd','Content-type': 'application/json'}
    print("Making Quay Repository Public for " + new_image +' using protocol ' + dst_registry_proto)
    print("Quay Repository = " + quay_repository)
    json_data=json.dumps({'visibility':'public'})
    response = requests.post(quay_repository, data=json_data, proxies=proxies,headers=headers, verify=False)

    if response.status_code != 200:
        print ("  "+str(response.status_code) + " -- Quay API Call Failed")
        print ("  "+response.text)
        print (response.raise_for_status())
        return
    else:
        print ("  "+str(response.status_code) + " -- Quay API Call Success !!")
        return

def copy_http_data(working_directory,universe_json_file):
    print("--Copying Universe HTTP to hosts Working Directory ")
    command = ['sudo', 'docker', 'cp', 'temp-universe-sync:/usr/share/nginx/html/', working_directory]
    subprocess.check_output(command)
    if mode != 'test':
        command = ['sudo', 'chown', '-R', 'a_ansible:users', working_directory]
        subprocess.check_output(command)
    updated_universe_json_file = (working_directory +'html/'+ universe_json_file)
    return updated_universe_json_file  # Return updated reference to the now modified Universe.json file

def transform_json(src_string,dst_string,json_file):
    print("transform_json function is changing <"+ src_string + "> with <"+dst_string +">.")
    for line in fileinput.input(json_file, inplace=True):
        # the comma after each print statement is needed to avoid double line breaks
        print(line.replace(src_string,dst_string),)

def new_transform_json(src_string,dst_string,packages):
    for package in packages:
        for key, value in package.items():
            if key == 'resource' or key == 'config':
                print('\n Old Value is {}'.format(value))
                stringvalue = str(value)
                if src_string in stringvalue:
                    print("Found the " +src_string)
                    new_string=stringvalue.replace(src_string,dst_string)
                    print("\n New String Value = "+new_string)
                    package[key]=new_string
    return packages

    '''
    print("\n new_transform_json function is changing <"+ src_string + "> with <"+dst_string +">.")
    if src_string in content:
        print(" FOUND String, Changing "+ src_string +" to "+ dst_string +"\n")
        content.replace(src_string, dst_string)
        return content
    else:
        print("  --- *** ERROR *** --- "+ src_string + " not found in \n")
        return content
    '''

def newer_transform_json(old_new_image_dict,json_file):
# This not working either
    for fullImageId,new_image in old_new_image_dict.items():
        print(str(fullImageId))
        print(str(new_image))
        print("newer_transform_json function is changing <"+ fullImageId + "> with <"+new_image +">.")
        for line in fileinput.input(json_file, inplace=True):
            # the comma after each print statement is needed to avoid double line breaks
            print(line.rstrip().replace(str(fullImageId),str(new_image)),)

def newest_transform_json(old_new_image_dict,json_file):
    file_handle = open(json_file, 'rb')
    file_string = file_handle.read().decode('utf-8')
    file_handle.close()

    for fullImageId,new_image in old_new_image_dict.items():
        # THIS APPEARS TO BE REDUNDANT aND THE short versions below will CATCH ALL !!!
        print("newest_transform_json function is changing "+ fullImageId + " with "+new_image )
        file_string = re.sub(fullImageId, new_image, file_string)

        print(" \n newest_transform_json is replacing Image references where authors did not include a Docker TAG")
        short_fullImageId = ":".join(fullImageId.split(":")[0:2])
        short_new_image = "".join(new_image.split(":")[0])
        print("newest_transform_json function is changing "+ short_fullImageId + " with "+ short_new_image )
        file_string = re.sub(short_fullImageId, short_new_image, file_string)


    print("***** DEBUG ***** Updated json = " + file_string)
    # LEFT OFF HERE _ EVERYTHING WORKING EXCEPT WRITING THE FILE OUT

    file_handle = open(json_file, 'w')
    file_handle.write(file_string)
    file_handle.close()


def return_http_artifacts(working_directory):
    http_artifacts = []
    os.chdir('{}{}/'.format(working_directory,'html'))
    for subdir, dirs, files in os.walk('{}{}'.format(working_directory,'html')):
        for file in files:
            if file.startswith(".") or file.startswith("index.html") or file.startswith("domain.crt"):
                print("Found files to skip = " + file)

            else:
                print("Files are " +os.path.join(subdir, file))
                http_artifacts.append(os.path.join(subdir, file))
    return http_artifacts

def upload_http_nexus(dst_http_protocol,dst_http_host,dst_http_namespace,http_artifacts):
    baseurl ='{}{}/{}{}/'.format(dst_http_protocol,dst_http_host,dst_http_namespace,time.strftime("%Y-%m-%d"))
    try:
        for file in http_artifacts:
            print('\nWorking on file ' + file)
            upload_file={'file' : open(file,'rb')}
            pathurl=(file.split("html/")[1])
            url = '{}{}'.format(baseurl,pathurl)
            print(' Uploading file to {}{}'.format(baseurl,pathurl))

            headers = {'Connection':'keep-alive','content-type': 'multipart/form-data'}
            with open(file,'rb') as uploadfile:
                response = requests.put(url, data=uploadfile, auth=(dst_http_repository_user,dst_http_repository_pass),proxies=proxies,headers=headers)

            if response.status_code != 201:
                print ("  "+str(response.status_code) + " -- Nexus API CAll unsuccessful")
                print (response.raise_for_status())
                exit(1)
            else:
                print ("  "+str(response.status_code) + " -- Nexus API CAll SUCCESS")
        return baseurl
    except:
        print(" **** WARNING - MISSING HTTP ARTIFACTS ****")
        return baseurl

def zip_universe_artifacts(working_directory,http_artifacts_scan_zip_dir):
    universe_zipfile = ('{}-{}.{}'.format('offline-universe',time.strftime("%Y-%m-%d"),'zip'))
    ## TEMP CHANGE to get Universe working running out of space in temp - need a module to define HOME Directory
    command = ['sudo','zip', '-r', '{}{}'.format(http_artifacts_scan_zip_dir, universe_zipfile), '{}{}'.format(working_directory,'html')]
    subprocess.check_call(command)
    command = ['sudo', 'chown', '-R', 'a_ansible:users', '{}{}'.format(http_artifacts_scan_zip_dir,universe_zipfile)]
    subprocess.check_output(command)
    return ('{}{}'.format(http_artifacts_scan_zip_dir,universe_zipfile))

def run_local_universe_http():
    print('--Running local NGINX Container on PORT 8083 ')
    command = "sudo docker run -d --name local-universe-http -p 8083:80 -v /tmp/html:/usr/share/nginx/html mesosphere/universe nginx -g \"daemon off;\""
    new_command = shlex.split(command)
    subprocess.check_output(new_command)

def clean_up_tmp():
    command = ['sudo', 'rm', '-rf', '{}{}'.format(working_directory,'html')]
    subprocess.check_call(command)

def clean_up_images():
    command = ['sudo', 'docker', 'stop', 'temp-universe-sync']
    subprocess.check_call(command)
    command = ['sudo', 'docker', 'rm', '-f', 'temp-universe-sync']
    subprocess.check_call(command)

if __name__ == "__main__":

    script_dir = os.getcwd()
    try:
      opts, args = getopt.getopt(sys.argv[1:],"hi:m:",["ifile=","mode="])
    except getopt.GetoptError:
      print ('universe-sync-jpmc.py -i <universe_image> -m <scan/sync>')
      sys.exit(2)
    found_i = False
    found_m = False
    for opt, arg in opts:
      if opt == '-h':
         print ('universe-sync-enterprise.py -i <universe_image> -m <scan/sync>')
         print ('   <universe_image> is the tar archive of a mesosphere/universe docker image')
         print ('   <scan/sync> choose \'scan\' to create a ZIP file ONLY of HTTP Artifacts for Blackduck Scanning before sync.')
         print ('   <scan/sync> choose \'sync\' to fully synchronize Universe Docker Images and HTTP Artifacts to targets.')
         sys.exit()
      elif opt in ("-i", "--ifile"):
         universe_image = arg
         found_i = True
      elif opt in ("-m", "--mode"):
         mode = arg
         found_m = True

    if not found_i or not found_m:
        print("You must specify the -i for input Docker Image and -m for execution mode")
        sys.exit(2)

    print ('Input file is ', universe_image)
    print ('Execution Mode is ', mode)
    print ('*****************************************')

    if mode == 'sync':
        print('The configured DCOS cluster is: ' + target_dcos_master)
        print('The configured user for the DCOS cluster is: ' + target_dcos_user)
        target_dcos_pass = input('Enter a Password for the target Cluster: ' )

    # Load local/universe Docker Container from Tarball
    load_universe(universe_image)
    registry_command = ['sudo', 'docker', 'run', '-d', '--name', 'temp-universe-sync', '-v', '/usr/share/nginx/html/','-p','5000:5000', '-e','REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt',
               '-e', 'REGISTRY_HTTP_TLS_KEY=/certs/domain.key', 'mesosphere/universe',
               'registry', 'serve', '/etc/docker/registry/config.yml']
    start_universe(universe_image,registry_command)
    if mode != 'test':
        docker_login(dst_registry_proto,dst_registry_host)

    # DOCKER REPO IMAGE MOVE from UNIVERSE IMAGE to DEST REGISTRY
    src_repos = get_registry_images(src_registry_proto,src_registry_host)
    src_manifests = get_registry_manifests(src_registry_proto,src_registry_host,src_repos)
    input ("DEBUG PAUSE - Press Enter to continue . . . ")
    try:
        old_new_image_dict = {}
        for image,imagetag in src_manifests.items():
            print('Starting on Image ('+image+':'+imagetag+")")
            fullImageId = src_registry_host + "/" + image + ":" + imagetag
            print("Source Docker Image to Pull = " + fullImageId)
            pull_images(fullImageId)
            new_image=tag_images(image,imagetag,fullImageId,dst_registry_host)
            print("Destination Docker Image to Push = " + new_image)
            if mode != 'test':
                push_images(new_image,docker_target)
                # New section to make Quay REPO Publicly Open - -
                make_repo_public(new_image,dst_registry_proto)

            # Build a Python Dict with OLD Image as key and New Image as Value
            old_new_image_dict[fullImageId] = new_image
            print("Finished with Image ("+image+':'+imagetag+")\n")

    except (subprocess.CalledProcessError):
            print('MISSING Docker Images: {}'.format(image))

    print("\n \n New Images uploaded to "+dst_registry_host+ " are " + str(old_new_image_dict.items()))
    input ("DEBUG PAUSE - Press Enter to continue . . . ")
    # HTTP Artifacts
    # Copy out the entire nginx / html directory to data directory where script is being run.
    updated_universe_json_file = copy_http_data(working_directory,universe_json_file)

    # HTTP Artifacts - Rewrite the universe.json file with correct Docker and HTTP URL's
    # 3 Lines below are unnecessary if using SED and
    with open(updated_universe_json_file, 'r') as json_data:
        src_universe_json = json.load(json_data)
    packages = src_universe_json['packages']

    '''
    # Iterate through the DICT of OLD-NEW Docker Image Tags
    for fullImageId,new_image in old_new_image_dict.items():
        new_packages=new_transform_json(fullImageId,new_image,packages)
    new_universe_json = {}
    new_universe_json["packages"] = new_packages

    '''
    command = ['sudo', 'chown', '-R', 'tkraus:wheel', '{}{}'.format(working_directory,'/html')]
    subprocess.check_output(command)
    '''
    newer_transform_json(old_new_image_dict,updated_universe_json_file)
    '''
    newest_transform_json(old_new_image_dict,updated_universe_json_file)
    input ("DEBUG PAUSE - Press Enter to continue . . . ")

    '''
    # Write the updated JSON to the json file repo-up-to-1.8.json
    with open(updated_universe_json_file, 'w') as json_file:
        json.dump(new_universe_json, json_file, indent=4)
    '''

    # Check the updated JSON file for correctness
    with open(updated_universe_json_file) as json_data:
        json_check = json.load(json_data)
        print("Reading updated JSON FILE to verify ")
        print(json_check)

    input (" \n DEBUG PAUSE - CHECK THE JSON & Press Enter to continue . . . ")

    dst_http_url ='{}{}/{}{}'.format(dst_http_protocol,dst_http_host,dst_http_namespace,time.strftime("%Y-%m-%d"))
    transform_json('{}{}'.format(src_http_protocol,src_http_host),dst_http_url,updated_universe_json_file)

    with open(updated_universe_json_file) as json_data:
        json_check = json.load(json_data)
        print("Reading updated JSON FILE to verify ")
        print(json_check)

    # Return a LIST of all Absolute File References for upload to HTTP Repository
    http_artifacts = return_http_artifacts(working_directory)
    print("Cleaned up HTTP Artifacts are " + str(http_artifacts))

    if mode == 'sync':
        print ("\n Configured HTTP Repository is " + http_target)
        if http_target == 'nexus':
            print("Configured HTTP Repository is Nexus ")
            # Temp added below to SPEED UP TESTING so there are NO uploads.
            # baseurl ='{}{}/{}{}/'.format(dst_http_protocol,dst_http_host,dst_http_namespace,time.strftime("%Y-%m-%d"))
            # Temp comment out below for speeding up testing
            baseurl = upload_http_nexus(dst_http_protocol,dst_http_host,dst_http_namespace,http_artifacts)
        elif http_target == 'artifactory':
            baseurl = upload_http_artifactory()
        else:
            print("Configured HTTP Repository is not supported -- " + http_target)


        ## BELOW SECTION for BUILDING universe-marathon.json file to register a universe-server
        ## That will run on MArathon and serve the Universe repo-up-to-1.x.json
        print("\n Working on Marathon App for Universe-Server \n" )
        # print ("Script Directory is " + script_dir)
        universe_marathon_template = ('{}/{}'.format(script_dir,'universe-marathon.json'))
        universe_marathon_finished = ('{}{}'.format(working_directory,'universe-marathon.json'))
        shutil.copy(universe_marathon_template,universe_marathon_finished)
        transform_json('<universe-repo-file>',universe_json_file,universe_marathon_finished)
        transform_json('<universe-repo-uri>','{}{}'.format(baseurl,universe_json_file),universe_marathon_finished)
        f=open(universe_marathon_finished, 'r')
        file_contents = f.read()
        print("Universe Updated Marathon App Def located here " + universe_marathon_finished +" is below " )
        print(file_contents)
        ## Login to DCOS to retrieve an API TOKEN
        dcos_token = marathon.dcos_auth_login(target_dcos_master,target_dcos_user,target_dcos_pass)
        if dcos_token != '':
            print('{}{}'.format("DCOS TOKEN = ", dcos_token))
        else:
            exit(1)

        ## Initialize new Marathon Instance of Marathon Class
        target_marathon = marathon.marathon(target_dcos_master,dcos_token)
        ## POST the Marathon App Def for the Universe-server
        new_app = target_marathon.add_app(universe_marathon_finished)

        if new_app !='/test/universe-server':
            print ('Universe-server Marathon App Add failed  = ', new_app)
        else:
            print ('Universe-server Marathon App Add Succeeded  = ', new_app)

        print('To load the new Universe use the DCOS CLI command')
        print('{} {} {}'.format('dcos package repo add','<repo-name>', 'http://universe-server.marathon.l4lb.thisdcos.directory/repo'))
    elif mode == 'scan':
        baseurl ='{}{}/{}{}/'.format(dst_http_protocol,dst_http_host,dst_http_namespace,time.strftime("%Y-%m-%d"))

        zipfile=zip_universe_artifacts(working_directory,http_artifacts_scan_zip_dir)
        print("\n ********************* \n" )
        print('{} {} {}'.format('Universe HTTP Artifacts Archived to', zipfile, 'in WORKING Directory'))

# Clean up Containers and HTTP Data Directory

if mode != 'test':
    clean_up_tmp()
    clean_up_images()

print("\n ********************* \n")
print("\n Program Finished \n" )
