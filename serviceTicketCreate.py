import requests
import json
import sys
from MainScript import centJiraCore 

centURLV2 = "http://10.10.100.106/centreon/api/latest/"
centURLV1 = "http://10.10.100.106/centreon/api/index.php?"
jiraURL = "http://10.10.100.106:8086/rest/api/2/issue/"


def getToken(username,password,url):
    payload = "{\r\n  \"security\": {\r\n    \"credentials\": {\r\n      \"login\": \""+username+"\",\r\n      \"password\": \""+password+"\"\r\n    }\r\n  }\r\n}"
    headers = {
    'Content-Type': 'application/json'
    }
    authURL = url + 'login'
    authTokenResponse = requests.request("POST", authURL, headers=headers, data = payload)
    authTokenJson = json.loads(authTokenResponse.text)
    return (authTokenJson['security']['token'])


#Get the parent host status
def getHostState(connURL,Token,Hostname):
    url = connURL+"object=centreon_realtime_hosts&action=list&fields=id,name,alias,address,state,state_type,output,next_check,acknowledged,instance&search="+Hostname
    payload = {}
    headers = {
    'Content-Type': 'application/json',
    'centreon-auth-token': Token
    }
    HostStateresponse = requests.request("GET", url, headers=headers, data = payload)
    HostStateresponseJson = json.loads(HostStateresponse.text)

    PStateRepo = {} #This repo will hold the all the status of parent host
    
    for item in HostStateresponseJson:
        PStateRepo['name'] = item['name']
        PStateRepo['state'] = item['state']
        PStateRepo['address'] = item['address']
        PStateRepo['output'] = item['output']
        PStateRepo['acknowledged'] = item['acknowledged']
        PStateRepo['instance_name'] = item['instance_name']
    return PStateRepo

#Get Service Details
def getServiceDetails(connURL,Token,hostname,serviceDesc):
    url = centURLV1 + "object=centreon_realtime_services&action=list&searchHost="+hostname+"&search="+serviceDesc
    payload  = {}
    headers = {
    'Content-Type': 'application/json',
    'centreon-auth-token': Token
    }
    getServiceResponse = requests.request("GET", url, headers=headers, data = payload)
    getServiceJson = json.loads(getServiceResponse.text)
    
    serviceDetailsHolder = {}
    
    for item in getServiceJson:
        serviceDetailsHolder['host_id'] = item['host_id']
        serviceDetailsHolder['name'] = item['name']
        serviceDetailsHolder['description'] = item['description']
        serviceDetailsHolder['service_id'] = item['service_id']
        serviceDetailsHolder['state'] = item['state']
        serviceDetailsHolder['output'] = item['output']
        serviceDetailsHolder['perfdata'] = item['perfdata']
        serviceDetailsHolder['acknowledged'] = item['acknowledged']
    return serviceDetailsHolder

#Ack Service
def ackService(connURL,Token,hostid,serviceid,JiraResponse):
    url = connURL + 'monitoring/services/acknowledgements'
    payload = "[\r\n  {\r\n    \"comment\": \""+JiraResponse+"\",\r\n    \"is_notify_contacts\": false,\r\n    \"is_persistent_comment\": true,\r\n    \"is_sticky\": true,\r\n    \"resource_id\": "+serviceid+",\r\n    \"parent_resource_id\": "+hostid+"\r\n  }\r\n]"
    headers = {
    'X-AUTH-TOKEN': Token,
    'Content-Type': 'text/plain'
    }
    ackresponse = requests.request("POST", url, headers=headers, data = payload)

#Jira Ticket Creation
def jiraTicketCreate(jiraURL,id,desc,summary):

    url = jiraURL

    payload = "{\r\n    \"fields\": {\r\n       \"project\":\r\n       {\r\n          \"id\": \""+id+"\"\r\n       },\r\n       \"summary\":\""+summary+"\",\r\n       \"description\":\""+desc+"\",\r\n       \"issuetype\": {\r\n          \"id\": \""+id+"\"\r\n       }\r\n   }\r\n}"
    headers = {
    'Authorization': 'Basic dnJuYXZlZW5rcjpXZWxjb21lQDE=',
    'Content-Type': 'application/json'
    }

    jiraResponse = requests.request("POST", url, headers=headers, data = payload)
    jiraResponseJson = json.loads(jiraResponse.text)
    return jiraResponseJson

#Main Logic
def mainLogic(serviceDetails,hostDetails,connURL,Token,jiraURL):
    if (hostDetails['state'] == '0'):
        if serviceDetails['acknowledged'] == '0':
            details = 'Service Down ' +serviceDetails['name']+' Service Details : '+serviceDetails['description'] + ', Error : '+serviceDetails['output']
            details = details.replace('\n', ' ').replace('\r', '')
            jira = jiraTicketCreate(jiraURL,'10000',details,details)
            jiraCentUpdate = jira['key']+', '+ jira['self']
            ackService(connURL,Token,serviceDetails['host_id'],serviceDetails['service_id'],jiraCentUpdate)
        else:
            print('Service Already Acknowledged')

    else:
        centJiraCore(serviceDetails['name'])
        pass
        
def start(hostname,servicename):
    #Variable Declaration
    sessionToken = getToken('admin','Welcome@1',centURLV2)
    serviceDetails = getServiceDetails(centURLV1,sessionToken,hostname,servicename)
    hostDetails = getHostState(centURLV1,sessionToken,serviceDetails['name'])
    mainLogic(serviceDetails,hostDetails,centURLV2,sessionToken,jiraURL)


if __name__ == "__main__":
    hostname = sys.argv[1]
    servicename = sys.argv[2]
    start(hostname,servicename)

