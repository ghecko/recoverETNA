import argparse
import json
import os
import re
import requests
import urllib.request
from subprocess import call
from clint.textui import progress


#######################
#  pip install clint  #
#######################

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_cookie(login, password):
    info_login_url = "https://auth.etna-alternance.net/login"
    login_url = "https://auth.etna-alternance.net/identity"
    data = [('login', login), ('password', password)]
    r = requests.post(info_login_url, data=data)
    cookie = {}
    cookie[r.cookies.keys()[0]] = r.cookies.values()[0]
    return cookie


def get_group_for_activities(mod_activities, cookie):
    url = "https://prepintra-api.etna-alternance.net/sessions/{}/{}/{}/mygroup".format(mod_activities["module"]["id"],
                                                                                       mod_activities["type"],
                                                                                       mod_activities["id"])
    r = requests.get(url, cookies=cookie)
    leader_array = json.loads(r.text)
    leader = leader_array["leader"]["login"]
    return leader


def download_file(url, directory, cookie):
    local_filename = url.split('/')[-1]
    if not os.path.exists(directory):
        os.makedirs(directory)
    r = requests.get(url, stream=True, cookies=cookie)
    try:
        total_length = int(r.headers.get('content-length'))
    except TypeError:
        opener = urllib.request.build_opener()
        opener.addheaders.append(('Cookie', 'authenticator={}'.format(cookie["authenticator"])))
        try:
            total_length = int(opener.open(url).read().__sizeof__())
        except urllib.error.HTTPError:
            print(bcolors.WARNING + "set random length for : " + url + bcolors.ENDC)
            total_length = 10000000
        r = requests.get(url, stream=True, cookies=cookie)
    with open(directory + "/" + local_filename, 'wb') as f:
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length / 1024) + 1):
            if chunk:
                f.write(chunk)


def download_course(mod_activities, cookie, dir_base):
    print(bcolors.OKBLUE + "download courses for {}".format(mod_activities["module"]["name"]) + bcolors.ENDC)
    # Get list of file
    directory = dir_base + "/" + mod_activities["module"]["name"] + "/" + mod_activities["name"]
    based_url = "https://modules-api.etna-alternance.net"
    file_url = based_url + "/{}/activities/{}/files".format(mod_activities["module"]["id"],
                                                                                       mod_activities["id"])
    response_file = requests.get(file_url, cookies=cookie)
    json_file = json.loads(response_file.text)
    for file in json_file:
        if (response_file.text == "[]"):
            print(bcolors.WARNING + "no resource for ==> {}".format(file["module"]) + bcolors.ENDC)
        else:
            print(bcolors.OKGREEN + "download file {}".format(mod_activities["module"]["name"] + "/" +
                                                                 file["path"].split('/')[-1]) + bcolors.ENDC)
            download_file(based_url + file["path"], directory, cookie)


def get_work(mod_activities, cookie, dir_base, login, password):
    print(bcolors.OKBLUE + "svn and subject for {}".format(mod_activities["module"]["name"]) + bcolors.ENDC)
    # Get list of subject files
    directory = dir_base + "/" + mod_activities["module"]["name"] + "/" + mod_activities["name"]
    based_url = "https://modules-api.etna-alternance.net"
    file_url = based_url + "/{}/activities/{}/files".format(mod_activities["module"]["id"],
                                                                                       mod_activities["id"])
    response_file = requests.get(file_url, cookies=cookie)
    json_file = json.loads(response_file.text)
    for file in json_file:
        if (response_file.text == "[]"):
            print(bcolors.WARNING + "no ressource for ==> {}".format(file["module"]) + bcolors.ENDC)
        else:
            print(bcolors.OKGREEN + "download file {}".format(mod_activities["module"]["name"] + "/" +
                                                                 file["path"].split('/')[-1]) + bcolors.ENDC)
            download_file(based_url + file["path"], directory, cookie)

    # svn checkout
    if(mod_activities["rendu"] != ""):
        groupLeader = get_group_for_activities(mod_activities, cookie)
        url_rendu = mod_activities["rendu"].replace(' /', '/')
        url_rendu = url_rendu.replace('$$session$$', str(mod_activities["module"]["name"]))
        url_rendu = url_rendu.replace('$$session_id$$', str(mod_activities["module"]["id"]))
        url_rendu = url_rendu.replace('$$leader$$', str(groupLeader))
        call(["svn", "co", "--username", login, "--password", password, url_rendu, directory])
    else:
        print(bcolors.WARNING + "no svn for ==> {}".format(mod_activities["module"]["name"]) + bcolors.ENDC)


def get_module(login, password, cookie):
    # ETNA Bachelor url
    module_url_bach = "https://modules-api.etna-alternance.net/students/{}/search?role=students&term_id=96".format(login)
    # ETNA Master url
    module_url_Mast = "https://modules-api.etna-alternance.net/students/{}/search?role=students&term_id=98".format(login)
    r = requests.get(module_url_bach, cookies=cookie)
    modules_Bach = json.loads(r.text)
    r = requests.get(module_url_Mast, cookies=cookie)
    modules_Master = json.loads(r.text)

    # Process for Bachelor modules
    for activities in modules_Bach:
        activities_url = "https://modules-api.etna-alternance.net/{}/activities".format(activities["id"])
        r = requests.get(activities_url, cookies=cookie)
        json_data = json.loads(r.text)
        for mod_activities in json_data:
            if not re.match(r'.*EMI.*', mod_activities["module"]["name"]):
                if mod_activities["type"] == "cours":
                    download_course(mod_activities, cookie, "Bachelor")
                elif mod_activities["type"] == "quest":
                    get_work(mod_activities, cookie, "Bachelor", login, password)
                else:
                    get_work(mod_activities, cookie, "Bachelor", login, password)
            else:
                print(bcolors.FAIL + "Don't download : {}".format(mod_activities["module"]["name"]) + bcolors.ENDC)

    # Process for Master modules
    for activities in modules_Master:
        activities_url = "https://modules-api.etna-alternance.net/{}/activities".format(activities["id"])
        r = requests.get(activities_url, cookies=cookie)
        json_data = json.loads(r.text)
        for mod_activities in json_data:
            if mod_activities["type"] == "cours":
                download_course(mod_activities, cookie, "Master")
            elif mod_activities["type"] == "quest":
                get_work(mod_activities, cookie, "Master", login, password)
            else:
                get_work(mod_activities, cookie, "Master", login, password)


def main(login, password):
    ## First, login to ETNA
    cookie = get_cookie(login, password)

    # Get modules name
    get_module(login, password, cookie)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Download ETNA resources")

    parser.add_argument("-l",
                        "--login",
                        type=str)
    parser.add_argument("-p",
                        "--password",
                        type=str)
    args = parser.parse_args()
    if args.login is None or args.password is None:
        parser.print_help()
    else:
        main(login=args.login, password=args.password)